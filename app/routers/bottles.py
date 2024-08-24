import uuid
import os

from fastapi import (APIRouter,
                     Depends,
                     HTTPException,
                     UploadFile,
                     File,
                     Form,
                     Request)
from fastapi.responses import (FileResponse,
                               HTMLResponse,
                               RedirectResponse,
                               JSONResponse)

from sqlalchemy.ext.asyncio import (AsyncSession)
from sqlalchemy.future import (select)

from app.dependencies import (get_current_user,
                              get_admin_user)
from app.models import (Bottle,
                        User,
                        BottleUsageLog)
from app.database import (get_db)
from app.schemas import (BottleUpdateModel)
from app.templates import (app_templates)
from app.logging_config import (log)

router = APIRouter()
UPLOAD_DIR = "/images"


@router.post("/upload-image", response_class=JSONResponse)
async def upload_image(request: Request,
                       file: UploadFile = File(...),
                       current_user: User = Depends(get_admin_user)) -> JSONResponse:
    """
    Uploads an image file to the server.

    Args:
        request (Request): The HTTP request object.
        file (UploadFile): The uploaded file.
        current_user (User): The current user.

    Returns:
        dict: A dictionary containing the file path of the uploaded image.
    """
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

    return JSONResponse(content={"file_path": f"/images/{file_id}.png"}, status_code=200)


@router.get("/create", response_class=HTMLResponse)
async def manage_bottles(request: Request,
                         current_user: User = Depends(get_admin_user)) -> HTMLResponse:
    """
    This endpoint serves the bottle creation template, which is a form with fields
    for the user to enter the details of a new bottle.

    Parameters:
        request (Request): The HTTP request object.
        current_user (User): The current user.

    Returns:
        HTMLResponse: The bottle creation template.
    """
    log.bind(type="admins",
             method=request.method,
             current_user_id=current_user.id,
             url=str(request.url),
             headers=dict(request.headers),
             params=dict(request.query_params)
             ).info(f"Gained access to bottle creation template")
    return app_templates.TemplateResponse("manage_bottles.html", {"request": request, "current_user": current_user})


@router.post("/create", response_class=RedirectResponse)
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
                                 current_user: User = Depends(get_admin_user)) -> RedirectResponse:
    """
    This endpoint creates a new bottle in the database.

    Parameters:
        request (Request): The HTTP request object.
        name (str): The name of the bottle.
        winery (str): The winery of the bottle.
        rating_average (int): The rating average of the bottle.
        location (str): The location of the bottle.
        image_path300_hidden (str): The hidden image path of the bottle (300px).
        image_path600_hidden (str): The hidden image path of the bottle (600px).
        description (str): The description of the bottle.
        wine_type (str): The wine type of the bottle.
        volume (int): The volume of the bottle.
        db (AsyncSession): The database session.
        current_user (User): The current user.

    Returns:
        RedirectResponse: A redirect response to the bottles page.
    """
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
                                current_user: User = Depends(get_admin_user)) -> HTMLResponse:
    """
    Read the bottle usage log and return a rendered HTML template showing the log.

    Args:
        request (Request): The incoming request.
        db (AsyncSession): The database session.
        current_user (User): The current user.

    Returns:
        TemplateResponse: The bottle usage log template with the log data.

    This function reads the bottle usage log from the database and returns a rendered HTML template
    showing the log. The log data is obtained using a SQLAlchemy query and transformed into a list
    of dictionaries. The template response includes the request, log data, and the current user.

    This function is protected by the `get_admin_user` dependency, which means only users with the
    'admin' role can access this function.

    This function logs the access to the bottle usage log template using the `log` object. The log
    includes the type of user, the HTTP method, the current user ID, the URL, and the headers and
    query parameters of the request.

    This function is called by the route `/bottles/usages` when the HTTP method is GET. The response
    class is set to `HTMLResponse`.
    """
    query = select(BottleUsageLog)
    result = (await db.execute(query)).scalars().all()

    logs = [
        {
            "id": bottle_log.id,
            "terminal_id": bottle_log.terminal_id,
            "bottle_id": bottle_log.bottle_id,
            "usage_date": bottle_log.usage_date,
            "used_volume": bottle_log.used_volume
        }
        for bottle_log in result
    ]

    log.bind(type="admins",
             method=request.method,
             current_user_id=current_user.id,
             url=str(request.url),
             headers=dict(request.headers),
             params=dict(request.query_params)
             ).info(f"Gained access to bottle usage log template")

    return app_templates.TemplateResponse("bottle_usage_log.html",
                                          {"request": request,
                                           "logs": logs,
                                           "current_user": current_user})


