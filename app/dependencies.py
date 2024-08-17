import os
from pathlib import Path
import aiofiles

import jwt

from fastapi import (Depends, HTTPException, Request)
from fastapi.security import (OAuth2PasswordBearer)
from fastapi.responses import (RedirectResponse)

from sqlalchemy.ext.asyncio import (AsyncSession, create_async_engine)
from sqlalchemy.orm import (sessionmaker)

from app.crud import (get_user_by_email, get_user)
from app.database import (get_db)
from app.schemas import (User)

# DATABASE_URL = "postgresql+asyncpg://nikitastepanov@localhost/terminals"
from app.utils import load_keys

DATABASE_URL = os.getenv('DATABASE_URL')

engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


ALGORITHM = "RS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 540


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)):
    from app.utils import PUBLIC_KEY
    if PUBLIC_KEY is None:
        await load_keys()

    token = request.cookies.get("access_token")
    if not token:
        return None

    try:
        print("decode:", PUBLIC_KEY)
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Unauthorized")

    user = await get_user_by_email(email, db)
    if user is None or not user.is_active or user.block_date is not None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return user


async def get_admin_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_superuser:
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail=f"Not enough permissions")

    return current_user


async def get_superadmin_user(current_user: User = Depends(get_current_user)):
    if current_user.role != "superadmin" or not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user


async def check_user_for_superuser(user_id: int,
                                   current_user: User,
                                   db: AsyncSession):
    if current_user is None:
        raise HTTPException(401, "Unauthorized")
    user = await get_user(user_id, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_superuser and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Permission denied")

    return user


async def check_user(user_id: int,
                     current_user: User,
                     db: AsyncSession):
    if current_user is None:
        raise HTTPException(401, "Unauthorized")
    user = await get_user(user_id, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
