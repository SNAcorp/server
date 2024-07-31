from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import User
from app.crud import update_user_role, block_user, unblock_user, get_user, update_user, user_to_dict
from app.dependencies import get_db, get_current_user, get_admin_user

router = APIRouter()


@router.put("/role/{user_id}")
async def change_user_role(request: Request, user_id: int, db: AsyncSession = Depends(get_db),
                           current_user: User = Depends(get_admin_user)):
    if current_user is None:
        raise HTTPException(401, "Unauthorized")
    user = await get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    data = await request.json()
    if data["role"] == "superuser" and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Permission denied")
    updated_user = await update_user_role(db, user, data["role"])
    return updated_user


@router.get("/user/{user_id}", response_class=JSONResponse)
async def get_user_details(user_id: int, current_user: User = Depends(get_admin_user),
                           db: AsyncSession = Depends(get_db)):
    if current_user is None:
        raise HTTPException(401, "Unauthorized")
    user = await get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user_data = user_to_dict(user)
    return JSONResponse(content=user_data)


@router.put("/user/{user_id}", response_class=JSONResponse)
async def update_user_details(user_id: int, user_data: dict, current_user: User = Depends(get_admin_user),
                              db: AsyncSession = Depends(get_db)):
    if current_user is None:
        raise HTTPException(401, "Unauthorized")
    user = await get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    updated_user = await update_user(db, user, user_data)
    user_data = user_to_dict(updated_user)
    return JSONResponse(content=user_data)


@router.put("/user/{user_id}", response_class=HTMLResponse)
async def update_user_details(user_id: int, user_data: dict, current_user: User = Depends(get_admin_user),
                              db: AsyncSession = Depends(get_db)):
    if current_user is None:
        raise HTTPException(401, "Unauthorized")

    user = await get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    updated_user = await update_user(db, user, user_data)
    return updated_user


@router.put("/block/{user_id}")
async def block_user_route(user_id: int, db: AsyncSession = Depends(get_db),
                           current_user: User = Depends(get_admin_user)):
    if current_user is None:
        raise HTTPException(401, "Unauthorized")
    user = await get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_superuser and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Permission denied")
    blocked_user = await block_user(db, user)
    return blocked_user


@router.put("/unblock/{user_id}")
async def unblock_user_route(user_id: int, db: AsyncSession = Depends(get_db),
                             current_user: User = Depends(get_admin_user)):
    if current_user is None:
        raise HTTPException(401, "Unauthorized")

    user = await get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_superuser and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Permission denied")
    unblocked_user = await unblock_user(db, user)
    return unblocked_user
