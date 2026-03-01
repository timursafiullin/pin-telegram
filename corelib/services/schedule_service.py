from corelib.repositories import EventRepository, ReminderRepository
from datetime import datetime, timedelta

class ScheduleService:
    def __init__(self, event_repo: EventRepository, reminder_repo: ReminderRepository):
        self.event_repo = event_repo
        self.reminder_repo = reminder_repo

    async def create_event(self, user_id: int, title: str, start_time: datetime, location: str | None, recurrence: str | None, remind_before_minutes: int = 60):
        event = await self.event_repo.add(user_id, title, start_time, location, recurrence)
        remind_at = start_time - timedelta(minutes=remind_before_minutes)
        await self.reminder_repo.add(event.id, remind_at)
        return event