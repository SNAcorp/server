import os
from loguru import logger
from sqlalchemy.ext.asyncio import (create_async_engine, AsyncSession)
from sqlalchemy.orm import (sessionmaker)

DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_async_engine(DATABASE_URL, echo=True)  # Создание асинхронного движка базы данных
SessionLocal = sessionmaker(autocommit=False, expire_on_commit=False, autoflush=False, bind=engine, class_=AsyncSession)

logger.add("/logs/db.log", rotation="1 day", retention="7 days", level="DEBUG")


async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        logger.info("Database session started")
        yield session
        logger.info("Database session closed")
