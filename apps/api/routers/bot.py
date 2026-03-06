import logging
from datetime import datetime
import re
from typing import Any, Type
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dateutil import parser
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from timezonefinder import TimezoneFinder

from apps.api.deps import get_llm_service, get_nlp_service, get_schedule_service, get_user
from apps.config import settings
from corelib.db.session import get_async_session
from corelib.repositories import InviteRepository, UserRepository
from corelib.services import LLMService, NLPService, ScheduleService
from corelib.utils.personalize import ANSWER_RULES
from corelib.utils.response_templates import format_event_created_response, format_schedule_response

router = APIRouter()
ALLOWED_INVITE_ROLES = {"owner", "tester", "user"}
SENSITIVE_KEYS = {"password", "token", "secret", "api_key", "invite_code"}
EXPECTED_ENTITY_FORMATS = {
    "add_event": {"date": "YYYY-MM-DD", "time": "HH:MM", "title": "optional"},
    "add_reminder": {"date": "YYYY-MM-DD", "time": "HH:MM", "reminder_text": "optional", "timezone": "optional IANA"},
    "get_schedule": {"date": "optional YYYY-MM-DD"},
    "set_language": {"language_code": "ISO 639-1 optional", "language_name": "optional"},
    "set_timezone": {"timezone": "IANA optional", "city": "optional"},
    "delete_event": {"target_id": "optional", "query": "optional"},
    "delete_reminder": {"target_id": "optional", "query": "optional"},
    "help": {"topic": "optional"},
    "smalltalk": {"topic": "optional"},
    "create_invite_code": {"role": "user|tester|owner", "max_uses": ">=1", "expires_in_days": ">=1"},
}
logger = logging.getLogger("apps.api.bot")
timezone_finder = TimezoneFinder()

LANGUAGE_NAME_TO_CODE = {
    "english": "en",
    "russian": "ru",
    "russian language": "ru",
    "spanish": "es",
    "german": "de",
    "french": "fr",
    "italian": "it",
    "portuguese": "pt",
    "ukrainian": "uk",
}

TRANSLATIONS = {
    "en": {
        "set_language_success": "Language updated: {language}.",
        "set_timezone_success": "Timezone updated: {timezone}.",
        "unknown_intent": "Sorry, I did not understand the request.",
        "invalid_language": "Could not recognize language. Please provide a valid language code or language name.",
        "invalid_timezone": "Could not recognize timezone. Please provide an IANA timezone or a known city.",
    },
    "ru": {
        "set_language_success": "Язык обновлен: {language}.",
        "set_timezone_success": "Часовой пояс обновлен: {timezone}.",
        "unknown_intent": "Извините, я не понял запрос.",
        "invalid_language": "Не удалось распознать язык. Укажите корректный код или название языка.",
        "invalid_timezone": "Не удалось распознать часовой пояс. Укажите IANA-таймзону или известный город.",
    },
}


def _resolve_language_code(raw_code: str | None, raw_name: str | None) -> str | None:
    if raw_code:
        code = raw_code.strip().lower()
        if re.fullmatch(r"[a-z]{2}", code):
            return code
    if raw_name:
        return LANGUAGE_NAME_TO_CODE.get(raw_name.strip().lower())
    return None


