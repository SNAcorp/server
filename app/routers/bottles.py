import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import Bottle
from sqlalchemy.orm import selectinload
from app.database import get_db
import os

router = APIRouter()
app_templates = Jinja2Templates(directory="app/templates")


@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    UPLOAD_DIR = "/images"
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    file_id = str(uuid.uuid4())
    file_path = f"/images/{file_id}.png"

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


@router.get("/{bottle_id}", response_class=HTMLResponse)
async def read_bottle(bottle_id: int, request: Request, session: AsyncSession = Depends(get_db)):
    if bottle_id < 0:
        raise HTTPException(status_code=404, detail="Bottle not found")
    result = await session.execute(
            select(Bottle).filter(Bottle.id == bottle_id)
        )
    bottle = result.scalars().first()
    if not bottle:
        raise HTTPException(status_code=404, detail="Bottle not found")
    return app_templates.TemplateResponse("bottle_detail.html", {"request": request, "bottle": bottle})


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


@router.post("/update-bottle/{bottle_id}")
async def update_bottle(bottle_id: int,
                        name: str = Form(...),
                        winery: str = Form(...),
                        rating_average: float = Form(...),
                        location: str = Form(...),
                        image_path300: str = Form(...),
                        image_path600: str = Form(...),
                        description: str = Form(...),
                        wine_type: str = Form(...),
                        volume: float = Form(...),
                        session: AsyncSession = Depends(get_db)
                        ):
    if bottle_id < 0:
        raise HTTPException(status_code=404, detail="Bottle not found")

    async with session.begin():
        result = await session.execute(
            select(Bottle).filter(Bottle.id == bottle_id)
        )
        bottle = result.scalars().first()
        if not bottle:
            raise HTTPException(status_code=404, detail="Bottle not found")

        bottle.name = name
        bottle.winery = winery
        bottle.rating_average = rating_average
        bottle.location = location
        bottle.image_path300 = image_path300
        bottle.image_path600 = image_path600
        bottle.description = description
        bottle.wine_type = wine_type
        bottle.volume = volume

        session.add(bottle)
        await session.commit()
    return {"message": "Bottle updated successfully"}
