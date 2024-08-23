import os

import jwt
from fastapi import (Depends, HTTPException, Request)
from fastapi.security import (OAuth2PasswordBearer)
from sqlalchemy.ext.asyncio import (AsyncSession, create_async_engine)
from sqlalchemy.orm import (sessionmaker)

from app.crud import (get_user_by_email, get_user)
from app.database import (get_db)
from app.logging_config import log
from app.schemas import (User)
# DATABASE_URL = "postgresql+asyncpg://nikitastepanov@localhost/terminals"
from app.utils import load_keys, SPECIAL_TOKEN

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
        log.bind(type="users",
                 method=request.method,
                 current_user_id=-1,
                 url=str(request.url),
                 headers=dict(request.headers),
                 params=dict(request.query_params)
                 ).info(f"Guest visiting the site")
        raise HTTPException(status_code=401, detail="Unauthorized")
    user = None
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        special_token = payload.get("special_token")
        if user_id is None or special_token != SPECIAL_TOKEN:
            log.bind(type="users",
                     method=request.method,
                     current_user_id=-2,
                     url=str(request.url),
                     headers=dict(request.headers),
                     params=dict(request.query_params)
                     ).error(f"Someone try to do fake token")
            raise HTTPException(status_code=401, detail="Unauthorized")
        user = await get_user(request=request, user_id=user_id, db=db)
    except jwt.PyJWTError:
        log.bind(type="users",
                 method=request.method,
                 current_user_id=user.id if user else -2,
                 url=str(request.url),
                 headers=dict(request.headers),
                 params=dict(request.query_params)
                 ).info(f"User's session ended")
        raise HTTPException(status_code=401, detail="Unauthorized")

    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not user.is_active or user.block_date is not None:
        log.bind(type="users",
                 method=request.method,
                 current_user_id=user.id,
                 url=str(request.url),
                 headers=dict(request.headers),
                 params=dict(request.query_params)
                 ).error(f"Permission denied")
        raise HTTPException(status_code=403, detail="Permission Denied")

    return user


async def get_admin_user(request: Request, current_user: User = Depends(get_current_user)):
    if not current_user.is_superuser:
        if current_user.role != "admin":
            log.bind(type="admins",
                     method=request.method,
                     current_user_id=current_user.id,
                     url=str(request.url),
                     headers=dict(request.headers),
                     params=dict(request.query_params)
                     ).error(f"Permission denied")
            raise HTTPException(status_code=403, detail="Permission denied")

    return current_user


async def get_superadmin_user(request: Request, current_user: User = Depends(get_current_user)):
    if not current_user.is_superuser:
        log.bind(type="admins",
                 method=request.method,
                 current_user_id=current_user.id,
                 url=str(request.url),
                 headers=dict(request.headers),
                 params=dict(request.query_params)
                 ).error(f"Permission denied")
        raise HTTPException(status_code=403, detail="Permission denied")
    return current_user


async def check_user_for_superuser(request: Request,
                                   user_id: int,
                                   current_user: User,
                                   db: AsyncSession):
    user = await check_user(request, user_id, current_user, db)

    if user.is_superuser and not current_user.is_superuser:
        log.bind(type="admins",
                 method=request.method,
                 current_user_id=current_user.id,
                 url=str(request.url),
                 headers=dict(request.headers),
                 params=dict(request.query_params)
                 ).error(f"Permission denied")
        raise HTTPException(status_code=403, detail="Permission denied")

    return user


async def check_user(request: Request,
                     user_id: int,
                     current_user: User,
                     db: AsyncSession):

    user = await get_user(request=request, user_id=user_id,
                          current_user=current_user, db=db)
    if user is None:
        log.bind(type="admins",
                 method=request.method,
                 current_user_id=current_user.id,
                 url=str(request.url),
                 headers=dict(request.headers),
                 params=dict(request.query_params)
                 ).error(f"User not found")
        raise HTTPException(status_code=404, detail="User not found")

    return user
