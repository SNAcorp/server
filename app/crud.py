from passlib.context import (CryptContext)
from datetime import (datetime)

from fastapi import (Depends)

from sqlalchemy.ext.asyncio import (AsyncSession)
from sqlalchemy.future import (select)

from app.database import (get_db)
from app.models import (User)
from app.schemas import (UserCreate)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter(User.id == user_id))
    return result.scalars().first()


async def get_user_by_email(email: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter(User.email == email))
    return result.scalars().first()


async def get_all_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    return result.scalars().all()


async def get_unblocked_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.is_active is True))
    return result.scalars().all()


async def get_blocked_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.is_active is False))
    return result.scalars().all()


async def get_users(skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).offset(skip).limit(limit))
    return result.scalars().all()


async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    hashed_password = pwd_context.hash(user.password)
    db_user = User(
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


async def get_unverified_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(not User.is_verified))
    return result.scalars().all()


async def hash_func(word: str) -> str:
    return pwd_context.hash(word)


async def update_user_role(user: User, role: str, db: AsyncSession = Depends(get_db)):
    user.role = role
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_status(user: User, is_verified: bool, db: AsyncSession = Depends(get_db)):
    user.is_verified = is_verified
    await db.commit()
    await db.refresh(user)
    return user


async def block_user(user: User, db: AsyncSession = Depends(get_db)):
    user.block_date = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    return user


async def unblock_user(user: User, db: AsyncSession = Depends(get_db)):
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


async def update_user(user: User, user_data: dict, db: AsyncSession = Depends(get_db)):
    for key, value in user_data.items():
        setattr(user, key, value)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
