import datetime
import os

from fastapi import (APIRouter, Depends, HTTPException, Request)
from fastapi.responses import (RedirectResponse, HTMLResponse, JSONResponse)

from sqlalchemy.ext.asyncio import (AsyncSession)
from sqlalchemy.future import (select)
from sqlalchemy.orm import (selectinload)

from app.dependencies import get_current_user
from app.models import (Terminal, TerminalBottle, RFID, Order,
                        OrderItem, Bottle, BottleUsageLog, OrderRFID)
from app.database import (get_db)
from app.jwt_auth import (create_terminal_token, verify_terminal)
from app.schemas import (TerminalBottleCreate, UseTerminalRequest, RegisterTerminalRequest, User)
from app.templates import (app_templates)

router = APIRouter()
SMALL_PORTION = 30
BIG_PORTION = 120
SMALL_PORTION_TIME = 3
BIG_PORTION_TIME = 9


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request,
                    db: AsyncSession = Depends(get_db),
                    current_user: User = Depends(get_current_user)) -> HTMLResponse:
    """
    Renders the dashboard HTML page, which displays a list of all terminals in the database.

    Args:
        request (Request): The HTTP request object.
        db (AsyncSession, optional): The database session. Defaults to the session from `get_db`.
        current_user (User, optional): The current user. Defaults to the user from `get_current_user`.

    Returns:
        TemplateResponse: The rendered HTML page for the terminals' dashboard.

    """
    result = await db.execute(select(Terminal).options(selectinload(Terminal.status)))
    terminals = result.scalars().all()
    return app_templates.TemplateResponse("terminals.html",
                                          {"request": request,
                                           "terminals": terminals,
                                           "current_user": current_user})


@router.post("/register-terminal", response_class=JSONResponse)
async def register_terminal(request: RegisterTerminalRequest,
                            db: AsyncSession = Depends(get_db)) -> JSONResponse:
    """
    Registers a new terminal with the given serial number in the database. If a terminal with the same serial number
    already exists, it generates a new token for that terminal and returns it. Otherwise, it creates a new terminal
    object with the given serial number and an empty list of bottles, and returns the id and token of the new terminal.

    Args:
        request (RegisterTerminalRequest): The request object containing the serial number of the terminal to be
                                          registered.
        db (AsyncSession, optional): The database session. Defaults to the session from `get_db`.

    Returns:
        dict: A dictionary containing the id and token of the registered terminal.
    """
    res = await db.execute(select(Terminal).where(Terminal.serial == request.serial))
    old_terminal = res.scalars().first()
    if old_terminal is not None:
        token = create_terminal_token(old_terminal.id, old_terminal.registration_date, request.serial)
        return JSONResponse(content={"terminal_id": old_terminal.id, "token": token}, status_code=200)

    new_terminal = Terminal(status_id=1, registration_date=datetime.datetime.utcnow(), serial=request.serial)
    db.add(new_terminal)
    await db.commit()
    await db.refresh(new_terminal)

    ter_id = new_terminal.id
    reg_date = new_terminal.registration_date
    empty_bottles = [
        TerminalBottle(
            terminal_id=new_terminal.id,
            slot_number=i,
            remaining_volume=0.0,
            bottle_id=int(os.getenv("EMPTY_BOTTLE_ID"))
        )
        for i in range(0, 8)
    ]

    db.add_all(empty_bottles)
    await db.commit()

    token = create_terminal_token(ter_id, reg_date, request.serial)

    return JSONResponse(content={"terminal_id": ter_id, "token": token}, status_code=200)


