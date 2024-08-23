import uuid
import os

from fastapi import (APIRouter, Depends, HTTPException, UploadFile, File, Form, Request)
from fastapi.responses import (FileResponse, HTMLResponse, RedirectResponse)

from sqlalchemy.ext.asyncio import (AsyncSession)
from sqlalchemy.future import (select)

from app.dependencies import (get_current_user, get_admin_user)
from app.models import (Bottle, User, BottleUsageLog)
from app.database import (get_db)
from app.schemas import (BottleUpdateModel)
from app.templates import app_templates
from app.logging_config import log
router = APIRouter()
UPLOAD_DIR = "/images"


@router.post("/upload-image")
async def upload_image(request: Request, file: UploadFile = File(...),
                       current_user: User = Depends(get_admin_user)):
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    file_id = str(uuid.uuid4())
    file_path = f"{UPLOAD_DIR}/{file_id}.png"

    with open(file_path, "wb+") as buffer:
        buffer.write(await file.read())

    log.bind(type="admins",
             method=request.method,
             current_user_id=current_user.id,
             url=str(request.url),
             headers=dict(request.headers),
             params=dict(request.query_params)
             ).info(f"Upload image: {file_path}")

    return {"file_path": f"/images/{file_id}.png"}


@router.get("/create", response_class=HTMLResponse)
async def manage_bottles(request: Request,
                         current_user: User = Depends(get_admin_user)):
    log.bind(type="admins",
             method=request.method,
             current_user_id=current_user.id,
             url=str(request.url),
             headers=dict(request.headers),
             params=dict(request.query_params)
             ).info(f"Gained access to bottle creation template")
    return app_templates.TemplateResponse("manage_bottles.html", {"request": request, "current_user": current_user})


@router.post("/create")
async def create_bottle_endpoint(request: Request,
                                 name: str = Form(...),
                                 winery: str = Form(...),
                                 rating_average: int = Form(...),
                                 location: str = Form(...),
                                 image_path300_hidden: str = Form(...),
                                 image_path600_hidden: str = Form(...),
                                 description: str = Form(...),
                                 wine_type: str = Form(...),
                                 volume: int = Form(...),
                                 db: AsyncSession = Depends(get_db),
                                 current_user: User = Depends(get_admin_user)):
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
    log.bind(type="admins",
             method=request.method,
             current_user_id=current_user.id,
             url=str(request.url),
             headers=dict(request.headers),
             params=dict(request.query_params)
             ).info(f"Create bottle: {new_bottle.id}")
    return RedirectResponse("/bottles", 303)


@router.get("/usages", response_class=HTMLResponse)
async def read_bottle_usage_log(request: Request,
                                db: AsyncSession = Depends(get_db),
                                current_user: User = Depends(get_admin_user)):
    query = select(BottleUsageLog)
    result = (await db.execute(query)).scalars().all()

    # Преобразование результатов в список словарей для более явного представления данных
    logs = [
        {
            "id": log.id,
            "terminal_id": log.terminal_id,
            "bottle_id": log.bottle_id,
            "usage_date": log.usage_date,
            "used_volume": log.used_volume
        }
        for log in result
    ]

    log.bind(type="admins",
             method=request.method,
             current_user_id=current_user.id,
             url=str(request.url),
             headers=dict(request.headers),
             params=dict(request.query_params)
             ).info(f"Gained access to bottle usage log template")

    return app_templates.TemplateResponse("bottle_usage_log.html",
                                          {"request": request, "logs": logs, "current_user": current_user})


