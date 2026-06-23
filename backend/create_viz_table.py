"""One-time script to create the job_visualizations table.

Run with: python create_viz_table.py

This is equivalent to the Alembic migration 0027_add_job_visualizations.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))


async def create_table():
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    # Use the same database URL as the app
    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://personalagent:personalagent@localhost:5433/personalagent",
    )
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgresql://") and "+asyncpg" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(database_url, echo=True)

    async with engine.begin() as conn:
        # Check if table already exists
        result = await conn.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'job_visualizations')"
        ))
        exists = result.scalar()

        if exists:
            print("Table 'job_visualizations' already exists. Nothing to do.")
            return

        # Create the table
        await conn.execute(text("""
            CREATE TABLE job_visualizations (
                id UUID PRIMARY KEY,
                job_id UUID NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
                operation_id VARCHAR(255) NOT NULL,
                spec JSONB NOT NULL,
                data JSONB,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                CONSTRAINT uq_job_viz_job_op UNIQUE (job_id, operation_id)
            )
        """))
        print("Successfully created 'job_visualizations' table!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_table())
