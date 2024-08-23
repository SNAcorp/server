from fastapi import (APIRouter, Depends, HTTPException, Request)
from fastapi.responses import (RedirectResponse)

from sqlalchemy.ext.asyncio import (AsyncSession)

from app.database import (get_db)
from app.dependencies import get_current_user
from app.schemas import (UserCreate, UserLogin, User)
from app.crud import (create_user, get_user_by_email, check_email)
from app.templates import app_templates
from app.utils import (verify_password, create_access_token)
from app.logging_config import log

router = APIRouter()


@router.get("/login")
def admin_panel(request: Request,
                current_user: User = Depends(get_current_user)):
    if current_user is not None:
        return RedirectResponse("/orders", 303)
    return app_templates.TemplateResponse("login_register.html",
                                          {"request": request})


@router.get("/verify")
def admin_panel(request: Request,
                current_user: User = Depends(get_current_user)):
    return app_templates.TemplateResponse("account_verification.html",
                                          {"request": request})


@router.post("/register/")
async def register_user(request: Request,
                        user: UserCreate,
                        db: AsyncSession = Depends(get_db)):
    is_email_valid = await check_email(request=request, email=user.email, db=db)
    if is_email_valid is False:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = await create_user(request=request, user=user, db=db)

    access_token = await create_access_token(request=request, current_user=new_user, data={"sub": new_user.id})

    response = RedirectResponse(url="/terminals", status_code=303)
    response.set_cookie(key="access_token", value=access_token, httponly=True)

    return response


@router.post("/login")
async def login_user(request: Request,
                     info: UserLogin,
                     db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(request=request, email=info.email, db=db)
    if user is None or not verify_password(info.password, user.hashed_password):
        if user is not None:
            log.bind(type="admins",
                     method=request.method,
                     current_user_id=user.id,
                     url=str(request.url),
                     headers=dict(request.headers),
                     params=dict(request.query_params)
                     ).error(f"Try to login with error password: {info.password}")
        raise HTTPException(status_code=400, detail="Invalid credentials")
    if not user.is_verified:
        return RedirectResponse("/auth/verify", status_code=303)
    access_token = await create_access_token(request=request, current_user=user, data={"sub": user.id})

    response = RedirectResponse(url="/terminals", status_code=303)
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    return response
