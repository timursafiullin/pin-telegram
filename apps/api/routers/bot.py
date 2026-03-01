from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dateutil import parser
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps import get_llm_service, get_nlp_service, get_schedule_service, get_user
from corelib.db.session import get_async_session
from corelib.repositories import InviteRepository, UserRepository
from corelib.services import LLMService, NLPService, ScheduleService

router = APIRouter()
ALLOWED_INVITE_ROLES = {"owner", "tester", "user"}


class BotMessage(BaseModel):
    user_id: str
    text: str


class StartPayload(BaseModel):
    telegram_id: str
    name: str | None = None


class InvitePayload(BaseModel):
    telegram_id: str
    invite_code: str


class TimezonePayload(BaseModel):
    telegram_id: str
    timezone: str


class CreateInvitePayload(BaseModel):
    telegram_id: str
    role: str = "user"
    max_uses: int = Field(default=1, ge=1)
    expires_in_days: int = Field(default=3, ge=1)


@router.on_event("startup")
async def ensure_bootstrap_invite():
    async for session in get_async_session():
        invite_repo = InviteRepository(session)
        await invite_repo.ensure_bootstrap_invite()
        break


@router.post("/register/start")
async def register_start(payload: StartPayload, session: AsyncSession = Depends(get_async_session)):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(payload.telegram_id)
    if user is None:
        user = await user_repo.create_pending_telegram_user(payload.telegram_id, payload.name)

    if user.is_active:
        return {"status": "registered", "message": "Welcome back!"}
    return {"status": "awaiting_invite", "message": "Please provide your invite code."}


