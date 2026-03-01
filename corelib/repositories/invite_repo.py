from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from corelib.db.models import Invite


class InviteRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def ensure_bootstrap_invite(self) -> Invite:
        stmt = select(Invite).limit(1)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing is not None:
            return existing

        invite = Invite(
            code=self._generate_code(),
            role="user",
            max_uses=None,
            expires_at=None,
            is_active=True,
        )
        self.session.add(invite)
        await self.session.commit()
        await self.session.refresh(invite)
        return invite

    async def create_invite(
        self,
        created_by: int,
        role: str = "user",
        max_uses: int = 1,
        expires_in_days: int = 3,
    ) -> Invite:
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
        invite = Invite(
            code=self._generate_code(),
            created_by=created_by,
            role=role,
            max_uses=max_uses,
            expires_at=expires_at,
            is_active=True,
        )
        self.session.add(invite)
        await self.session.commit()
        await self.session.refresh(invite)
        return invite

    async def get_active_by_code(self, code: str) -> Invite | None:
        stmt = select(Invite).where(Invite.code == code).where(Invite.is_active.is_(True))
        result = await self.session.execute(stmt)
        invite = result.scalar_one_or_none()
        if invite is None:
            return None
        if invite.expires_at and invite.expires_at < datetime.now(timezone.utc):
            return None
        if invite.max_uses is not None and invite.uses_count >= invite.max_uses:
            return None
        return invite

    async def consume_invite(self, invite: Invite) -> Invite:
        invite.uses_count += 1
        if invite.max_uses is not None and invite.uses_count >= invite.max_uses:
            invite.is_active = False
        await self.session.commit()
        await self.session.refresh(invite)
        return invite

    async def get_by_creator(self, creator_id: int) -> list[Invite]:
        stmt = (
            select(Invite)
            .where(Invite.created_by == creator_id)
            .order_by(Invite.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def _generate_code() -> str:
        return token_urlsafe(8).upper().replace("-", "")
