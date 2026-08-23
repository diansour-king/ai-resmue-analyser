import asyncio

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from careerlayer_api import models  # noqa: F401  imported so autogenerate sees the tables
from careerlayer_api.db import Base
from careerlayer_api.settings import get_settings

target_metadata = Base.metadata


def run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def main() -> None:
    engine = create_async_engine(get_settings().database_url)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(run_migrations)
            await connection.commit()
    finally:
        await engine.dispose()


# Alembic's offline mode emits SQL scripts for a DBA to apply by hand. Migrations here
# always run against a live database from CI or the deploy step, so that path is omitted
# rather than left as untested generated code.
if context.is_offline_mode():
    raise RuntimeError("offline migrations are not supported; run against a live database")

asyncio.run(main())
