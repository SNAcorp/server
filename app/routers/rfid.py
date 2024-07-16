from datetime import timedelta, datetime

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import RFID
from database import get_db

router = APIRouter()


@router.get("/validate/{rfid_code}")
async def validate_rfid(rfid_code: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RFID).where(RFID.code == rfid_code))
    rfid = result.scalars().first()
    if rfid is None:
        return JSONResponse(content={"is_valid": False})

    if rfid.is_valid:
        return JSONResponse(content={"is_valid": True})

    if rfid.limit and rfid.last_used:
        elapsed_time = datetime.utcnow() - rfid.last_used
        remaining_time = timedelta(minutes=10) - elapsed_time
        if remaining_time.total_seconds() > 0:
            return JSONResponse(content={"is_valid": False, "limit": str(remaining_time)})
        else:
            # Сброс ограничений по истечению 10 минут
            rfid.usage_count = 0
            rfid.is_valid = True
            rfid.limit = False
            await db.commit()
            return JSONResponse(content={"is_valid": True})

    return JSONResponse(content={"is_valid": False})
