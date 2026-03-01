from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dateutil import parser
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps import get_llm_service, get_nlp_service, get_schedule_service, get_user
from corelib.db.session import get_async_session
from corelib.repositories import InviteRepository, UserRepository
from corelib.services import LLMService, NLPService, ScheduleService

router = APIRouter()


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

    await invite_repo.mark_used(invite, user.id)
    return {"status": "awaiting_timezone", "message": "Invite accepted. Send your IANA timezone, e.g. Europe/Moscow"}


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

    await user_repo.activate_user_with_timezone(user, payload.timezone)
    return {"status": "registered", "message": "Registration completed."}


@router.post("/message")
async def handle_bot_message(
    payload: BotMessage,
    nlp_service: NLPService = Depends(get_nlp_service),
    schedule_service: ScheduleService = Depends(get_schedule_service),
    llm_service: LLMService = Depends(get_llm_service),
):
    user = await get_user(payload.user_id)
    parsed = await nlp_service.parse_intent_list(payload.text)

    result = []
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
        else:
            result.append({"info": "Sorry, I did not understand the request."})

    answer = await llm_service.chat_completion(
        [
            {"role": "system", "content": "You are a personal assistant. Respond in a friendly and concise manner."},
            {"role": "user", "content": f"Data: {result}. Generate a response."},
        ],
        temperature=0.3,
    )
    return {"reply": answer}
