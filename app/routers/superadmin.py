from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas import User
from app.crud import update_user_role, update_user_status, get_user
from app.dependencies import get_db, get_current_user, get_superadmin_user

router = APIRouter()

# @router.put("/verify/{user_id}")
# def verify_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_superadmin_user)):
#     user = get_user(db, user_id)
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
#     updated_user = update_user_status(db, user, True)
#     return updated_user
#
# @router.put("/reject/{user_id}")
# def reject_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_superadmin_user)):
#     user = get_user(db, user_id)
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
#     updated_user = update_user_status(db, user, False)
#     return updated_user
#
# @router.put("/superadmin/{user_id}")
# def make_superadmin(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_superadmin_user)):
#     user = get_user(db, user_id)
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
#     updated_user = update_user_role(db, user, "superadmin")
#     return updated_user
