from datetime import datetime, timedelta

from corelib.repositories import EventRepository, ReminderRepository


class ScheduleService:
    def __init__(self, event_repo: EventRepository, reminder_repo: ReminderRepository):
        self.event_repo = event_repo
        self.reminder_repo = reminder_repo

    async def create_event(
        self,
        user_id: int,
        title: str,
        start_time: datetime,
        location: str | None,
        recurrence: str | None,
        remind_before_minutes: int = 60,
    ):
        event = await self.event_repo.add(user_id, title, start_time, location, recurrence)
        remind_at = start_time - timedelta(minutes=remind_before_minutes)
        await self.reminder_repo.add(event.id, remind_at)
        return event

    async def get_upcoming_events(self, user_id: int, day: datetime) -> list:
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
        return await self.event_repo.get_upcoming_for_date(user_id, day_start, day_end)
