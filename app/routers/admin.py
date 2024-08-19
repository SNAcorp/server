from time import process_time

from fastapi import (APIRouter, Depends, HTTPException, Request)
from fastapi.responses import (JSONResponse)
from loguru import logger
from sqlalchemy.ext.asyncio import (AsyncSession)

from app.database import (get_db)
from app.schemas import (User)
from app.crud import (update_user_role, block_user, unblock_user, update_user, user_to_dict)
from app.dependencies import (get_admin_user, check_user, check_user_for_superuser)

router = APIRouter()

logger.add("/logs/admins.log", rotation="1 day", retention="7 days", level="DEBUG")


@router.put("/role/{user_id}")
async def change_user_role(request: Request,
                           user_id: int,
                           db: AsyncSession = Depends(get_db),
                           current_user: User = Depends(get_admin_user)):
    user = await check_user(user_id, current_user=current_user, db=db)
    data = await request.json()

    logger.info(
        f"Request processed: Admin ID: {current_user.id} -  User ID: {user_id} - Status: process | {request.method} | {request.url} | ({process_time:.2f}s)")

    if data["role"] == "superuser" and not current_user.is_superuser:
        logger.error(f"Permission denied for: {current_user.id}, from {request.url}")
        logger.info(
            f"Request error: Admin ID: {current_user.id} -  User ID: {user_id} - Status: error | {request.method} | {request.url} | ({process_time:.2f}s)")

        raise HTTPException(status_code=403, detail="Permission denied")

    updated_user = await update_user_role(user, data["role"], db)
    logger.info(
        f"Request complete: Admin ID: {current_user.id} -  User ID: {user_id} - Status: complete | {request.method} | {request.url} | ({process_time:.2f}s)")

    return updated_user


@router.get("/user/{user_id}", response_class=JSONResponse)
async def get_user_details(request: Request,
                           user_id: int,
                           db: AsyncSession = Depends(get_db),
                           current_user: User = Depends(get_admin_user)):
    user = await check_user(user_id, current_user=current_user, db=db)
    user_data = user_to_dict(user)

    logger.info(
        f"Request complete: Admin ID: {current_user.id} -  User ID: {user_id} - Status: compete | {request.method} | {request.url} | ({process_time:.2f}s)")

    return JSONResponse(content=user_data)


@router.put("/user/{user_id}", response_class=JSONResponse)
async def update_user_details(request: Request,
                              user_id: int,
                              user_data: dict,
                              current_user: User = Depends(get_admin_user),
                              db: AsyncSession = Depends(get_db)):
    user = await check_user(user_id, current_user=current_user, db=db)
    updated_user = await update_user(user, user_data, db)
    user_data = user_to_dict(updated_user)

    logger.info(
        f"Request complete: Admin ID: {current_user.id} -  User ID: {user_id} - Status: compete | {request.method} | {request.url} | ({process_time:.2f}s)")

    return JSONResponse(content=user_data)


@router.put("/block/{user_id}")
async def block_user_route(request: Request,
                           user_id: int,
                           db: AsyncSession = Depends(get_db),
                           current_user: User = Depends(get_admin_user)):
    user = await check_user_for_superuser(user_id, current_user=current_user, db=db)
    blocked_user = await block_user(user, db)

    logger.info(
        f"Request complete: Admin ID: {current_user.id} -  User ID: {user_id} - Status: compete | {request.method} | {request.url} | ({process_time:.2f}s)")

    return blocked_user


@router.put("/unblock/{user_id}")
async def unblock_user_route(request: Request,
                             user_id: int,
                             db: AsyncSession = Depends(get_db),
                             current_user: User = Depends(get_admin_user)):
    user = await check_user_for_superuser(user_id, current_user=current_user, db=db)
    unblocked_user = await unblock_user(user, db)

    logger.info(
        f"Request complete: Admin ID: {current_user.id} -  User ID: {user_id} - Status: compete | {request.method} | {request.url} | ({process_time:.2f}s)")

    return unblocked_user
