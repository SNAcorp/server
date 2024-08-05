import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.dependencies import get_current_user, get_admin_user
from app.models import Bottle, User, BottleUsageLog
from app.database import get_db
import os

from app.schemas import BottleUpdateModel

router = APIRouter()
app_templates = Jinja2Templates(directory="app/templates")
UPLOAD_DIR = "/images"


@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    file_id = str(uuid.uuid4())
    file_path = f"{UPLOAD_DIR}/{file_id}.png"

    with open(file_path, "wb+") as buffer:
        buffer.write(await file.read())

    return {"file_path": f"/images/{file_id}.png"}


@router.get("/create", response_class=HTMLResponse)
async def manage_bottles(request: Request,
                         current_user: User = Depends(get_current_user)):
    if current_user is None:
        return RedirectResponse("/login", 303)
    return app_templates.TemplateResponse("manage_bottles.html", {"request": request, "current_user": current_user})


@router.post("/create")
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
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
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
    return RedirectResponse("/bottles", 303)


@router.get("/usages", response_class=HTMLResponse)
async def read_bottle_usage_log(request: Request, current_user: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    query = select(BottleUsageLog)
    result = (await db.execute(query)).scalars().all()

    # Преобразование результатов в список словарей для более явного представления данных
    logs = [
        {
            "terminal_id": log.terminal_id,
            "bottle_id": log.bottle_id,
            "usage_date": log.usage_date,
            "used_volume": log.used_volume
        }
        for log in result
    ]

    return app_templates.TemplateResponse("bottle_usage_log.html", {"request": request, "logs": logs, "current_user": current_user})


@router.get("/{bottle_id}", response_class=HTMLResponse)
async def read_bottle(bottle_id: int, request: Request, current_user: User = Depends(get_current_user),
                      session: AsyncSession = Depends(get_db)):
    if current_user is None:
        return RedirectResponse("/login", 303)
    if bottle_id < 0:
        if current_user.is_superuser:
            result = await session.execute(
                select(Bottle).filter(Bottle.id == bottle_id)
            )
            bottle = result.scalars().first()
            return app_templates.TemplateResponse("bottle_detail.html",
                                                  {"request": request, "bottle": bottle, "current_user": current_user})
        else:
            raise HTTPException(status_code=404, detail="Bottle not found")
    result = await session.execute(
        select(Bottle).filter(Bottle.id == bottle_id)
    )
    bottle = result.scalars().first()
    if not bottle:
        raise HTTPException(status_code=404, detail="Bottle not found")
    return app_templates.TemplateResponse("bottle_detail.html",
                                          {"request": request, "bottle": bottle, "current_user": current_user})


@router.get("/image/{bottle_id}/{resolution}", response_class=FileResponse)
async def get_bottle_image(bottle_id: int, resolution: str, current_user: User = Depends(get_current_user),
                           db: AsyncSession = Depends(get_db)):
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
async def update_bottle(
        bottle_id: int,
        bottle_data: BottleUpdateModel,
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

        bottle.name = bottle_data.name
        bottle.winery = bottle_data.winery
        bottle.rating_average = bottle_data.rating_average
        bottle.location = bottle_data.location
        bottle.image_path300 = bottle_data.image_path300
        bottle.image_path600 = bottle_data.image_path600
        bottle.description = bottle_data.description
        bottle.wine_type = bottle_data.wine_type
        bottle.volume = bottle_data.volume

        session.add(bottle)
        await session.commit()
    return {"message": "Bottle updated successfully"}
