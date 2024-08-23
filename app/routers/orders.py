from datetime import timedelta

from fastapi import (APIRouter, Depends, HTTPException, Request, Form)
from fastapi.responses import (JSONResponse, RedirectResponse, HTMLResponse)

from sqlalchemy.ext.asyncio import (AsyncSession)
from sqlalchemy.future import (select)
from sqlalchemy.orm import (selectinload, joinedload)

from app.dependencies import get_current_user
from app.database import (get_db)
from app.logging_config import log
from app.models import Order, RFID, OrderRFID, OrderItem
from app.schemas import User
from app.templates import app_templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def read_orders(request: Request,
                      db: AsyncSession = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Order).options(selectinload(Order.items)))
    orders = result.scalars().all()

    log.bind(type="users",
             method=request.method,
             current_user_id=current_user.id,
             url=str(request.url),
             headers=dict(request.headers),
             params=dict(request.query_params)
             ).info(f"Gained access to orders list template")

    return app_templates.TemplateResponse("orders.html",
                                          {"request": request,
                                           "orders": orders,
                                           "timedelta": timedelta,
                                           "current_user": current_user})


@router.post("/{order_id}/add", response_class=JSONResponse)
async def add_rfid_to_order(request: Request,
                            order_id: int,
                            rfid_code: str = Form(...),
                            db: AsyncSession = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalars().first()
    if order is None:
        log.bind(type="users",
                 method=request.method,
                 current_user_id=current_user.id,
                 url=str(request.url),
                 headers=dict(request.headers),
                 params=dict(request.query_params)
                 ).error(f"Аttempt to add access to order {order_id}, but order does not exist")
        raise HTTPException(status_code=404, detail="Order not found")

    rfid_result = await db.execute(
        select(RFID)
        .join(OrderRFID, RFID.id == OrderRFID.rfid_id)
        .join(Order, OrderRFID.order_id == Order.id)
        .options(joinedload(RFID.order_rfids))  # Асинхронная предзагрузка связанных записей
        .where(
            RFID.code == rfid_code,
            Order.is_completed == False  # Условие на активный заказ
        )
    )

    rfid = rfid_result.scalars().first()
    if rfid is not None:
        log.bind(type="users",
                 method=request.method,
                 current_user_id=current_user.id,
                 url=str(request.url),
                 headers=dict(request.headers),
                 params=dict(request.query_params)
                 ).error(f"Аttempt to add rfid {rfid_code} to order {order_id}, but this rfid is active in another order")
        raise HTTPException(status_code=422, detail="RFID in another order")

    rfid = RFID(code=rfid_code)
    db.add(rfid)
    await db.flush()

    order_rfid = OrderRFID(order_id=order.id, rfid_id=rfid.id)
    db.add(order_rfid)
    await db.commit()

    log.bind(type="users",
             method=request.method,
             current_user_id=current_user.id,
             url=str(request.url),
             headers=dict(request.headers),
             params=dict(request.query_params),
             ).info(f"Added rfid {rfid_code} to order {order_id}")

    return JSONResponse(content={"success": True}, status_code=200)


@router.get("/create", response_class=HTMLResponse)
async def create_order_page(request: Request,
                            current_user: User = Depends(get_current_user)):
    log.bind(type="users",
             method=request.method,
             current_user_id=current_user.id,
             url=str(request.url),
             headers=dict(request.headers),
             params=dict(request.query_params),
             ).info(f"Gained access create order template")

    return app_templates.TemplateResponse("create_order.html",
                                          {"request": request,
                                           "current_user": current_user})


@router.post("/{order_id}/complete")
async def complete_order(request: Request,
                         order_id: int,
                         db: AsyncSession = Depends(get_db),
                         current_user: User = Depends(get_current_user)):

    result = await db.execute(
        select(Order).options(selectinload(Order.rfids)).where(Order.id == order_id)
    )
    order = result.scalars().first()
    if order is None:
        log.bind(type="users",
                 method=request.method,
                 current_user_id=current_user.id,
                 url=str(request.url),
                 headers=dict(request.headers),
                 params=dict(request.query_params),
                 ).error(f"Try to complete order {order_id}, but order does not exist")
        raise HTTPException(status_code=404, detail="Order not found")
    order.is_completed = True
    for rfid in order.rfids:
        rfid.is_valid = False
    await db.commit()

    log.bind(type="users",
             method=request.method,
             current_user_id=current_user.id,
             url=str(request.url),
             headers=dict(request.headers),
             params=dict(request.query_params),
             ).info(f"Completed order {order_id}")

    return JSONResponse(content={"success": True}, status_code=200)


@router.get("/{order_id}", response_class=HTMLResponse)
async def read_order(order_id: int, request: Request,
                     db: AsyncSession = Depends(get_db),
                     current_user: User = Depends(get_current_user)):

    result = await db.execute(
        select(Order).options(
            selectinload(Order.rfids).selectinload(OrderRFID.rfid),
            selectinload(Order.items).selectinload(OrderItem.bottle)
        ).where(Order.id == order_id)
    )
    order = result.scalars().first()

    if order is None:
        log.bind(type="users",
                 method=request.method,
                 current_user_id=current_user.id,
                 url=str(request.url),
                 headers=dict(request.headers),
                 params=dict(request.query_params),
                 ).error(f"Try to complete order {order_id}, but order does not exist")
        raise HTTPException(status_code=404, detail="Order not found")

    # Проверим, является ли order.items итерируемым объектом
    if not hasattr(order.items, '__iter__'):
        raise HTTPException(status_code=500, detail="Order items are not iterable")

    order_details = {
        "id": order.id,
        "is_completed": order.is_completed,
        "rfids": [{"code": order_rfid.rfid.code, "timestamp": order_rfid.timestamp} for order_rfid in order.rfids],
        "items": []
    }

    items = order.items

    log.bind(type="users",
             method=request.method,
             current_user_id=current_user.id,
             url=str(request.url),
             headers=dict(request.headers),
             params=dict(request.query_params),
             ).info(f"Gained access to order {order_id}")

    return app_templates.TemplateResponse("order_detail.html",
                                          {"request": request,
                                           "order": order_details,
                                           "items": items,
                                           "current_user": current_user})

@router.post("/rfid/check")
async def rfid_check(request: Request, db: AsyncSession = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    data = await request.json()
    rfid = data.get("rfid")
    if not rfid:
        log.bind(type="users",
                 method=request.method,
                 current_user_id=current_user.id,
                 url=str(request.url),
                 headers=dict(request.headers),
                 params=dict(request.query_params),
                 ).info(f"Try to check rfid {rfid}, but rfid does not exist in request data")
        raise HTTPException(422, detail="Invalid rfid")

    rfid_result = await db.execute(
        select(RFID)
        .join(OrderRFID, RFID.id == OrderRFID.rfid_id)
        .join(Order, OrderRFID.order_id == Order.id)
        .options(joinedload(RFID.order_rfids))  # Асинхронная предзагрузка связанных записей
        .where(
            RFID.code == rfid,
            Order.is_completed == False  # Условие на активный заказ
        )
    )

    result = rfid_result.scalars().first()

    if result is None:
        return True

    return False
@router.post("/create", response_class=JSONResponse)
async def create_order(request: Request, db: AsyncSession = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    data = await request.json()
    rfids = data.get('rfids', [])
    order = Order()
    db.add(order)
    await db.flush()  # Ensuring the order is added and its ID is available

    errors = []
    for rfid_code in rfids:
        rfid_result = await db.execute(
            select(RFID)
            .join(OrderRFID, RFID.id == OrderRFID.rfid_id)
            .join(Order, OrderRFID.order_id == Order.id)
            .options(joinedload(RFID.order_rfids))  # Асинхронная предзагрузка связанных записей
            .where(
                RFID.code == rfid_code,
                Order.is_completed == False  # Условие на активный заказ
            )
        )

        rfid = rfid_result.scalars().first()

        if rfid is None:
            # If RFID not found, add it to the database
            rfid = RFID(code=rfid_code)
            db.add(rfid)
            await db.flush()  # Ensure the RFID is added and its ID is available
        else:
            # Check if the RFID is in any active orders
            errors.append({"rfid": rfid_code, "message": f"RFID {rfid_code} is already in use in an active order."})

        if not errors:
            order_rfid = OrderRFID(order_id=order.id, rfid_id=rfid.id)
            db.add(order_rfid)

    if errors:
        return JSONResponse(content={"success": False, "errors": errors}, status_code=400)

    await db.commit()
    return JSONResponse(content={"success": True}, status_code=200)
