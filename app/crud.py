from passlib.context import (CryptContext)
import datetime
from fastapi.exceptions import HTTPException
from fastapi import Request
from sqlalchemy.ext.asyncio import (AsyncSession)
from sqlalchemy.future import (select)

from app.models import (User)
from app.schemas import (UserCreate)
from app.logging_config import log
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def get_user(request: Request, user_id: int, db: AsyncSession, current_user: User = None):
    if current_user is None:
        current_user_id = -3
    else:
        current_user_id = current_user.id
    query = await db.execute(select(User).filter(User.id == user_id))
    result = query.scalars().first()
    if result is None:
        log.bind(type="admins",
                 method=request.method,
                 current_user_id=current_user_id,
                 url=str(request.url),
                 headers=dict(request.headers),
                 params=dict(request.query_params)
                 ).error(f"Try to take info about user: {user_id}. But user not found")
        if current_user is None:
            return None
        raise HTTPException(400, detail="User not found")
    log.bind(type="admins",
             method=request.method,
             current_user_id=current_user_id,
             url=str(request.url),
             headers=dict(request.headers),
             params=dict(request.query_params)
             ).info(f"Gained info about user: {user_id}")
    return result


async def check_email(request: Request, email: str, db: AsyncSession):
    query = await db.execute(select(User).filter(User.email == email))
    result = query.scalars().first()
    if result is None:
        log.bind(type="admins",
                 method=request.method,
                 current_user_id=-3,
                 url=str(request.url),
                 headers=dict(request.headers),
                 params=dict(request.query_params)
                 ).error(f"Email {email} not found in database")
        return True
    log.bind(type="admins",
             method=request.method,
             current_user_id=-3,
             url=str(request.url),
             headers=dict(request.headers),
             params=dict(request.query_params)
             ).info(f"Email {email} was found in database")
    return False


async def get_user_by_email(request: Request, email: str, db: AsyncSession, current_user: User = None):
    if current_user is None:
        current_user_id = -3
    else:
        current_user_id = current_user.id
    query = await db.execute(select(User).filter(User.email == email))
    result = query.scalars().first()
    if result is None:
        log.bind(type="admins",
                 method=request.method,
                 current_user_id=current_user_id,
                 url=str(request.url),
                 headers=dict(request.headers),
                 params=dict(request.query_params)
                 ).error(f"Try to take info about user: {email}. But user not found")
        if current_user is None:
            return None
        raise HTTPException(400, detail="User not found")
    log.bind(type="admins",
             method=request.method,
             current_user_id=-current_user_id,
             url=str(request.url),
             headers=dict(request.headers),
             params=dict(request.query_params)
             ).info(f"Gained info about user: {email}")
    return result


async def get_all_users(request: Request, current_user: User, db: AsyncSession):
    result = await db.execute(select(User))
    log.bind(type="admins",
             method=request.method,
             current_user_id=current_user.id,
             url=str(request.url),
             headers=dict(request.headers),
             params=dict(request.query_params)
             ).info(f"Gained info about all users")
    return result.scalars().all()


async def get_unblocked_users(request: Request, current_user: User, db: AsyncSession):
    result = await db.execute(select(User).where(User.is_active is True))
    log.bind(type="admins",
             method=request.method,
             current_user_id=current_user.id,
             url=str(request.url),
             headers=dict(request.headers),
             params=dict(request.query_params)
             ).info(f"Gained info about unblocked users")
    return result.scalars().all()


async def get_blocked_users(request: Request, current_user: User, db: AsyncSession):
    result = await db.execute(select(User).where(User.is_active is False))
    log.bind(type="admins",
             method=request.method,
             current_user_id=current_user.id,
             url=str(request.url),
             headers=dict(request.headers),
             params=dict(request.query_params)
             ).info(f"Gained info about blocked users")
    return result.scalars().all()


