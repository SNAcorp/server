from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models import TerminalState
import os

DATABASE_URL = os.getenv('DATABASE_URL')
# DATABASE_URL = "postgresql+asyncpg://nikitastepanov@localhost/terminals"
# os.getenv('DATABASE_URL',
engine = create_async_engine(DATABASE_URL, echo=True)  # Создание асинхронного движка базы данных
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)


async def get_db():
    async with SessionLocal() as session:
        yield session  # Создание асинхронной сессии для взаимодействия с базой данных