@router.get("/{bottle_id}", response_class=HTMLResponse)
async def read_bottle(bottle_id: int,
                      request: Request,
                      db: AsyncSession = Depends(get_db),
                      current_user: User = Depends(get_current_user)) -> HTMLResponse:
    """
    This endpoint serves the bottle detail template, which includes the bottle ID,
    name, winery, rating average, location, image path (300px and 600px), description,
    wine type, and volume.

    Parameters:
        bottle_id (int): The ID of the bottle.
        request (Request): The HTTP request object.
        db (AsyncSession): The database session.
        current_user (User): The current user.

    Returns:
        HTMLResponse: The bottle detail template.

    Raises:
        HTTPException: If the bottle is not found.

    Logs:
        - Logs an error message if the bottle is not found.
        - Logs an info message if the bottle is found.
    """
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
                           db: AsyncSession = Depends(get_db)) -> FileResponse:
    """
    Endpoint for getting bottle image with specified resolution.

    Args:
        request (Request): The HTTP request object.
        bottle_id (int): The ID of the bottle.
        resolution (str): The resolution of the image.
        db (AsyncSession): The database session.

    Returns:
        FileResponse: The bottle image with specified resolution.

    Raises:
        HTTPException: If bottle not found or invalid resolution.
    """
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
                return FileResponse(bottle.image_path300, media_type="image/png", filename=f"{bottle_id}.png")
            elif resolution == "600":
                log.bind(type="users",
                         method=request.method,
                         current_user_id=-1,
                         url=str(request.url),
                         headers=dict(request.headers),
                         params=dict(request.query_params)
                         ).info(f"Downloaded image for bottle: {bottle_id} with resolution: {resolution}")
                return FileResponse(bottle.image_path600, media_type="image/png", filename=f"{bottle_id}.png")
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


@router.post("/update-bottle/{bottle_id}", response_class=JSONResponse)
async def update_bottle(request: Request,
                        bottle_id: int,
                        bottle_data: BottleUpdateModel,
                        current_user: User = Depends(get_admin_user),
                        db: AsyncSession = Depends(get_db)) -> JSONResponse:
    """
    Endpoint for updating information about a bottle.

    Args:
        request (Request): The HTTP request object.
        bottle_id (int): The ID of the bottle to update.
        bottle_data (BottleUpdateModel): The updated bottle data.
        current_user (User): The current admin user.
        db (AsyncSession): The database session.

    Returns:
        dict: A dictionary containing a success message.

    Raises:
        HTTPException: If the bottle ID is invalid or the bottle is not found.
    """
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
    return JSONResponse(status_code=200, content={"message": "Bottle updated successfully"})


@router.get("/", response_class=HTMLResponse)
async def list_bottles(request: Request,
                       current_user: User = Depends(get_current_user),
                       session: AsyncSession = Depends(get_db)) -> HTMLResponse:
    """
    Get a list of all bottles excluding the default bottle (id=-1).

    Args:
        request (Request): The HTTP request object.
        current_user (User): The current user.
        session (AsyncSession): The database session.

    Returns:
        TemplateResponse: A template response containing all the bottles in a list,
        sorted by ID, along with the current user and the request object.
    """
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
