import os
import subprocess

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.crud import get_unverified_users, get_all_users, get_blocked_users, get_unblocked_users
from app.dependencies import get_current_user, get_admin_user
from app.routers import auth, users, admin, superadmin
from app.jwt_auth import verify_terminal
from app.models import Base, EMPTY_BOTTLE_ID, RFID, OrderItem, OrderRFID, TerminalState
from app.routers import terminals, orders, bottles, rfid

from fastapi import Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import or_
from app.models import Order, Terminal, Bottle
from app.database import get_db
from app.schemas import IsServerOnline, User
from datetime import timedelta, datetime

app = FastAPI()

# DATABASE_URL = "postgresql+asyncpg://nikitastepanov@localhost/terminals"
DATABASE_URL = os.getenv('DATABASE_URL')
#
# engine = create_engine("postgresql://server:v9023aSH@db:5432/terminals", echo=True)
#
# # Создание соединения
# conn = engine.connect()
# conn.execute("commit")
#
# # Создание базы данных "terminals"
# conn.execute("CREATE DATABASE terminals")
#
# # Закрытие соединения
# conn.close()

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

app.include_router(terminals.router, prefix="/terminal", tags=["terminals"])
app.include_router(orders.router, prefix="/orders", tags=["orders"])
app.include_router(bottles.router, prefix="/bottles", tags=["bottles"])
app.include_router(rfid.router, prefix="/rfid", tags=["rfid"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(superadmin.router, prefix="/superadmin", tags=["superadmin"])

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        states = [
            "Active",
            "Broken",
            "Under Maintenance",
            "Updating",
            "Switched off",
            "Connection lost"
        ]
        result = await session.execute(select(Bottle).where(Bottle.id == EMPTY_BOTTLE_ID))
        empty_bottle = result.scalars().first()
        if empty_bottle is None:
            empty_bottle = Bottle(
                id=EMPTY_BOTTLE_ID,
                name="Empty Bottle",
                winery="N/A",
                rating_average=0.0,
                location="N/A",
                image_path300="images/empty300.png",
                image_path600="images/empty600.png",
                description="This is an empty slot.",
                wine_type="N/A",
                volume=0.0
            )
            session.add(empty_bottle)
        for state in states:
            status = await session.execute(select(TerminalState).where(TerminalState.state == state))
            if status.scalars().first() is None:
                new_state = TerminalState(state=state)
                session.add(new_state)
        await session.commit()


app_templates = Jinja2Templates(directory="app/templates")

origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:3000",
    # Добавьте другие допустимые источники здесь
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/bottles", response_class=HTMLResponse)
async def list_bottles(request: Request, current_user: User = Depends(get_current_user),
                       session: AsyncSession = Depends(get_db)):
    if current_user is None:
        return RedirectResponse("/login", 302)
    result = await session.execute(select(Bottle).filter(Bottle.id != -1))
    bottles = result.scalars().all()
    sorted_bottles = sorted(bottles, key=lambda x: x.id)
    return app_templates.TemplateResponse("bottle_list.html",
                                          {"request": request, "bottles": sorted_bottles, "current_user": current_user})


@app.get("/orders", response_class=HTMLResponse)
async def read_orders(request: Request,
                      db: AsyncSession = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    if current_user is None:
        return RedirectResponse("/login", 303)

    result = await db.execute(select(Order).options(selectinload(Order.items)))
    orders = result.scalars().all()

    return app_templates.TemplateResponse("orders.html",
                                          {"request": request,
                                           "orders": orders,
                                           "timedelta": timedelta,
                                           "current_user": current_user})


@app.post("/order/{order_id}/add_rfid")
async def add_rfid_to_order(order_id: int,
                            rfid_code: str = Form(...),
                            db: AsyncSession = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalars().first()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    rfid_result = await db.execute(select(RFID).where(RFID.code == rfid_code))
    rfid = rfid_result.scalars().first()
    if rfid is None:
        raise HTTPException(status_code=404, detail="RFID not found")

    order_rfid = OrderRFID(order_id=order.id, rfid_id=rfid.id)
    db.add(order_rfid)
    await db.commit()

    return {"message": "RFID added to order successfully"}


@app.get("/login")
def admin_panel(request: Request,
                current_user: User = Depends(get_current_user)):
    if current_user:
        return RedirectResponse("/orders", 303)
    return app_templates.TemplateResponse("login_register.html",
                                          {"request": request})


@app.get("/order/{order_id}", response_class=HTMLResponse)
async def read_order(order_id: int, request: Request,
                     db: AsyncSession = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    if current_user is None:
        return RedirectResponse("/login", 303)

    result = await db.execute(
        select(Order).options(
            selectinload(Order.rfids).selectinload(OrderRFID.rfid),
            selectinload(Order.items).selectinload(OrderItem.bottle)
        ).where(Order.id == order_id)
    )
    order = result.scalars().first()

    if order is None:
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

    for item in order.items:
        order_details["items"].append({
            "bottle_name": item.bottle.name,
            "bottle_id": item.bottle.id,
            "total_volume": item.volume
        })

    return app_templates.TemplateResponse("order_detail.html",
                                          {"request": request,
                                           "order": order_details,
                                           "current_user": current_user})


@app.get("/create-order", response_class=HTMLResponse)
async def create_order_page(request: Request,
                            current_user: User = Depends(get_current_user)):
    if current_user is None:
        return RedirectResponse("/login", 303)
    return app_templates.TemplateResponse("create_order.html",
                                          {"request": request,
                                           "current_user": current_user})


@app.post("/create-order", response_class=JSONResponse)
async def create_order(request: Request, db: AsyncSession = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    if current_user is None:
        return RedirectResponse("/login", 303)
    data = await request.json()
    rfids = data.get('rfids', [])
    order = Order()
    db.add(order)
    await db.flush()  # Ensuring the order is added and its ID is available

    # Logging the received RFID codes for debugging
    print(f"Received RFID codes: {rfids}")

    errors = []
    for rfid_code in rfids:
        rfid_result = await db.execute(select(RFID).where(RFID.code == rfid_code))
        rfid = rfid_result.scalars().first()

        if rfid is None:
            # If RFID not found, add it to the database
            print(f"RFID {rfid_code} not found in the database. Adding it.")
            rfid = RFID(code=rfid_code)
            db.add(rfid)
            await db.flush()  # Ensure the RFID is added and its ID is available
        else:
            # Check if the RFID is in any active orders
            active_order_result = await db.execute(
                select(OrderRFID)
                    .join(Order)
                    .where(Order.is_completed == False, OrderRFID.rfid_id == rfid.id)
            )
            active_order_rfid = active_order_result.scalars().first()
            if active_order_rfid:
                errors.append({"rfid": rfid_code, "message": f"RFID {rfid_code} is already in use in an active order."})

        if not errors:
            order_rfid = OrderRFID(order_id=order.id, rfid_id=rfid.id)
            db.add(order_rfid)

    if errors:
        return JSONResponse(content={"success": False, "errors": errors}, status_code=400)

    await db.commit()
    return JSONResponse(content={"success": True}, status_code=200)


@app.get("/terminals", response_class=HTMLResponse)
async def dashboard(request: Request,
                    db: AsyncSession = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    if current_user is None:
        return RedirectResponse("/login", 303)
    result = await db.execute(select(Terminal).options(selectinload(Terminal.status)))
    terminals = result.scalars().all()
    return app_templates.TemplateResponse("terminals.html",
                                          {"request": request,
                                           "terminals": terminals,
                                           "current_user": current_user})


@app.get("/", response_class=JSONResponse)
async def for_huckers():
    return {"msg": "Hello, how are you mr/mrs?)"}


@app.get("/static/{image_name}")
async def get_image(image_name: str):
    file_path = f"app/static/{image_name}"
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    else:
        raise HTTPException(status_code=404, detail="Image not found")



@app.get("/terminals/{terminal_id}", response_class=HTMLResponse)
async def manage_terminal(request: Request,
                          terminal_id: int,
                          db: AsyncSession = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    if current_user is None:
        return RedirectResponse("/login", 303)
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


@app.get("/admin/panel", response_class=HTMLResponse)
async def admin_panel(request: Request, db: AsyncSession = Depends(get_db),
                      current_user: User = Depends(get_admin_user)):
    if current_user is None:
        return RedirectResponse("/login", 303)
    all_users = await get_all_users(db)
    unblocked_users = await get_unblocked_users(db)
    blocked_users = await get_blocked_users(db)
    unverified_users = []
    if current_user.is_superuser:
        unverified_users = await get_unverified_users(db)

    return app_templates.TemplateResponse("admin_panel.html", {
        "request": request,
        "current_user": current_user,
        "all_users": all_users,
        "unblocked_users": unblocked_users,
        "blocked_users": blocked_users,
        "unverified_users": unverified_users
    })


@app.post("/", response_class=JSONResponse)
async def reset_bottles_endpoint(request: IsServerOnline):
    payload = verify_terminal(request.token)
    if payload["terminal_id"] != request.terminal_id:
        raise HTTPException(status_code=403, detail="Invalid terminal ID")
    return {"is_online": True}


def main():
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=80, reload=True)


if __name__ == "__main__":
    main()
