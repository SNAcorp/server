import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import Bottle
from app.database import get_db
from app.schemas import BottleCreate
import os

router = APIRouter()


@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    if file.content_type != "image/png":
        raise HTTPException(status_code=400, detail="Invalid file type. Only PNG is allowed.")

    UPLOAD_DIR = "images"
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    file_id = str(uuid.uuid4())
    file_path = f"images/{file_id}.png"

    with open(file_path, "wb+") as buffer:
        buffer.write(await file.read())

    return {"file_path": file_path}


@router.post("/create-bottle")
async def create_bottle_endpoint(
        name: str = Form(...),
        winery: str = Form(...),
        rating_average: float = Form(...),
        location: str = Form(...),
        image_path300_hidden: str = Form(...),
        image_path600_hidden: str = Form(...),
        description: str = Form(...),
        wine_type: str = Form(...),
        volume: float = Form(...),
        db: AsyncSession = Depends(get_db)
):
    new_bottle = Bottle(
        name=name,
        winery=winery,
        rating_average=rating_average,
        location=location,
        image_path300=image_path300_hidden,
        image_path600=image_path600_hidden,
        description=description,
        wine_type=wine_type,
        volume=volume
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
