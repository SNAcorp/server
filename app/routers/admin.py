from fastapi import (APIRouter,
                     Depends,
                     Request)
from fastapi.responses import (JSONResponse,
                               HTMLResponse)
from sqlalchemy.ext.asyncio import (AsyncSession)

from app.templates import (app_templates)
from app.logging_config import (log)
from app.database import (get_db)
from app.schemas import (User)
from app.crud import (update_user_role,
                      block_user,
                      unblock_user,
                      update_user,
                      user_to_dict,
                      get_all_users,
                      get_unblocked_users,
                      get_blocked_users,
                      get_unverified_users)
from app.dependencies import (get_admin_user,
                              check_user,
                              check_user_for_superuser)

router = APIRouter()


@router.get("/panel", response_class=HTMLResponse)
async def admin_panel(request: Request, db: AsyncSession = Depends(get_db),
                      current_user: User = Depends(get_admin_user)):
    all_users = await get_all_users(request=request, current_user=current_user, db=db)
    unblocked_users = await get_unblocked_users(request=request, current_user=current_user, db=db)
    blocked_users = await get_blocked_users(request=request, current_user=current_user, db=db)
    unverified_users = []
    if current_user.is_superuser:
        unverified_users = await get_unverified_users(request=request, current_user=current_user, db=db)
    log.bind(type="admins",
             method=request.method,
             current_user_id=current_user.id,
             url=str(request.url),
             headers=dict(request.headers),
             params=dict(request.query_params)
             ).info(f"Gained access to admin panel")
    return app_templates.TemplateResponse("admin_panel.html", {
        "request": request,
        "current_user": current_user,
        "all_users": all_users,
        "unblocked_users": unblocked_users,
        "blocked_users": blocked_users,
        "unverified_users": unverified_users
    })


@router.put("/role/{user_id}")
async def change_user_role(request: Request,
                           user_id: int,
                           db: AsyncSession = Depends(get_db),
                           current_user: User = Depends(get_admin_user)):
    user = await check_user(request=request, user_id=user_id,
                            current_user=current_user, db=db)

    data = await request.json()

    updated_user = await update_user_role(request=request, current_user=current_user,
                                          user=user, role=data["role"], db=db)
    return updated_user


@router.get("/user/{user_id}", response_class=JSONResponse)
async def get_user_details(request: Request,
                           user_id: int,
                           db: AsyncSession = Depends(get_db),
                           current_user: User = Depends(get_admin_user)):

    user = await check_user(request=request, user_id=user_id,
                            current_user=current_user, db=db)
    user_data = user_to_dict(user)

    return JSONResponse(content=user_data)


@router.put("/user/{user_id}", response_class=JSONResponse)
async def update_user_details(request: Request,
                              user_id: int,
                              user_data: dict,
                              current_user: User = Depends(get_admin_user),
                              db: AsyncSession = Depends(get_db)):
    user = await check_user(request=request, user_id=user_id,
                            current_user=current_user, db=db)
    updated_user = await update_user(request=request, current_user=current_user,
                                     user=user, user_data=user_data, db=db)
    user_data = user_to_dict(updated_user)

    return JSONResponse(content=user_data)


@router.put("/block/{user_id}")
async def block_user_route(request: Request,
                           user_id: int,
                           db: AsyncSession = Depends(get_db),
                           current_user: User = Depends(get_admin_user)):
    user = await check_user_for_superuser(request=request, user_id=user_id,
                                          current_user=current_user, db=db)
    blocked_user = await block_user(request=request, current_user=current_user,
                                    user=user, db=db)

    return blocked_user


@router.put("/unblock/{user_id}")
async def unblock_user_route(request: Request,
                             user_id: int,
                             db: AsyncSession = Depends(get_db),
                             current_user: User = Depends(get_admin_user)):
    user = await check_user_for_superuser(request=request, user_id=user_id,
                                          current_user=current_user, db=db)
    unblocked_user = await unblock_user(request=request, current_user=current_user,
                                        user=user, db=db)

    return unblocked_user