async def get_users(request: Request, current_user: User, db: AsyncSession, skip: int = 0, limit: int = 10):
    result = await db.execute(select(User).offset(skip).limit(limit))
    log.bind(type="admins",
             method=request.method,
             current_user_id=current_user.id,
             url=str(request.url),
             headers=dict(request.headers),
             params=dict(request.query_params)
             ).info(f"Gained info from {skip} to {skip + limit} users")
    return result.scalars().all()


async def create_user(request: Request, user: UserCreate, db: AsyncSession, current_user: User = None):
    hashed_password = pwd_context.hash(user.password)
    if user.email == "stepanov.iop@gmail.com":
        db_user = User(
            email=user.email,
            hashed_password=hashed_password,
            first_name=user.first_name,
            last_name=user.last_name,
            middle_name=user.middle_name,
            phone_number=user.phone_number,
            role="superadmin",
            is_verified=True,
            is_superuser=True
        )
    else:
        db_user = User(
            email=user.email,
            hashed_password=hashed_password,
            first_name=user.first_name,
            last_name=user.last_name,
            middle_name=user.middle_name,
            phone_number=user.phone_number
        )
    db.add(db_user)
    await db.flush()  # Flush to ensure that db_user gets an ID
    await db.refresh(db_user)  # Refresh the instance to make sure we have all data, including generated fields
    await db.commit()  # Commit the transaction

    log.bind(type="admins",
             method=request.method,
             current_user_id=-3,
             url=str(request.url),
             headers=dict(request.headers),
             params=dict(request.query_params)
             ).info(f"Created user {db_user.id}")
    return db_user



async def get_unverified_users(request: Request, current_user: User, db: AsyncSession):
    result = await db.execute(select(User).where(not User.is_verified))
    log.bind(type="admins",
             method=request.method,
             current_user_id=current_user.id,
             url=str(request.url),
             headers=dict(request.headers),
             params=dict(request.query_params)
             ).info(f"Gained info about unverified users")
    return result.scalars().all()


async def hash_func(word: str) -> str:
    return pwd_context.hash(word)


async def update_user_role(request: Request, current_user: User, user: User, role: str, db: AsyncSession):
    user.role = role
    await db.commit()
    await db.refresh(user)
    log.bind(type="admins",
             method=request.method,
             current_user_id=current_user.id,
             url=str(request.url),
             headers=dict(request.headers),
             params=dict(request.query_params)
             ).info(f"Updated user role: {user.id}")
    return user


async def update_user_status(request: Request, current_user: User, user: User, is_verified: bool, db: AsyncSession):
    user.is_verified = is_verified
    await db.commit()
    await db.refresh(user)
    log.bind(type="admins",
             method=request.method,
             current_user_id=current_user.id,
             url=str(request.url),
             headers=dict(request.headers),
             params=dict(request.query_params)
             ).info(f"Verified user: {user.id}")
    return user


async def block_user(request: Request, current_user: User, user: User, db: AsyncSession):
    user.is_active = False
    user.block_date = datetime.datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    log.bind(type="admins",
             method=request.method,
             current_user_id=current_user.id,
             url=str(request.url),
             headers=dict(request.headers),
             params=dict(request.query_params)
             ).info(f"Blocked user: {user.id}")
    return user


async def unblock_user(request: Request, current_user: User, user: User, db: AsyncSession):
    user.is_active = True
    user.block_date = None
    await db.commit()
    await db.refresh(user)
    log.bind(type="admins",
             method=request.method,
             current_user_id=current_user.id,
             url=str(request.url),
             headers=dict(request.headers),
             params=dict(request.query_params)
             ).info(f"Unblocked user: {user.id}")
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


async def update_user(request: Request, current_user: User, user: User, user_data: dict, db: AsyncSession):
    old_data = user_to_dict(user)
    for key, value in user_data.items():
        setattr(user, key, value)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    log.bind(type="admins",
             method=request.method,
             current_user_id=current_user.id,
             url=str(request.url),
             headers=dict(request.headers),
             old_user_info=old_data,
             new_user_info=user_to_dict(user),
             params=dict(request.query_params)
             ).info(f"Updated user: {user.id}")
    return user
