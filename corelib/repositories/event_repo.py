from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from corelib.db.models import Event


class EventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(
        self,
        user_id: int,
        title: str,
        start_time: datetime,
        location: str | None,
        recurrence: str | None,
    ) -> Event:
        event = Event(
            user_id=user_id,
            title=title,
            start_time=start_time,
            location=location,
            recurrence=recurrence,
        )
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)
        return event

    async def get_upcoming_for_date(self, user_id: int, day_start: datetime, day_end: datetime) -> list[Event]:
        stmt = (
            select(Event)
            .where(Event.user_id == user_id)
            .where(Event.start_time >= day_start)
            .where(Event.start_time <= day_end)
            .order_by(Event.start_time)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
