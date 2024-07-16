from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models import Order, RFID, OrderRFID
from app.database import get_db

router = APIRouter()


@router.get("/")
async def get_orders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order))
    orders = result.scalars().all()
    return orders


@router.post("/order/{order_id}/complete")
async def complete_order(order_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Order).options(selectinload(Order.rfids)).where(Order.id == order_id)
    )
    order = result.scalars().first()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    order.is_completed = True
    for rfid in order.rfids:
        rfid.is_valid = False
    await db.commit()
    return JSONResponse(content={"message": "Order completed"})


@router.post("/create-order")
async def create_order(request: Request, db: AsyncSession = Depends(get_db)):
    form = await request.form()
    rfids = form.getlist('rfids')
    order = Order()
    db.add(order)
    await db.flush()  # Ensuring the order is added and its ID is available

    # Logging the received RFID codes for debugging
    print(f"Received RFID codes: {rfids}")

    for rfid_code in rfids:
        rfid_result = await db.execute(select(RFID).where(RFID.code == rfid_code))
        rfid = rfid_result.scalars().first()
        if rfid is None:
            # If RFID not found, add it to the database
            print(f"RFID {rfid_code} not found in the database. Adding it.")
            rfid = RFID(code=rfid_code)
            db.add(rfid)
            await db.flush()  # Ensure the RFID is added and its ID is available
        order_rfid = OrderRFID(order_id=order.id, rfid_id=rfid.id)
        db.add(order_rfid)

    await db.commit()
    response = RedirectResponse(url="/orders", status_code=303)
    return response
