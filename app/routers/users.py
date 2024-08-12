from fastapi import (APIRouter, Depends, Request, Form)
from fastapi.templating import (Jinja2Templates)
from fastapi.responses import (JSONResponse, RedirectResponse)
from fastapi.exceptions import (HTTPException)

from sqlalchemy.ext.asyncio import (AsyncSession)

from app import (models)
from app.database import (get_db)
from app.schemas import (User)
from app.crud import (get_users, hash_func)
from app.dependencies import (get_current_user)
from app.utils import (verify_password)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_model=list[User])
async def read_users(request: Request,
                     skip: int = 0,
                     limit: int = 10,
                     current_user: User = Depends(get_current_user)):
    if current_user is None:
        return RedirectResponse("/login", 303)
    users = await get_users(skip=skip, limit=limit)
    return templates.TemplateResponse("users_list.html", {"request": request, "users": users})


@router.get("/me/", response_model=User)
async def read_user_me(request: Request,
                       current_user: User = Depends(get_current_user)):
    if current_user is None:
        return RedirectResponse("/login", 303)
    return templates.TemplateResponse("profile.html", {"request": request, "current_user": current_user})


@router.post("/me/change-password")
async def change_password(old_password: str = Form(...),
                          new_password: str = Form(...),
                          confirm_password: str = Form(...),
                          db: AsyncSession = Depends(get_db),
                          current_user: models.User = Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(401, "Unauthorized")
    if not verify_password(old_password, current_user.hashed_password):
        return JSONResponse(status_code=400,
                            content={"success": False, "message": "Incorrect current password"})
    new_password_hash = await hash_func(new_password)
    if verify_password(new_password, current_user.hashed_password):
        return JSONResponse(status_code=400,
                            content={"success": False, "message": "New and old passwords are the same"})
    if new_password != confirm_password:
        return JSONResponse(status_code=400,
                            content={"success": False, "message": "New passwords do not match"})

    current_user.hashed_password = new_password_hash
    db.add(current_user)
    await db.commit()

    return JSONResponse(status_code=200,
                        content={"success": True, "message": "Password successfully changed"})
