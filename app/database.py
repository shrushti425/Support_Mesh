import logging
from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

logger = logging.getLogger("supportmesh.database")

# Ensure the database URL uses the asyncpg driver
db_url = settings.DATABASE_URL
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)

# Create engine
engine = create_async_engine(
    db_url,
    echo=False,
    future=True,
)

# Async session factory
async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for models
class Base(DeclarativeBase):
    pass

# Dependency to get session
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Initialize Database
async def init_db() -> None:
    try:
        async with engine.begin() as conn:
            # Enable the pgvector extension in the database
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database and vector extension initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise
