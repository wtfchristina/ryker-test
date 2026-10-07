from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Optional
import uuid
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

DATABASE_URL = "postgresql+asyncpg://ryker_app_user:SecureClientAppPass123!@localhost:5432/ryker_vault"

engine = create_async_engine(
    DATABASE_URL,
    poolclass=NullPool,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession,
)

@asynccontextmanager
async def get_tenant_db(org_id: Optional[uuid.UUID] = None) -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            if org_id:
                await session.execute(
                    text("SELECT set_config('app.current_org_id', :org_id, false)"),
                    {"org_id": str(org_id)},
                )
            else:
                await session.execute(
                    text("SELECT set_config('app.current_org_id', '', false)")
                )
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
