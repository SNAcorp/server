from fastapi import (APIRouter, Depends, HTTPException, Request)
from fastapi.responses import (HTMLResponse, JSONResponse)

from sqlalchemy.ext.asyncio import (AsyncSession)

from app.database import (get_db)
from app.schemas import (User)
from app.crud import (update_user_role, block_user, unblock_user, update_user, user_to_dict)
from app.dependencies import (get_admin_user, check_user, check_user_for_superuser)

router = APIRouter()


@router.put("/role/{user_id}")
async def change_user_role(request: Request,
                           user_id: int,
                           db: AsyncSession = Depends(get_db),
                           current_user: User = Depends(get_admin_user)):
    user = await check_user(user_id)
    data = await request.json()
    if data["role"] == "superuser" and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Permission denied")
    updated_user = await update_user_role(user, data["role"], db)
    return updated_user


@router.get("/user/{user_id}", response_class=JSONResponse)
async def get_user_details(user_id: int,
                           current_user: User = Depends(get_admin_user)):
    user = await check_user(user_id)
    user_data = user_to_dict(user)
    return JSONResponse(content=user_data)


@router.put("/user/{user_id}", response_class=JSONResponse)
async def update_user_details(user_id: int,
                              user_data: dict,
                              db: AsyncSession = Depends(get_db),
                              current_user: User = Depends(get_admin_user)):
    user = await check_user(user_id)
    updated_user = await update_user(user, user_data, db)
    user_data = user_to_dict(updated_user)
    return JSONResponse(content=user_data)


@router.put("/user/{user_id}", response_class=HTMLResponse)
async def update_user_details(user_id: int,
                              user_data: dict,
                              db: AsyncSession = Depends(get_db),
                              current_user: User = Depends(get_admin_user)):
    user = await check_user(user_id)
    updated_user = await update_user(user, user_data, db)
    return updated_user


@router.put("/block/{user_id}")
async def block_user_route(user_id: int,
                           db: AsyncSession = Depends(get_db),
                           current_user: User = Depends(get_admin_user)):
    user = await check_user_for_superuser(user_id, current_user=current_user)
    blocked_user = await block_user(user, db)
    return blocked_user


@router.put("/unblock/{user_id}")
async def unblock_user_route(user_id: int,
                             db: AsyncSession = Depends(get_db),
                             current_user: User = Depends(get_admin_user)):
    user = await check_user_for_superuser(user_id, current_user=current_user)
    unblocked_user = await unblock_user(user, db)
    return unblocked_user
