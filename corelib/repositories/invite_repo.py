from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from corelib.db.models import Invite


class InviteRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active_by_code(self, code: str) -> Invite | None:
        stmt = select(Invite).where(Invite.code == code).where(Invite.is_active.is_(True))
        result = await self.session.execute(stmt)
        invite = result.scalar_one_or_none()
        if invite is None:
            return None
        if invite.expires_at and invite.expires_at < datetime.now(timezone.utc):
            return None
        if invite.used_at is not None:
            return None
        return invite

    async def mark_used(self, invite: Invite, used_by: int) -> Invite:
        invite.used_by = used_by
        invite.used_at = datetime.now(timezone.utc)
        invite.is_active = False
        await self.session.commit()
        await self.session.refresh(invite)
        return invite
