from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from models import Bottle
from database import get_db
from schemas import BottleCreate

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
