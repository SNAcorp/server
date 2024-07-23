import logging

from fastapi import APIRouter, Depends, HTTPException, Security, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, joinedload
from datetime import datetime, timedelta
import uuid
from app.models import Terminal, TerminalBottle, RFID, Order, OrderItem, Bottle, EMPTY_BOTTLE_ID, BottleUsageLog
from app.database import get_db
from app.jwt_auth import create_terminal_token, verify_terminal, security
from app.schemas import TerminalBottleCreate, UseTerminalRequest, RegisterTerminalResponse, TerminalResponse, \
    ResetTerminalRequest

router = APIRouter()
SMALL_PORTION = 30
BIG_PORTION = 120

@router.post("/register-terminal", response_model=RegisterTerminalResponse)
async def register_terminal(serial: str, db: AsyncSession = Depends(get_db)):
    new_terminal = Terminal(status_id=1, registration_date=datetime.utcnow(), serial=serial)
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
            bottle_id=EMPTY_BOTTLE_ID
        )
        for i in range(0, 8)
    ]

    db.add_all(empty_bottles)
    await db.commit()

    token = create_terminal_token(ter_id, reg_date, serial)

    return {"terminal_id": ter_id, "token": token}


@router.post("/use")
async def use_terminal(request: UseTerminalRequest, db: AsyncSession = Depends(get_db)):
    payload = verify_terminal(request.token)

    if payload["terminal_id"] != request.terminal_id:
        raise HTTPException(status_code=403, detail="Invalid terminal ID")

    result = await db.execute(select(RFID).where(RFID.code == request.rfid_code))
    rfid = result.scalars().first()
    if rfid is None:
        raise HTTPException(status_code=404, detail="RFID not found")

    # Проверка, если RFID не валиден и есть ограничение
    if not rfid.is_valid and rfid.limit and rfid.last_used:
        elapsed_time = datetime.utcnow() - rfid.last_used
        if elapsed_time < timedelta(minutes=10):
            if rfid.usage_count < 2:
                rfid.usage_count += 1
            else:
                raise HTTPException(status_code=403, detail="RFID usage limit reached. Try again later.")
        else:
            # Сброс счетчика, если прошло более 10 минут
            rfid.usage_count = 1
            rfid.last_used = datetime.utcnow()
    else:
        rfid.usage_count = 1
        rfid.last_used = datetime.utcnow()

    rfid.limit = True
    rfid.is_valid = False

    result = await db.execute(select(TerminalBottle).where(TerminalBottle.terminal_id == request.terminal_id,
                                                           TerminalBottle.slot_number == request.slot_number))
    terminal_bottle = result.scalars().first()
    if terminal_bottle is None:
        raise HTTPException(status_code=404, detail="Bottle not found in the terminal")
    if terminal_bottle.remaining_volume < request.volume:
        raise HTTPException(status_code=400, detail="Not enough volume in the bottle")

    if request.volume == 0:
        terminal_bottle.remaining_volume -= SMALL_PORTION
    elif request.volume == 1:
        terminal_bottle.remaining_volume -= BIG_PORTION
    else:
        raise HTTPException(status_code=404, detail="Portion not found")

    order = Order()
    db.add(order)
    await db.flush()

    order_item = OrderItem(order_id=order.id, bottle_id=terminal_bottle.bottle_id, volume=request.volume)
    db.add(order_item)
    await db.commit()

    return {"message": "Wine poured successfully"}


@router.post("/add-bottle-to-terminal")
async def add_bottle_to_terminal(terminal_bottle: TerminalBottleCreate, db: AsyncSession = Depends(get_db)):
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

    return {"message": "Bottle added to terminal successfully"}


@router.get("/terminal-bottles/{terminal_id}")
async def get_terminal_bottles(terminal_id: int, db: AsyncSession = Depends(get_db)):
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
                "url300": bottle.url300,
                "url600": bottle.url600,
                "wine_type": bottle.wine_type,
                "volume": bottle.volume,
                "remaining_volume": terminal_bottle.remaining_volume,
                "slot_number": terminal_bottle.slot_number
            })

    return {"terminal_id": terminal_id, "bottles": bottle_info}


@router.post("/{terminal_id}/update-bottle", response_model=TerminalResponse)
async def update_terminal_bottle(terminal_id: int, request: Request, db: AsyncSession = Depends(get_db)):
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
        )
        result = await db.execute(query)
        terminal_bottle = result.scalars().first()

        if terminal_bottle:
            if terminal_bottle.bottle_id != bottle_id:
                terminal_bottle.bottle_id = bottle_id
                terminal_bottle.remaining_volume = (
                    await db.execute(select(Bottle.volume).where(Bottle.id == bottle_id))).scalar()
        else:
            terminal_bottle = TerminalBottle(
                terminal_id=terminal_id,
                bottle_id=bottle_id,
                slot_number=slot_number,
                remaining_volume=(await db.execute(select(Bottle.volume).where(Bottle.id == bottle_id))).scalar(),
            )
            db.add(terminal_bottle)

    await db.commit()

    terminal_data = await db.execute(
        select(Terminal).filter(Terminal.id == terminal_id).options(selectinload(Terminal.bottles)))
    terminal_data = terminal_data.scalars().first()

    return TerminalResponse.from_orm(terminal_data)


@router.post("/reset_bottles")
async def reset_bottles_endpoint(request: ResetTerminalRequest, db: AsyncSession = Depends(get_db)):
    payload = verify_terminal(request.token)
    if payload["terminal_id"] != request.terminal_id:
        raise HTTPException(status_code=403, detail="Invalid terminal ID")

    await reset_bottles_to_initial_volume(db, payload["terminal_id"])
    return {"message": "Bottles in terminal reset to initial volume and usage logged successfully"}


async def reset_bottles_to_initial_volume(db: AsyncSession, terminal_id: int):
    # Получаем терминал с указанным ID и загруженными бутылками
    result = await db.execute(select(Terminal).where(Terminal.id == terminal_id).options(
        joinedload(Terminal.bottles).joinedload(TerminalBottle.bottle)))
    terminal = result.scalars().first()

    if terminal is None:
        raise HTTPException(status_code=404, detail="Terminal not found")

    for terminal_bottle in terminal.bottles:
        bottle = terminal_bottle.bottle
        initial_volume = bottle.volume
        used_volume = initial_volume - terminal_bottle.remaining_volume
        if used_volume > 0:
            # Записываем остаток в таблицу BottleUsageLog
            usage_log = BottleUsageLog(
                terminal_id=terminal.id,
                bottle_id=bottle.id,
                usage_date=datetime.utcnow(),
                used_volume=used_volume
            )
            db.add(usage_log)

            # Обновляем объем бутылки до исходного значения
            terminal_bottle.remaining_volume = initial_volume

    await db.commit()
