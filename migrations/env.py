import os
from dotenv import load_dotenv

from logging.config import fileConfig
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from alembic import context
from sqlalchemy import inspect

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

async def run_migrations_online():
    engine = create_async_engine(database_url, echo=True)

    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with engine.connect() as connection:
        # Inspect the connection to check for the version table instead of using has_table()
        inspector = inspect(connection)
        if not inspector.has_table('alembic_version'):
            raise Exception("The alembic_version table does not exist!")

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        # Use async context manager for transactions
        async with connection.begin():
            await context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio
    asyncio.run(run_migrations_online())