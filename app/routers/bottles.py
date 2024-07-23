from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import Bottle
from app.database import get_db
from app.schemas import BottleCreate

router = APIRouter()


@router.post("/create-bottle")
async def create_bottle_endpoint(bottle: BottleCreate, db: AsyncSession = Depends(get_db)):
    new_bottle = Bottle(
        name=bottle.name,
        winery=bottle.winery,
        rating_average=bottle.rating_average,
        location=bottle.location,
        image_path300=bottle.image_path300,
        image_path600=bottle.image_path600,
        url300=bottle.url300,
        url600=bottle.url600,
        description=bottle.description,
        wine_type=bottle.wine_type,
        volume=bottle.volume
    )
    db.add(new_bottle)
    await db.commit()
    await db.refresh(new_bottle)
    return new_bottle

@router.get("/image/{bottle_id}/{resolution}", response_class=FileResponse)
async def get_bottle_image(bottle_id: int, resolution: str, db: AsyncSession = Depends(get_db)):
    async with db as session:
        result = await session.execute(select(Bottle).filter(Bottle.id == bottle_id))
        bottle = result.scalars().first()
        if bottle:
            if resolution == "300":
                return FileResponse(bottle.image_path300)
            elif resolution == "600":
                return FileResponse(bottle.image_path600)
            else:
                raise HTTPException(status_code=400, detail="Invalid resolution")
        else:
            raise HTTPException(status_code=404, detail="Bottle not found")