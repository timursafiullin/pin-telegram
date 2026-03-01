from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from corelib.db.models import Reminder


class ReminderRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, event_id: int, remind_at: datetime) -> Reminder:
        reminder = Reminder(event_id=event_id, remind_at=remind_at)
        self.session.add(reminder)
        await self.session.commit()
        await self.session.refresh(reminder)
        return reminder
