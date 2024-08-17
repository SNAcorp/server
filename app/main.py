import os
import time
from datetime import (timedelta)
from loguru import logger

from fastapi import (FastAPI, Depends, HTTPException, Request, Form)
from fastapi.middleware.cors import (CORSMiddleware)
from fastapi.staticfiles import (StaticFiles)
from fastapi.responses import (HTMLResponse, JSONResponse, RedirectResponse, FileResponse)
from fastapi.templating import (Jinja2Templates)

from sqlalchemy.ext.asyncio import (AsyncSession, create_async_engine)
from sqlalchemy.future import (select)
from sqlalchemy.orm import (selectinload, sessionmaker)

from app.crud import (get_unverified_users, get_all_users, get_blocked_users, get_unblocked_users)
from app.crypto import generate_rsa_keys
from app.dependencies import (get_current_user, get_admin_user)
from app.routers import (auth, users, admin, superadmin, terminals, orders, bottles, rfid, logs)
from app.jwt_auth import (verify_terminal)
from app.models import (Base, EMPTY_BOTTLE_ID, RFID, OrderItem, OrderRFID, TerminalState, Order, Terminal, Bottle)
from app.database import (get_db, DATABASE_URL)
from app.schemas import (IsServerOnline, User)
from app.routers.error_handlers import (custom_404_handler, custom_401_handler)
from app.utils import load_keys

app = FastAPI()

# DATABASE_URL = "postgresql+asyncpg://nikitastepanov@localhost/terminals"
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

logger.add("/logs/app.log", rotation="1 day", retention="7 days", level="DEBUG")

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(bind=engine,
                                 class_=AsyncSession,
                                 expire_on_commit=False)

app.add_exception_handler(404, custom_404_handler)
app.add_exception_handler(401, custom_401_handler)

app.include_router(terminals.router, prefix="/terminal", tags=["terminals"])
app.include_router(orders.router, prefix="/orders", tags=["orders"])
app.include_router(bottles.router, prefix="/bottles", tags=["bottles"])
app.include_router(rfid.router, prefix="/rfid", tags=["rfid"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(superadmin.router, prefix="/superadmin", tags=["superadmin"])
app.include_router(logs.router, prefix="/logs", tags=["logs"])

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.on_event("startup")
async def startup():
    logger.info("Application start up")
    await generate_rsa_keys()
    await load_keys()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        states = ["Active",
                  "Broken",
                  "Under Maintenance",
                  "Updating",
                  "Switched off",
                  "Connection lost"]
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


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    # Логирование информации о запросе
    logger.info(f"Incoming request: {request.method} {request.url}")

    response = await call_next(request)

    if response is None:
        logger.error(f"Response is None for request: {request.method} {request.url}")
        print(f"LOL, Response is None for request: {request.method} {request.url}")
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

    process_time = time.time() - start_time
    status_code = response.status_code

    # Определяем категорию запроса
    if status_code >= 500:
        category = "Failed"
    elif 400 <= status_code < 500:
        category = "Suspicious"
    else:
        category = "Successful"

    logger.info(f"Request processed: {category} - {status_code} - {request.method} | {request.url} | ({process_time:.2f}s)")

    return response


@app.middleware("http")
async def detect_suspicious_requests(request: Request, call_next):
    if any(word in request.url.path.lower() for word in ["select", "drop", "insert", "update", "delete", "wget", "php", "xml", "%", "-"]):
        logger.warning(f"Suspicious request detected: {request.method} | {request.url}")
        return RedirectResponse("404.html", 303)

    response = await call_next(request)
    if response is None:
        logger.error(f"Response is None for request: {request.method} {request.url}")
        print(f"LOL, Response is None for request: {request.method} {request.url}")
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
    return response


@app.get("/learning", response_class=HTMLResponse)
async def read_learn(request: Request):
    from topics import topics
    return app_templates.TemplateResponse("lol.html", {"request": request, "topics": topics})


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
    if current_user is not None:
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

    items = order.items
    print("items", items)

    return app_templates.TemplateResponse("order_detail.html",
                                          {"request": request,
                                           "order": order_details,
                                           "items": items,
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
async def for_huckers(current_user: User = Depends(get_current_user)):
    if current_user is not None:
        return RedirectResponse("/orders", 303)
    return {"msg": "Hello, how are you mr/mrs?) What are you need at this website?"}


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
