from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from corelib.config import settings
from corelib.db.session import get_async_session
from corelib.repositories import EventRepository, ReminderRepository, UserRepository
from corelib.services import LLMService, NLPService, ScheduleService


async def get_user(user_id: str, session: AsyncSession = Depends(get_async_session)):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is not activated")
    return user


async def get_llm_service() -> LLMService:
    return LLMService(settings)


async def get_nlp_service(llm_service: LLMService = Depends(get_llm_service)) -> NLPService:
    return NLPService(llm_service)


async def get_schedule_service(session: AsyncSession = Depends(get_async_session)) -> ScheduleService:
    event_repo = EventRepository(session)
    reminder_repo = ReminderRepository(session)
    return ScheduleService(event_repo, reminder_repo)