@router.post("/use", response_class=JSONResponse)
async def use_terminal(request: UseTerminalRequest,
                       db: AsyncSession = Depends(get_db)) -> JSONResponse:
    """
       Use a bottle in the terminal.

       Args:
           request (UseTerminalRequest): The request object containing the necessary data to use a bottle.
               - terminal_id (int): The ID of the terminal.
               - rfid_code (str): The RFID code of the bottle.
               - slot_number (int): The slot number of the bottle in the terminal.
               - volume (int): The volume of the bottle to use.
               - token (str): The token of the terminal.
           db (AsyncSession, optional): The database session. Defaults to the session from `get_db`.

       Returns:
           dict: A dictionary indicating that the operation was successful.
               - is_valid (bool): Always `True`.

       Raises:
           HTTPException: If any of the following conditions are met:
               - The terminal ID in the token does not match the provided terminal ID.
               - The RFID code is not found.
               - The bottle is not found in the terminal.
    """
    payload = verify_terminal(request.token)

    if payload["terminal_id"] != request.terminal_id:
        raise HTTPException(status_code=403, detail="Invalid terminal ID")

    rfid_result = await db.execute(select(RFID).where(RFID.code == request.rfid_code))
    stmt = select(Order.id).join(OrderRFID).join(RFID).where(RFID.code == request.rfid_code)
    result = await db.execute(stmt)
    order = result.scalars().first()
    rfid = rfid_result.scalars().first()
    if rfid is None:
        raise HTTPException(status_code=404, detail="RFID not found")

    # # Проверка, если RFID не валиден и есть ограничение
    # if not rfid.is_valid and rfid.limit and rfid.last_used:
    #     elapsed_time = datetime.utcnow() - rfid.last_used
    #     if elapsed_time < timedelta(minutes=10):
    #         if rfid.usage_count < 2:
    #             rfid.usage_count += 1
    #         else:
    #             raise HTTPException(status_code=403, detail="RFID usage limit reached. Try again later.")
    #     else:
    #         # Сброс счетчика, если прошло более 10 минут
    #         rfid.usage_count = 0
    #         rfid.last_used = datetime.utcnow()
    # else:
    #     rfid.usage_count = 0
    #     rfid.last_used = datetime.utcnow()
    #
    # rfid.limit = True
    # rfid.is_valid = False

    result = await db.execute(select(TerminalBottle).where(TerminalBottle.terminal_id == request.terminal_id,
                                                           TerminalBottle.slot_number == request.slot_number))
    terminal_bottle = result.scalars().first()
    if terminal_bottle is None:
        raise HTTPException(status_code=404, detail="Bottle not found in the terminal")
    terminal_bottle.remaining_volume -= request.volume

    order_item = OrderItem(order_id=order, bottle_id=terminal_bottle.bottle_id, volume=request.volume)
    db.add(order_item)
    await db.commit()

    return JSONResponse(content={"is_valid": True}, status_code=200)


@router.post("/add-bottle-to-terminal", response_class=JSONResponse)
async def add_bottle_to_terminal(terminal_bottle: TerminalBottleCreate,
                                 db: AsyncSession = Depends(get_db)) -> JSONResponse:
    """
    Add a bottle to a terminal.

    Args:
        terminal_bottle (TerminalBottleCreate): The request object containing the necessary data to add a bottle to a terminal.
            - terminal_id (int): The ID of the terminal.
            - slot_number (int): The slot number of the bottle in the terminal.
            - remaining_volume (float): The remaining volume of the bottle in the terminal.
            - bottle_id (int): The ID of the bottle.
        db (AsyncSession, optional): The database session. Defaults to the session from `get_db`.

    Returns:
        dict: A dictionary indicating that the operation was successful.
            - message (str): A message indicating that the bottle was added to the terminal.

    Raises:
        HTTPException: If any of the following conditions are met:
            - The terminal ID is not found.
            - The slot number is not found.
    """
    result = await db.execute(select(Terminal).filter(Terminal.id == terminal_bottle.terminal_id))
    terminal = result.scalars().first()

    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")

    if terminal_bottle.slot_number > 7 or terminal_bottle.slot_number < 0:
        raise HTTPException(status_code=404, detail="Slot not found")

    new_terminal_bottle = TerminalBottle(
        terminal_id=terminal_bottle.terminal_id,
        slot_number=terminal_bottle.slot_number,
        remaining_volume=terminal_bottle.remaining_volume,
        bottle_id=terminal_bottle.bottle_id
    )

    db.add(new_terminal_bottle)
    await db.commit()

    return JSONResponse(content={"message": "Bottle added to terminal successfully"}, status_code=200)


