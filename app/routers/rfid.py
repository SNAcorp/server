from fastapi import (APIRouter, Depends, Request)
from fastapi.responses import (JSONResponse)

from sqlalchemy.ext.asyncio import (AsyncSession)
from sqlalchemy.future import (select)

from app.dependencies import (get_current_terminal)
from app.logging_config import (log)
from app.models import (RFID, Terminal)
from app.database import (get_db)

router = APIRouter()


# current_terminal: Terminal = Depends(get_current_terminal)
@router.get("/validate/{rfid_code}", response_class=JSONResponse)
async def validate_rfid(request: Request,
                        rfid_code: str,
                        db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RFID).where(RFID.code == rfid_code))
    rfid = result.scalars().first()
    if rfid is None:
        log.bind(type="terminals",
                 method=request.method,
                 current_terminal_id=1,
                 url=str(request.url),
                 headers=dict(request.headers),
                 params=dict(request.query_params),
                 ).info("RFID not found in database")
        return JSONResponse(content={"is_valid": False})

    # if rfid.is_valid:
    return JSONResponse(content={"is_valid": True})

    # if rfid.limit and rfid.last_used:
    #     elapsed_time = datetime.utcnow() - rfid.last_used
    #     remaining_time = timedelta(minutes=10) - elapsed_time
    #     if remaining_time.total_seconds() > 0:
    #         return JSONResponse(content={"is_valid": False, "limit": str(remaining_time)})
    #     else:
    #         # Сброс ограничений по истечению 10 минут
    #         rfid.usage_count = 0
    #         rfid.is_valid = True
    #         rfid.limit = False
    #         await db.commit()
    #         return JSONResponse(content={"is_valid": True})
    #
    # return JSONResponse(content={"is_valid": False})
