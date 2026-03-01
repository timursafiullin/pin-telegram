from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from corelib.config import Settings

from corelib.db.session import get_async_session
from corelib.services import (
    LLMService,
    NLPService,
    ScheduleService,
)
from corelib.repositories import (
    UserRepository,
    EventRepository,
    ReminderRepository,
)

async def get_user(user_id: str):
    pass

async def get_llm_service(settings: Settings = Depends(Settings)):
    return LLMService(settings)

async def get_nlp_service(llm_service: LLMService = Depends(get_llm_service)):
    return NLPService(llm_service)

async def get_schedule_service(session: AsyncSession = Depends(get_async_session)):
    event_repo = EventRepository(session)
    reminder_repo = ReminderRepository(session)
    return ScheduleService(event_repo, reminder_repo)
