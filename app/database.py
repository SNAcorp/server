import os
import asyncio
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError

# Получение URL базы данных из переменной окружения
DATABASE_URL = os.getenv('DATABASE_URL')

# Создание асинхронного движка базы данных
engine = create_async_engine(DATABASE_URL, echo=True)

# Создание фабрики сессий
SessionLocal = sessionmaker(autocommit=False, expire_on_commit=False, autoflush=False, bind=engine, class_=AsyncSession)

# Настройка логирования с ротацией и фильтрацией по типу "db"
logger.add("/logs/db.log", rotation="1 day", retention="7 days", level="DEBUG", filter=lambda record: record["extra"].get("type") == "db")

# Максимальное количество попыток выполнения транзакции
MAX_RETRIES = 5

async def get_db() -> AsyncSession:
    """
    Получение асинхронной сессии базы данных с логированием, управлением контекстом,
    защитой от коллизий и повторными попытками транзакций.
    """
    async with SessionLocal() as session:
        logger.bind(type="db").info("Database session started")
        retries = 0
        try:
            while retries < MAX_RETRIES:
                try:
                    async with session.begin():
                        # Устанавливаем уровень изоляции транзакции на максимально строгий
                        await session.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
                        yield session
                        logger.bind(type="db").info("Database session successfully committed")
                        break  # Выходим из цикла при успешной транзакции
                except IntegrityError as e:
                    await session.rollback()  # Откат транзакции при конфликте версий
                    retries += 1
                    logger.bind(type="db").warning(
                        f"IntegrityError: Collision detected and transaction rolled back. Retrying {retries}/{MAX_RETRIES}..."
                    )
                    if retries >= MAX_RETRIES:
                        logger.bind(type="db").error(
                            f"Transaction failed after {MAX_RETRIES} attempts. Aborting."
                        )
                        raise  # Повторное возбуждение исключения после достижения лимита попыток
                    await asyncio.sleep(2 ** retries)  # Экспоненциальное увеличение времени ожидания перед повторной попыткой
                except OperationalError as e:
                    await session.rollback()  # Откат транзакции в случае операционной ошибки
                    retries += 1
                    logger.bind(type="db").warning(
                        f"OperationalError: Retry {retries}/{MAX_RETRIES}..."
                    )
                    if retries >= MAX_RETRIES:
                        logger.bind(type="db").error(
                            f"Transaction failed after {MAX_RETRIES} attempts. Aborting."
                        )
                        raise
                    await asyncio.sleep(2 ** retries)  # Экспоненциальная задержка перед повторной попыткой
                except SQLAlchemyError as e:
                    await session.rollback()  # Откат транзакции в случае других ошибок SQLAlchemy
                    logger.bind(type="db").error(f"Database session rollback due to error: {str(e)}")
                    raise  # Повторное возбуждение исключения для дальнейшей обработки
            else:
                logger.bind(type="db").error("Max retries reached, transaction aborted.")
        finally:
            logger.bind(type="db").info("Database session closed")
