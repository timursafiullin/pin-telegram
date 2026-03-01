from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from corelib.config import settings


_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


def init_engine() -> AsyncEngine:
    """Initialize and return a shared async SQLAlchemy engine."""
    global _engine, _session_maker

    if _engine is None:
        _engine = create_async_engine(
            settings.POSTGRES_URL,
            pool_pre_ping=True,
            echo=settings.DATABASE_ECHO,
        )
        _session_maker = async_sessionmaker(
            _engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """Return a shared async session factory."""
    global _session_maker

    if _session_maker is None:
        init_engine()

    if _session_maker is None:
        raise RuntimeError("Session maker is not initialized")

    return _session_maker


async def dispose_engine() -> None:
    """Dispose shared async engine and reset factory references."""
    global _engine, _session_maker

    if _engine is not None:
        await _engine.dispose()

    _engine = None
    _session_maker = None


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async SQLAlchemy session."""
    session_maker = get_session_maker()

    async with session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
