from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas import User
from app.crud import update_user_role, block_user, unblock_user
from app.dependencies import get_db, get_current_user, get_admin_user

router = APIRouter()

@router.put("/role/{user_id}")
def change_user_role(user_id: int, role: str, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    updated_user = update_user_role(db, user, role)
    return updated_user

@router.put("/block/{user_id}")
def block_user_route(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    blocked_user = block_user(db, user)
    return blocked_user

@router.put("/unblock/{user_id}")
def unblock_user_route(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    unblocked_user = unblock_user(db, user)
    return unblocked_user
