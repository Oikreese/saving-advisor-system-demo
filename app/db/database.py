"""
Database connection and session management
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator

from app.core.config import settings

logger = logging.getLogger(__name__)

# Database engine
engine = None
async_session_maker = None


def get_database_url() -> str:
    """Get database connection URL"""
    # Select database based on DB_DRIVER configuration
    if settings.DB_DRIVER == "sqlite":
        logger.info("Using SQLite database")
        return "sqlite+aiosqlite:///./saving_advisor.db"
    
    # Use PostgreSQL
    try:
        db_user = settings.DB_USER
        db_password = settings.DB_PASSWORD
        db_host = settings.DB_HOST
        db_port = settings.DB_PORT
        db_name = settings.DB_NAME
        
        logger.info(f"Using PostgreSQL database: {db_host}:{db_port}/{db_name}")
        return f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    except AttributeError as e:
        # If PostgreSQL is not configured, fall back to SQLite
        logger.warning(f"PostgreSQL configuration incomplete ({e}), falling back to SQLite")
        return "sqlite+aiosqlite:///./saving_advisor.db"


async def init_db():
    """Initialize database connection"""
    global engine, async_session_maker
    
    database_url = get_database_url()
    logger.info(f"Initializing database connection: {database_url.split('@')[-1] if '@' in database_url else 'SQLite'}")
    
    # Create async engine
    if settings.ENVIRONMENT == "development" or "sqlite" in database_url:
        # SQLite or development environment uses NullPool
        engine = create_async_engine(
            database_url,
            echo=settings.DEBUG,
            poolclass=NullPool,
        )
    else:
        # Production environment PostgreSQL uses connection pool
        engine = create_async_engine(
            database_url,
            echo=settings.DEBUG,
            pool_size=10,
            max_overflow=20,
        )
    
    # Create session factory
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    # Create all tables
    from app.db.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database initialization successful")


async def close_db():
    """Close database connection"""
    global engine
    if engine:
        await engine.dispose()
        logger.info("Database connection closed")


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session context manager"""
    if async_session_maker is None:
        raise RuntimeError("Database not initialized. Please call init_db() first")
    
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Database session getter for FastAPI dependency injection"""
    async with get_db_session() as session:
        yield session

