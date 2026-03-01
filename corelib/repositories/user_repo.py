from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from corelib.db.models import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_telegram_id(self, telegram_id: str) -> User | None:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_pending_telegram_user(
        self,
        telegram_id: str,
        name: str | None,
        role: str = "tester",
    ) -> User:
        user = User(
            telegram_id=telegram_id,
            name=name,
            role=role,
            is_active=False,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def activate_user_with_timezone(self, user: User, timezone: str) -> User:
        user.timezone = timezone
        user.is_active = True
        await self.session.commit()
        await self.session.refresh(user)
        return user