@router.get("/{bottle_id}", response_class=HTMLResponse)
async def read_bottle(bottle_id: int,
                      request: Request,
                      db: AsyncSession = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    if bottle_id < 0:
        if current_user.is_superuser:
            result = await db.execute(
                select(Bottle).filter(Bottle.id == bottle_id)
            )
            bottle = result.scalars().first()
            log.bind(type="users",
                     method=request.method,
                     current_user_id=current_user.id,
                     url=str(request.url),
                     headers=dict(request.headers),
                     params=dict(request.query_params)
                     ).info(f"Gained access to info about bottle: {bottle_id}")
            return app_templates.TemplateResponse("bottle_detail.html",
                                                  {"request": request, "bottle": bottle, "current_user": current_user})
        else:
            log.bind(type="users",
                     method=request.method,
                     current_user_id=current_user.id,
                     url=str(request.url),
                     headers=dict(request.headers),
                     params=dict(request.query_params)
                     ).error(f"Tried to gain info about bottle: {bottle_id}")
            raise HTTPException(status_code=404, detail="Bottle not found")
    result = await db.execute(
        select(Bottle).filter(Bottle.id == bottle_id)
    )
    bottle = result.scalars().first()
    if not bottle:
        log.bind(type="users",
                 method=request.method,
                 current_user_id=current_user.id,
                 url=str(request.url),
                 headers=dict(request.headers),
                 params=dict(request.query_params)
                 ).error(f"Tried to gain info about bottle: {bottle_id}")
        raise HTTPException(status_code=404, detail="Bottle not found")
    log.bind(type="users",
             method=request.method,
             current_user_id=current_user.id,
             url=str(request.url),
             headers=dict(request.headers),
             params=dict(request.query_params)
             ).info(f"Gained access to info about bottle: {bottle_id}")
    return app_templates.TemplateResponse("bottle_detail.html",
                                          {"request": request, "bottle": bottle, "current_user": current_user})


@router.get("/image/{bottle_id}/{resolution}", response_class=FileResponse)
async def get_bottle_image(request: Request,
                           bottle_id: int,
                           resolution: str,
                           db: AsyncSession = Depends(get_db)):
    async with db as session:
        result = await session.execute(select(Bottle).filter(Bottle.id == bottle_id))
        bottle = result.scalars().first()
        if bottle:
            if resolution == "300":
                log.bind(type="users",
                         method=request.method,
                         current_user_id=-1,
                         url=str(request.url),
                         headers=dict(request.headers),
                         params=dict(request.query_params)
                         ).info(f"Downloaded image for bottle: {bottle_id} with resolution: {resolution}")
                return FileResponse(bottle.image_path300)
            elif resolution == "600":
                log.bind(type="users",
                         method=request.method,
                         current_user_id=-1,
                         url=str(request.url),
                         headers=dict(request.headers),
                         params=dict(request.query_params)
                         ).info(f"Downloaded image for bottle: {bottle_id} with resolution: {resolution}")
                return FileResponse(bottle.image_path600)
            else:
                log.bind(type="users",
                         method=request.method,
                         current_user_id=-1,
                         url=str(request.url),
                         headers=dict(request.headers),
                         params=dict(request.query_params)
                         ).error(f"Tried to gain image for bottle: {bottle_id} with resolution: {resolution}")
                raise HTTPException(status_code=400, detail="Invalid resolution")
        else:
            log.bind(type="users",
                     method=request.method,
                     current_user_id=-1,
                     url=str(request.url),
                     headers=dict(request.headers),
                     params=dict(request.query_params)
                     ).error(f"Tried to gain image for bottle: {bottle_id}")
            raise HTTPException(status_code=404, detail="Bottle not found")


@router.post("/update-bottle/{bottle_id}")
async def update_bottle(request: Request,
                        bottle_id: int,
                        bottle_data: BottleUpdateModel,
                        current_user: User = Depends(get_admin_user),
                        db: AsyncSession = Depends(get_db)):

    if bottle_id < 0:
        log.bind(type="admins",
                 method=request.method,
                 current_user_id=current_user.id,
                 url=str(request.url),
                 headers=dict(request.headers),
                 params=dict(request.query_params)
                 ).info(f"Tried to update info about bottle: {bottle_id}")
        raise HTTPException(status_code=404, detail="Bottle not found")

    async with db.begin():
        result = await db.execute(
            select(Bottle).filter(Bottle.id == bottle_id)
        )
        bottle = result.scalars().first()
        if not bottle:
            log.bind(type="admins",
                     method=request.method,
                     current_user_id=current_user.id,
                     url=str(request.url),
                     headers=dict(request.headers),
                     params=dict(request.query_params)
                     ).info(f"Tried to update info about bottle: {bottle_id}")
            raise HTTPException(status_code=404, detail="Bottle not found")
        old_data = dict(bottle)
        bottle.name = bottle_data.name
        bottle.winery = bottle_data.winery
        bottle.rating_average = bottle_data.rating_average
        bottle.location = bottle_data.location
        bottle.image_path300 = bottle_data.image_path300
        bottle.image_path600 = bottle_data.image_path600
        bottle.description = bottle_data.description
        bottle.wine_type = bottle_data.wine_type
        bottle.volume = bottle_data.volume

        db.add(bottle)
        await db.commit()
        log.bind(type="admins",
                 method=request.method,
                 current_user_id=current_user.id,
                 url=str(request.url),
                 headers=dict(request.headers),
                 params=dict(request.query_params),
                 old_info=old_data,
                 new_info=dict(bottle),
                 ).info(f"Updated info about bottle: {bottle_id}")
    return {"message": "Bottle updated successfully"}


@router.get("/", response_class=HTMLResponse)
async def list_bottles(request: Request, current_user: User = Depends(get_current_user),
                       session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Bottle).filter(Bottle.id != -1))
    bottles = result.scalars().all()
    sorted_bottles = sorted(bottles, key=lambda x: x.id)
    log.bind(type="users",
             method=request.method,
             current_user_id=current_user.id,
             url=str(request.url),
             headers=dict(request.headers),
             params=dict(request.query_params),
             ).info(f"Gained bottles list template")
    return app_templates.TemplateResponse("bottle_list.html",
                                          {"request": request, "bottles": sorted_bottles, "current_user": current_user})
