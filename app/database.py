import os

from sqlalchemy.ext.asyncio import (create_async_engine, AsyncSession)
from sqlalchemy.orm import (sessionmaker)

DATABASE_URL = os.getenv('DATABASE_URL')
# DATABASE_URL = "postgresql+asyncpg://nikitastepanov@localhost/terminals"
# os.getenv('DATABASE_URL',
engine = create_async_engine(DATABASE_URL, echo=True)  # Создание асинхронного движка базы данных
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)


async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
