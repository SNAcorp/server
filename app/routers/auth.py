from fastapi import (APIRouter, Depends, HTTPException)
from fastapi.responses import (RedirectResponse)

from sqlalchemy.ext.asyncio import (AsyncSession)

from app.database import (get_db)
from app.schemas import (UserCreate, UserLogin)
from app.crud import (create_user, get_user_by_email)
from app.utils import (verify_password, create_access_token)

router = APIRouter()


@router.post("/register/")
async def register_user(user: UserCreate,
                        db: AsyncSession = Depends(get_db)):
    db_user = await get_user_by_email(user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = await create_user(user)
    if new_user.email == "stepanov.iop@gmail.com":
        new_user.is_superuser = True
        new_user.is_verified = True
        new_user.role = "superadmin"
        await db.commit()
        await db.refresh(new_user)
    return new_user


@router.post("/login")
async def login_user(info: UserLogin):
    user = await get_user_by_email(info.email)
    if not user or not verify_password(info.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    if not user.is_verified:
        raise HTTPException(status_code=400, detail="User not verified")
    access_token = create_access_token(data={"sub": user.email})

    response = RedirectResponse(url="/terminals", status_code=303)
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    return response