def _localized_message(user_language: str | None, key: str, **kwargs: Any) -> str:
    language_code = (user_language or "en").split("-")[0].lower()
    template = TRANSLATIONS.get(language_code, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"][key])
    return template.format(**kwargs)


class BotMessage(BaseModel):
    user_id: str
    text: str


class StartPayload(BaseModel):
    telegram_id: str
    name: str | None = None
    language: str | None = None


class InvitePayload(BaseModel):
    telegram_id: str
    invite_code: str


class TimezonePayload(BaseModel):
    telegram_id: str
    timezone: str


class TimezoneByLocationPayload(BaseModel):
    telegram_id: str
    lat: float
    lon: float


class TimezoneDefaultPayload(BaseModel):
    telegram_id: str


class CreateInvitePayload(BaseModel):
    telegram_id: str
    role: str = "user"
    max_uses: int = Field(default=1, ge=1)
    expires_in_days: int = Field(default=3, ge=1)


class AddEventEntities(BaseModel):
    date: str
    time: str
    title: str | None = None
    location: str | None = None
    recurrence: str | None = None
    remind_before_minutes: int | None = None


class GetScheduleEntities(BaseModel):
    date: str | None = None


class AddReminderEntities(BaseModel):
    date: str
    time: str
    reminder_text: str | None = None
    timezone: str | None = None


class SetLanguageEntities(BaseModel):
    language_code: str | None = None
    language_name: str | None = None


class SetTimezoneEntities(BaseModel):
    timezone: str | None = None
    city: str | None = None


class DeleteTargetEntities(BaseModel):
    target_id: str | None = None
    query: str | None = None


class HelpEntities(BaseModel):
    topic: str | None = None


class SmalltalkEntities(BaseModel):
    topic: str | None = None


class CreateInviteCodeEntities(BaseModel):
    role: str = "user"
    max_uses: int = Field(default=1, ge=1)
    expires_in_days: int = Field(default=3, ge=1)


def _mask_sensitive_data(payload: Any) -> Any:
    if isinstance(payload, dict):
        masked: dict[str, Any] = {}
        for key, value in payload.items():
            if key.lower() in SENSITIVE_KEYS:
                masked[key] = "***"
            else:
                masked[key] = _mask_sensitive_data(value)
        return masked
    if isinstance(payload, list):
        return [_mask_sensitive_data(item) for item in payload]
    return payload


def _visible_text(text: str) -> str:
    if settings.LOG_VERBOSE_BOT_PAYLOAD:
        return text
    return "[REDACTED: set LOG_VERBOSE_BOT_PAYLOAD=true for full payload]"




def normalize_iana_timezone(timezone_name: str | None, fallback: str = "Etc/UTC") -> str:
    candidate = (timezone_name or "").strip()
    if not candidate:
        return fallback
    try:
        ZoneInfo(candidate)
        return candidate
    except ZoneInfoNotFoundError:
        return fallback

def validate_intent_payload(intent: str, entities: Any) -> tuple[BaseModel | None, str | None]:
    safe_entities = entities if isinstance(entities, dict) else {}

    models_by_intent: dict[str, Type[BaseModel]] = {
        "add_event": AddEventEntities,
        "add_reminder": AddReminderEntities,
        "get_schedule": GetScheduleEntities,
        "set_language": SetLanguageEntities,
        "set_timezone": SetTimezoneEntities,
        "delete_event": DeleteTargetEntities,
        "delete_reminder": DeleteTargetEntities,
        "help": HelpEntities,
        "smalltalk": SmalltalkEntities,
        "create_invite_code": CreateInviteCodeEntities,
    }
    error_messages_by_intent = {
        "add_event": "Could not recognize date/time. Please clarify date and time.",
        "add_reminder": "Could not recognize reminder date/time. Please clarify date and time.",
        "set_language": "Could not recognize language. Please provide language code or language name.",
        "set_timezone": "Could not recognize timezone. Please provide IANA timezone or city.",
        "delete_event": "Could not identify which event to delete. Provide event id or description.",
        "delete_reminder": "Could not identify which reminder to delete. Provide reminder id or description.",
        "create_invite_code": "Could not recognize invite parameters. Please clarify your request.",
    }

    if intent == "add_event" and (not safe_entities.get("date") or not safe_entities.get("time")):
        return None, error_messages_by_intent["add_event"]
    if intent == "add_reminder" and (not safe_entities.get("date") or not safe_entities.get("time")):
        return None, error_messages_by_intent["add_reminder"]
    if intent == "set_language" and not (safe_entities.get("language_code") or safe_entities.get("language_name")):
        return None, error_messages_by_intent["set_language"]
    if intent == "set_timezone" and not (safe_entities.get("timezone") or safe_entities.get("city")):
        return None, error_messages_by_intent["set_timezone"]
    if intent in {"delete_event", "delete_reminder"} and not (safe_entities.get("target_id") or safe_entities.get("query")):
        return None, error_messages_by_intent[intent]

    model_cls = models_by_intent.get(intent)
    if model_cls is None:
        return None, None

    try:
        return model_cls.model_validate(safe_entities), None
    except ValidationError:
        return None, error_messages_by_intent.get(intent, "Could not process request parameters. Please clarify your request.")


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
        user = await user_repo.create_pending_telegram_user(
            payload.telegram_id,
            payload.name,
            language=payload.language,
        )
    else:
        await user_repo.update_profile(
            user,
            name=payload.name,
            language=payload.language,
        )

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


@router.post("/register/timezone/by_location")
async def register_timezone_by_location(
    payload: TimezoneByLocationPayload,
    session: AsyncSession = Depends(get_async_session),
):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(payload.telegram_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    timezone = normalize_iana_timezone(
        timezone_finder.timezone_at(lat=payload.lat, lng=payload.lon),
        fallback="Etc/UTC",
    )

    await user_repo.activate_user_with_timezone(user, timezone, role=user.role)
    return {"status": "registered", "timezone": timezone, "message": "Registration completed."}




@router.post("/register/timezone/default")
async def register_timezone_default(
    payload: TimezoneDefaultPayload,
    session: AsyncSession = Depends(get_async_session),
):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(payload.telegram_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    timezone = normalize_iana_timezone(settings.DEFAULT_TIMEZONE, fallback="Etc/UTC")
    await user_repo.activate_user_with_timezone(user, timezone, role=user.role)
    return {"status": "registered", "timezone": timezone, "message": "Registration completed."}


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
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    nlp_service: NLPService = Depends(get_nlp_service),
    schedule_service: ScheduleService = Depends(get_schedule_service),
    llm_service: LLMService = Depends(get_llm_service),
):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    request_time = datetime.utcnow().isoformat()

    logger.info(
        "incoming /bot/message user_id=%s request_id=%s time=%s text=%s",
        payload.user_id,
        request_id,
        request_time,
        _visible_text(payload.text),
        extra={"log_prefix": "[REQUEST]"},
    )

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(payload.user_id)
    if user is None:
        logger.warning(
            "user not found for request_id=%s user_id=%s",
            request_id,
            payload.user_id,
            extra={"log_prefix": "[RESPONSE]"},
        )
        raise HTTPException(status_code=404, detail="User not found")

    parsed: list[dict[str, Any]] = []
    try:
        parsed = await nlp_service.parse_intent_list(payload.text)
        for packet in parsed:
            logger.info(
                "nlp parse request_id=%s intent=%s entities=%s",
                request_id,
                packet.get("intent"),
                _mask_sensitive_data(packet.get("entities") or {}),
                extra={"log_prefix": "[NLP]"},
            )

        result = []
        secure_replies = []
        direct_replies = []
        for p in parsed:
            intent = p.get("intent")
            entities = p.get("entities")
            validated_entities, validation_error = validate_intent_payload(intent, entities)

            if validation_error:
                logger.warning(
                    "intent validation failed request_id=%s intent=%s entities=%s expected=%s error=%s",
                    request_id,
                    intent,
                    _mask_sensitive_data(entities if isinstance(entities, dict) else {"raw": entities}),
                    EXPECTED_ENTITY_FORMATS.get(intent),
                    validation_error,
                    extra={"log_prefix": "[NLP]"},
                )
                secure_replies.append(validation_error)
                continue

            if intent == "add_event":
                add_event_entities = validated_entities
                if not isinstance(add_event_entities, AddEventEntities):
                    secure_replies.append("Could not process event parameters. Please clarify your request.")
                    continue
                try:
                    dt = parser.parse(f"{add_event_entities.date} {add_event_entities.time}").astimezone(ZoneInfo(user.timezone))
                except (ValueError, TypeError, OverflowError):
                    logger.warning(
                        "date parsing failed request_id=%s source=%s expected=%s",
                        request_id,
                        f"{add_event_entities.date} {add_event_entities.time}",
                        EXPECTED_ENTITY_FORMATS["add_event"],
                        extra={"log_prefix": "[NLP]"},
                    )
                    secure_replies.append("Invalid date/time format. Please use something like: 2026-03-20 18:30")
                    continue

                created_event = await schedule_service.create_event(
                    user_id=user.id,
                    title=add_event_entities.title or p.get("title") or "Event",
                    start_time=dt,
                    location=add_event_entities.location or p.get("location"),
                    recurrence=add_event_entities.recurrence or p.get("recurrence"),
                    remind_before_minutes=add_event_entities.remind_before_minutes or p.get("remind_before_minutes", 60),
                )
                direct_replies.append(
                    format_event_created_response(
                        start_time=created_event.start_time,
                        title=created_event.title,
                        timezone_name=user.timezone,
                        language=user.language or "en",
                    )
                )
            elif intent == "get_schedule":
                get_schedule_entities = validated_entities
                if not isinstance(get_schedule_entities, GetScheduleEntities):
                    secure_replies.append("Could not recognize schedule date. Please clarify your request.")
                    continue
                if get_schedule_entities.date:
                    try:
                        day = parser.parse(get_schedule_entities.date)
                    except (ValueError, TypeError, OverflowError):
                        logger.warning(
                            "schedule date parsing failed request_id=%s source=%s expected=%s",
                            request_id,
                            get_schedule_entities.date,
                            EXPECTED_ENTITY_FORMATS["get_schedule"],
                            extra={"log_prefix": "[NLP]"},
                        )
                        secure_replies.append("Invalid schedule date format. Please provide a valid date.")
                        continue
                else:
                    day = datetime.now(tz=ZoneInfo(user.timezone))
                events = await schedule_service.get_upcoming_events(user.id, day)
                event_items = [{"title": e.title, "start_time": e.start_time.isoformat()} for e in events]
                direct_replies.append(
                    format_schedule_response(
                        day=day,
                        events=event_items,
                        timezone_name=user.timezone,
                        language=user.language or "en",
                    )
                )
            elif intent == "set_language":
                language_entities = validated_entities
                if not isinstance(language_entities, SetLanguageEntities):
                    secure_replies.append(_localized_message(user.language, "invalid_language"))
                    continue
                resolved_language = _resolve_language_code(language_entities.language_code, language_entities.language_name)
                if not resolved_language:
                    secure_replies.append(_localized_message(user.language, "invalid_language"))
                    continue
                await user_repo.update_profile(user, name=user.name, language=resolved_language)
                user.language = resolved_language
                direct_replies.append(_localized_message(user.language, "set_language_success", language=resolved_language))
            elif intent == "set_timezone":
                timezone_entities = validated_entities
                if not isinstance(timezone_entities, SetTimezoneEntities):
                    secure_replies.append(_localized_message(user.language, "invalid_timezone"))
                    continue
                next_timezone = None
                if timezone_entities.timezone:
                    candidate = timezone_entities.timezone.strip()
                    try:
                        ZoneInfo(candidate)
                        next_timezone = candidate
                    except ZoneInfoNotFoundError:
                        next_timezone = None
                if not next_timezone and timezone_entities.city:
                    city = timezone_entities.city.strip()
                    if city:
                        # simple fallback for city phrases when only city is available
                        next_timezone = normalize_iana_timezone(city, fallback="")
                if not next_timezone:
                    secure_replies.append(_localized_message(user.language, "invalid_timezone"))
                    continue
                await user_repo.activate_user_with_timezone(user, next_timezone, role=user.role)
                user.timezone = next_timezone
                direct_replies.append(_localized_message(user.language, "set_timezone_success", timezone=next_timezone))
            elif intent == "create_invite_code":
                if user.role != "owner":
                    secure_replies.append("Only owner can create invite codes.")
                    continue
                invite_entities = validated_entities
                if not isinstance(invite_entities, CreateInviteCodeEntities):
                    secure_replies.append("Could not recognize invite parameters. Please clarify your request.")
                    continue
                role = invite_entities.role
                max_uses = invite_entities.max_uses
                expires_in_days = invite_entities.expires_in_days
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
                result.append({"info": _localized_message(user.language, "unknown_intent")})

        if secure_replies and not result:
            reply_parts = []
            if direct_replies:
                reply_parts.append("\n\n".join(direct_replies))
            reply_parts.append("\n".join(secure_replies))
            reply_text = "\n\n".join(reply_parts)
            logger.info(
                "reply generated request_id=%s mode=secure_only",
                request_id,
                extra={"log_prefix": "[RESPONSE]"},
            )
            return {"reply": reply_text}

        if direct_replies and not result:
            reply_text = "\n\n".join(direct_replies)
            if secure_replies:
                reply_text += "\n\n" + "\n".join(secure_replies)
            logger.info(
                "reply generated request_id=%s mode=deterministic",
                request_id,
                extra={"log_prefix": "[RESPONSE]"},
            )
            return {"reply": reply_text}

        if secure_replies:
            result.append({"secure_info": "Invite operations completed. Sensitive data omitted."})

        answer = await llm_service.chat_completion(
            [
                {"role": "system", "content": f"You are a personal assistant. Respond: {ANSWER_RULES}"},
                {"role": "system", "content": f"User context: language={user.language}, timezone={user.timezone}"},
                {"role": "system", "content": "Always reply in the language from user context. Keep deterministic bullet/list structure if present."},
                {"role": "user", "content": f"Data: {result}. Generate a response."},
            ],
            temperature=0.3,
        )

        logger.info("reply generated request_id=%s", request_id, extra={"log_prefix": "[RESPONSE]"})
        if direct_replies:
            answer = "\n\n".join(direct_replies + [answer])
        if secure_replies:
            return {"reply": f"{answer}\n\n" + "\n".join(secure_replies)}
        return {"reply": answer}
    except Exception:
        logger.exception(
            "unhandled error in /bot/message request_id=%s intents=%s",
            request_id,
            _mask_sensitive_data(parsed),
            extra={"log_prefix": "[ERROR]"},
        )
        raise
