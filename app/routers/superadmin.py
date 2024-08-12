from fastapi import (APIRouter, Depends)

from sqlalchemy.ext.asyncio import (AsyncSession)

from app.database import (get_db)
from app.schemas import (User)
from app.crud import (update_user_role, update_user_status)
from app.dependencies import (get_superadmin_user, check_user, check_user_for_superuser)

router = APIRouter()


@router.put("/verify/{user_id}")
async def verify_user(user_id: int,
                      db: AsyncSession = Depends(get_db),
                      current_user: User = Depends(get_superadmin_user)):
    user = await check_user(user_id, current_user=current_user)
    updated_user = await update_user_status(user, True, db)
    return updated_user


@router.put("/reject/{user_id}")
async def reject_user(user_id: int,
                      db: AsyncSession = Depends(get_db),
                      current_user: User = Depends(get_superadmin_user)):
    user = await check_user_for_superuser(user_id, current_user=current_user)
    updated_user = await update_user_status(user, False, db)
    return updated_user


@router.put("/superadmin/{user_id}")
async def make_superadmin(user_id: int,
                          db: AsyncSession = Depends(get_db),
                          current_user: User = Depends(get_superadmin_user)):
    user = await check_user_for_superuser(user_id, current_user=current_user)
    updated_user = await update_user_role(user, "superadmin", db)
    return updated_user