@router.post("/register/invite")
async def register_invite(payload: InvitePayload, session: AsyncSession = Depends(get_async_session)):
    user_repo = UserRepository(session)
    invite_repo = InviteRepository(session)

    user = await user_repo.get_by_telegram_id(payload.telegram_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found. Please run /start first")

    invite = await invite_repo.get_active_by_code(payload.invite_code)
    if invite is None:
        raise HTTPException(status_code=400, detail="Invalid or expired invite code")

    await invite_repo.consume_invite(invite)
    user.role = invite.role
    await session.commit()
    return {
        "status": "awaiting_timezone",
        "assigned_role": invite.role,
        "message": "Invite accepted. Send your IANA timezone, e.g. Europe/Moscow",
    }


@router.post("/register/timezone")
async def register_timezone(payload: TimezonePayload, session: AsyncSession = Depends(get_async_session)):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(payload.telegram_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        ZoneInfo(payload.timezone)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(status_code=400, detail="Unknown timezone") from exc

    await user_repo.activate_user_with_timezone(user, payload.timezone, role=user.role)
    return {"status": "registered", "message": "Registration completed."}


@router.post("/invites/create")
async def create_invite(payload: CreateInvitePayload, session: AsyncSession = Depends(get_async_session)):
    user_repo = UserRepository(session)
    invite_repo = InviteRepository(session)

    creator = await user_repo.get_by_telegram_id(payload.telegram_id)
    if creator is None or not creator.is_active:
        raise HTTPException(status_code=403, detail="Only active users can create invite codes")
    if creator.role != "owner":
        raise HTTPException(status_code=403, detail="Only owner can create invite codes")
    if payload.role not in ALLOWED_INVITE_ROLES:
        raise HTTPException(status_code=400, detail="Unknown role for invite")

    invite = await invite_repo.create_invite(
        created_by=creator.id,
        role=payload.role,
        max_uses=payload.max_uses,
        expires_in_days=payload.expires_in_days,
    )
    return {
        "code": invite.code,
        "role": invite.role,
        "max_uses": invite.max_uses,
        "uses_count": invite.uses_count,
        "expires_at": invite.expires_at.isoformat() if invite.expires_at else None,
        "is_active": invite.is_active,
    }


@router.get("/invites/my")
async def my_invites(telegram_id: str, session: AsyncSession = Depends(get_async_session)):
    user_repo = UserRepository(session)
    invite_repo = InviteRepository(session)

    creator = await user_repo.get_by_telegram_id(telegram_id)
    if creator is None or not creator.is_active:
        raise HTTPException(status_code=403, detail="Only active users can view invite codes")

    invites = await invite_repo.get_by_creator(creator.id)
    return {
        "items": [
            {
                "code": invite.code,
                "role": invite.role,
                "max_uses": invite.max_uses,
                "uses_count": invite.uses_count,
                "expires_at": invite.expires_at.isoformat() if invite.expires_at else None,
                "is_active": invite.is_active,
            }
            for invite in invites
        ]
    }


@router.post("/message")
async def handle_bot_message(
    payload: BotMessage,
    session: AsyncSession = Depends(get_async_session),
    nlp_service: NLPService = Depends(get_nlp_service),
    schedule_service: ScheduleService = Depends(get_schedule_service),
    llm_service: LLMService = Depends(get_llm_service),
):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(payload.user_id)
    parsed = await nlp_service.parse_intent_list(payload.text)

    result = []
    secure_replies = []
    for p in parsed:
        intent = p.get("intent")
        entities = p.get("entities", {})

        if intent == "add_event":
            dt = parser.parse(f"{entities['date']} {entities['time']}").astimezone(ZoneInfo(user.timezone))
            created_event = await schedule_service.create_event(
                user_id=user.id,
                title=entities.get("title") or p.get("title") or "Event",
                start_time=dt,
                location=p.get("location"),
                recurrence=p.get("recurrence"),
                remind_before_minutes=p.get("remind_before_minutes", 60),
            )
            result.append({"event": {"title": created_event.title, "start_time": created_event.start_time.isoformat()}})
        elif intent == "get_schedule":
            day = parser.parse(entities["date"]) if entities.get("date") else datetime.now(tz=ZoneInfo(user.timezone))
            events = await schedule_service.get_upcoming_events(user.id, day)
            result.append({"events": [{"title": e.title, "start_time": e.start_time.isoformat()} for e in events]})
        elif intent == "create_invite_code":
            if user.role != "owner":
                secure_replies.append("Only owner can create invite codes.")
                continue
            role = entities.get("role", "user")
            max_uses = int(entities.get("max_uses", 1))
            expires_in_days = int(entities.get("expires_in_days", 3))
            if role not in ALLOWED_INVITE_ROLES:
                secure_replies.append("Unknown role for invite code.")
                continue
            if max_uses < 1 or expires_in_days < 1:
                secure_replies.append("max_uses and expires_in_days must be >= 1")
                continue
            invite_repo = InviteRepository(schedule_service.event_repo.session)
            invite = await invite_repo.create_invite(
                created_by=user.id,
                role=role,
                max_uses=max_uses,
                expires_in_days=expires_in_days,
            )
            secure_replies.append(
                "Invite created: "
                f"code={invite.code}, role={invite.role}, max_uses={invite.max_uses}, "
                f"expires_at={invite.expires_at.isoformat() if invite.expires_at else 'never'}"
            )
        elif intent == "list_my_invite_codes":
            invite_repo = InviteRepository(schedule_service.event_repo.session)
            invites = await invite_repo.get_by_creator(user.id)
            if not invites:
                secure_replies.append("You do not have invite codes yet.")
                continue
            lines = [
                (
                    f"{invite.code} | role={invite.role} | uses={invite.uses_count}/"
                    f"{invite.max_uses if invite.max_uses is not None else '∞'} | "
                    f"expires_at={invite.expires_at.isoformat() if invite.expires_at else 'never'} | "
                    f"active={invite.is_active}"
                )
                for invite in invites
            ]
            secure_replies.append("Your invite codes:\n" + "\n".join(lines))
        else:
            result.append({"info": "Sorry, I did not understand the request."})

    if secure_replies and not result:
        return {"reply": "\n".join(secure_replies)}

    if secure_replies:
        result.append({"secure_info": "Invite operations completed. Sensitive data omitted."})

    answer = await llm_service.chat_completion(
        [
            {"role": "system", "content": "You are a personal assistant. Respond in a friendly and concise manner."},
            {"role": "user", "content": f"Data: {result}. Generate a response."},
        ],
        temperature=0.3,
    )

    if secure_replies:
        return {"reply": f"{answer}\n\n" + "\n".join(secure_replies)}
    return {"reply": answer}
