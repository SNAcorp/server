from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app import models
from passlib.context import CryptContext

from app.models import User
from app.schemas import UserCreate

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def get_user(db: AsyncSession, user_id: int):
    result = await db.execute(select(models.User).filter(models.User.id == user_id))
    return result.scalars().first()


async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(models.User).filter(models.User.email == email))
    return result.scalars().first()


async def get_all_users(db: AsyncSession):
    result = await db.execute(select(User))
    return result.scalars().all()


async def get_unblocked_users(db: AsyncSession):
    result = await db.execute(select(User).where(User.is_active == True))
    return result.scalars().all()


async def get_blocked_users(db: AsyncSession):
    result = await db.execute(select(User).where(User.is_active == False))
    return result.scalars().all()


async def get_users(db: AsyncSession, skip: int = 0, limit: int = 10):
    result = await db.execute(select(models.User).offset(skip).limit(limit))
    return result.scalars().all()


async def create_user(db: AsyncSession, user: UserCreate):
    hashed_password = pwd_context.hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        first_name=user.first_name,
        last_name=user.last_name,
        middle_name=user.middle_name,
        phone_number=user.phone_number
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def get_unverified_users(db: AsyncSession):
    result = await db.execute(select(User).where(not User.is_verified))
    return result.scalars().all()


async def hash_func(word: str) -> str:
    return pwd_context.hash(word)


async def update_user_role(db: AsyncSession, user: models.User, role: str):
    user.role = role
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_status(db: AsyncSession, user: models.User, is_verified: bool):
    user.is_verified = is_verified
    await db.commit()
    await db.refresh(user)
    return user


async def block_user(db: AsyncSession, user: models.User):
    user.block_date = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    return user


async def unblock_user(db: AsyncSession, user: models.User):
    user.block_date = None
    await db.commit()
    await db.refresh(user)
    return user


def user_to_dict(user: User):
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "middle_name": user.middle_name,
        "phone_number": user.phone_number,
        "role": user.role,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "is_verified": user.is_verified,
        "registration_date": user.registration_date.isoformat() if user.registration_date else None,
        "block_date": user.block_date.isoformat() if user.block_date else None
    }


async def update_user(db: AsyncSession, user: User, user_data: dict):
    for key, value in user_data.items():
        setattr(user, key, value)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
