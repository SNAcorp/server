from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import User
from app.crud import update_user_role, block_user, unblock_user, get_user
from app.dependencies import get_db, get_current_user, get_admin_user

router = APIRouter()


@router.put("/role/{user_id}")
async def change_user_role(request: Request, user_id: int, db: AsyncSession = Depends(get_db),
                           current_user: User = Depends(get_admin_user)):
    user = await get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    data = await request.json()
    print(data)
    updated_user = update_user_role(db, user, data["role"])
    return updated_user


@router.put("/block/{user_id}")
async def block_user_route(user_id: int, db: AsyncSession = Depends(get_db),
                           current_user: User = Depends(get_admin_user)):
    user = await get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    blocked_user = block_user(db, user)
    return blocked_user


@router.put("/unblock/{user_id}")
async def unblock_user_route(user_id: int, db: AsyncSession = Depends(get_db),
                             current_user: User = Depends(get_admin_user)):
    user = await get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    unblocked_user = unblock_user(db, user)
    return unblocked_user


