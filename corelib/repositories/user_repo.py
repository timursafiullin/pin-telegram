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
        return result.scalars().first()

    async def create_pending_telegram_user(
        self,
        telegram_id: str,
        name: str | None,
        role: str = "tester",
        language: str | None = None,
    ) -> User:
        user = User(
            telegram_id=telegram_id,
            name=name,
            role=role,
            language=(language or "en"),
            is_active=False,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update_profile(self, user: User, name: str | None = None, language: str | None = None) -> User:
        user.name = name
        if language:
            user.language = language
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def activate_user_with_timezone(self, user: User, timezone: str, role: str | None = None) -> User:
        user.timezone = timezone
        if role is not None:
            user.role = role
        user.is_active = True
        await self.session.commit()
        await self.session.refresh(user)
        return user