@router.get("/terminal-bottles/{terminal_id}", response_class=JSONResponse)
async def get_terminal_bottles(terminal_id: int,
                               db: AsyncSession = Depends(get_db)) -> JSONResponse:
    """
    Get the bottles in a terminal.

    Args:
        terminal_id (int): The ID of the terminal.
        db (AsyncSession, optional): The database session. Defaults to the session from `get_db`.

    Returns:
        dict: A dictionary containing the terminal ID and the list of bottles in the terminal.

    Raises:
        HTTPException: If the terminal ID is not found.
    """
    result = await db.execute(
        select(Terminal).options(selectinload(Terminal.bottles)).filter(Terminal.id == terminal_id))
    terminal = result.scalars().first()

    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")

    bottle_info = []
    for terminal_bottle in terminal.bottles:
        bottle_result = await db.execute(select(Bottle).filter(Bottle.id == terminal_bottle.bottle_id))
        bottle = bottle_result.scalars().first()
        if bottle:
            bottle_info.append({
                "id": bottle.id,
                "name": bottle.name,
                "description": bottle.description,
                "winery": bottle.winery,
                "rating_average": bottle.rating_average,
                "location": bottle.location,
                "image_path300": bottle.image_path300,
                "image_path600": bottle.image_path600,
                "wine_type": bottle.wine_type,
                "volume": bottle.volume,
                "remaining_volume": terminal_bottle.remaining_volume,
                "slot_number": terminal_bottle.slot_number
            })

    return JSONResponse(content={"terminal_id": terminal_id,
                                 "bottles": bottle_info,
                                 "volumes": {"big": BIG_PORTION_TIME, "small": SMALL_PORTION_TIME},
                                 "portions": {"big": BIG_PORTION, "small": SMALL_PORTION}}, status_code=200)


@router.post("/{terminal_id}/update-bottle", response_class=RedirectResponse)
async def update_terminal_bottle(terminal_id: int,
                                 request: Request,
                                 db: AsyncSession = Depends(get_db)) -> RedirectResponse:
    """
    Update the bottles in a terminal.

    Args:
        terminal_id (int): The ID of the terminal.
        request (Request): The request object containing the form data.
        db (AsyncSession, optional): The database session. Defaults to the session from `get_db`.

    Returns:
        dict: A dictionary containing the terminal ID and the list of bottles in the terminal.

    Raises:
        HTTPException: If the terminal ID is not found.
    """
    form = await request.form()
    bottles_data = {}

    for key, value in form.items():
        if key.startswith('bottles['):
            _, slot, field = key.split('[')
            slot = int(slot.rstrip(']'))
            field = field.rstrip(']')
            if slot not in bottles_data:
                bottles_data[slot] = {}
            bottles_data[slot][field] = value

    query = select(Terminal).filter(Terminal.id == terminal_id).options(selectinload(Terminal.bottles))
    result = await db.execute(query)
    terminal = result.scalars().first()

    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")

    for slot_number, data in bottles_data.items():
        bottle_id = int(data['bottle_id'])

        query = select(TerminalBottle).filter(
            TerminalBottle.terminal_id == terminal_id,
            TerminalBottle.slot_number == slot_number
        ).options(selectinload(TerminalBottle.bottle))
        result = await db.execute(query)
        terminal_bottle = result.scalars().first()

        if terminal_bottle:
            bottle = terminal_bottle.bottle
            initial_volume = bottle.volume
            used_volume = initial_volume - terminal_bottle.remaining_volume

            if terminal_bottle.bottle_id != bottle_id:
                if used_volume > 0:
                    usage_log = BottleUsageLog(
                        terminal_id=terminal.id,
                        bottle_id=bottle.id,
                        usage_date=datetime.datetime.utcnow(),
                        used_volume=used_volume
                    )
                    db.add(usage_log)

                terminal_bottle.bottle_id = bottle_id
                terminal_bottle.remaining_volume = (
                    await db.execute(select(Bottle.volume).where(Bottle.id == bottle_id))
                ).scalar()
            else:
                # Если бутылка заменяется на ту же самую
                if used_volume > 0:
                    usage_log = BottleUsageLog(
                        terminal_id=terminal.id,
                        bottle_id=bottle.id,
                        usage_date=datetime.datetime.utcnow(),
                        used_volume=used_volume
                    )
                    db.add(usage_log)

                # Сбрасываем объем
                terminal_bottle.remaining_volume = initial_volume
        else:
            terminal_bottle = TerminalBottle(
                terminal_id=terminal_id,
                bottle_id=bottle_id,
                slot_number=slot_number,
                remaining_volume=(
                    await db.execute(select(Bottle.volume).where(Bottle.id == bottle_id))
                ).scalar(),
            )
            db.add(terminal_bottle)

    await db.commit()

    return RedirectResponse(f"/terminals/{terminal_id}", 303)


