import os
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from corelib.db.models import Base

load_dotenv('.env')
database_url = os.getenv("POSTGRES_URL")

config = context.config
fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=Base.metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    engine = create_async_engine(database_url, poolclass=pool.NullPool)

    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio

    asyncio.run(run_migrations_online())