# async def reset_bottles_endpoint(request: ResetTerminalRequest,
#                                  db: AsyncSession = Depends(get_db)) -> JSONResponse:
#     """
#     Reset bottles in terminal to initial volume and log usage.
#
#     Parameters:
#         request (ResetTerminalRequest): The request object containing the terminal ID and token.
#         db (AsyncSession): The database session.
#
#     Returns:
#         JSONResponse: A JSON response indicating success.
#
#     Raises:
#         HTTPException: If the terminal ID in the request does not match the terminal ID in the token.
#     """
#     payload = verify_terminal(request.token)
#     if payload["terminal_id"] != request.terminal_id:
#         raise HTTPException(status_code=403, detail="Invalid terminal ID")
#
#     await reset_bottles_to_initial_volume(payload["terminal_id"], db)
#     return JSONResponse(status_code=200,
#                         content={
#                             "message": "Bottles in terminal reset to initial volume and usage logged successfully"})
#
#
# async def reset_bottles_to_initial_volume(terminal_id: int,
#                                           db: AsyncSession = Depends(get_db)) -> None:
#     """
#     Reset bottles in terminal to initial volume and log usage.
#
#     Args:
#         terminal_id (int): The ID of the terminal.
#         db (AsyncSession): The database session.
#
#     Raises:
#         HTTPException: If the terminal is not found.
#     """
#     # Get the terminal with the specified ID and load the bottles
#     result = await db.execute(
#         select(Terminal).where(Terminal.id == terminal_id).options(
#             joinedload(Terminal.bottles).joinedload(TerminalBottle.bottle)))
#     terminal = result.scalars().first()
#
#     if terminal is None:
#         raise HTTPException(status_code=404, detail="Terminal not found")
#
#     # Iterate over the bottles in the terminal
#     for terminal_bottle in terminal.bottles:
#         bottle = terminal_bottle.bottle
#         initial_volume = bottle.volume
#         used_volume = initial_volume - terminal_bottle.remaining_volume
#
#         # If used volume is greater than 0, log the usage and update the bottle volume
#         if used_volume > 0:
#             # Log the usage in BottleUsageLog table
#             usage_log = BottleUsageLog(
#                 terminal_id=terminal.id,
#                 bottle_id=bottle.id,
#                 usage_date=datetime.datetime.utcnow(),
#                 used_volume=used_volume
#             )
#             db.add(usage_log)
#
#             # Update the bottle volume to the initial value
#             terminal_bottle.remaining_volume = initial_volume
#
#     await db.commit()


@router.get("/{terminal_id}", response_class=HTMLResponse)
async def manage_terminal(request: Request,
                          terminal_id: int,
                          db: AsyncSession = Depends(get_db),
                          current_user: User = Depends(get_current_user)) -> HTMLResponse:
    """
    Endpoint for managing a terminal.

    This endpoint renders the "manage_terminal.html" template with the terminal and its bottles.
    It also performs some preprocessing on the bottles to ensure they are sorted by slot number.

    Args:
        request (Request): The request object.
        terminal_id (int): The ID of the terminal to manage.
        db (AsyncSession): The database session.
        current_user (User): The current user.

    Returns:
        TemplateResponse: The rendered "manage_terminal.html" template.

    Raises:
        HTTPException: If the terminal is not found.
    """
    result = await db.execute(
        select(Terminal).options(selectinload(Terminal.bottles)).filter(Terminal.id == terminal_id))
    terminal = result.scalars().first()
    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")

    bottles_result = await db.execute(select(Bottle))
    bottles = bottles_result.scalars().all()
    sorted_bottles = sorted(terminal.bottles, key=lambda x: x.slot_number)

    return app_templates.TemplateResponse("manage_terminal.html",
                                          {"request": request,
                                           "terminal": terminal,
                                           "bottles": bottles,
                                           "sorted": sorted_bottles,
                                           "current_user": current_user})
