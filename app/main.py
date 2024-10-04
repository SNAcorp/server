import os
import time

from fastapi import (FastAPI, Depends, HTTPException, Request)
from fastapi.middleware.cors import (CORSMiddleware)
from fastapi.responses import (HTMLResponse, JSONResponse, RedirectResponse, FileResponse)
from fastapi.staticfiles import (StaticFiles)
from sqlalchemy.ext.asyncio import (AsyncSession, create_async_engine)
from sqlalchemy.future import (select)
from sqlalchemy.orm import (sessionmaker)

from app.crypto import generate_rsa_keys
from app.database import (DATABASE_URL)
from app.dependencies import (get_current_user)
from app.jwt_auth import (verify_terminal)
from app.logging_config import log
from app.models import (Base, TerminalState, Bottle)
from app.routers import (auth, users, admin, superadmin, terminals, orders, bottles, rfid, logs, warehouse)
from app.routers.error_handlers import (custom_404_handler, custom_401_handler, custom_403_handler)
from app.schemas import (IsServerOnline, User)
from app.templates import app_templates
from app.topics import topics
from app.utils import load_keys

app = FastAPI()

"""-1 - гости; -2 - хацкеры; -3 - система"""

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(bind=engine,
                                 class_=AsyncSession,
                                 expire_on_commit=False)

app.add_exception_handler(404, custom_404_handler)
app.add_exception_handler(403, custom_403_handler)
app.add_exception_handler(401, custom_401_handler)

app.include_router(terminals.router, prefix="/terminals", tags=["terminals"])
app.include_router(orders.router, prefix="/orders", tags=["orders"])
app.include_router(bottles.router, prefix="/bottles", tags=["bottles"])
app.include_router(rfid.router, prefix="/rfid", tags=["rfid"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(superadmin.router, prefix="/superadmin", tags=["superadmin"])
app.include_router(logs.router, prefix="/logs", tags=["logs"])
app.include_router(warehouse.router, prefix="/warehouse", tags=["warehouse"])

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.on_event("startup")
async def startup():
    """
    This function is a startup event handler.
    It is called when the application starts up.
    It performs the following actions:
    1. Logs the application start up event.
    2. Generates RSA keys.
    3. Loads the RSA keys.
    4. Creates all tables in the database if they do not exist.
    5. Checks if an empty bottle exists. If not, creates one.
    6. Checks if all terminal states exist. If not, creates them.
    Returns:
        None
    """
    log.bind(type="app").info("Application start up")
    await generate_rsa_keys()
    await load_keys()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        empty_bottle_id = int(os.environ.get("EMPTY_BOTTLE_ID"))
        states = ["Active",
                  "Broken",
                  "Under Maintenance",
                  "Updating",
                  "Switched off",
                  "Connection lost"]
        result = await session.execute(select(Bottle).where(Bottle.id == empty_bottle_id))
        empty_bottle = result.scalars().first()
        if empty_bottle is None:
            empty_bottle = Bottle(
                id=empty_bottle_id,
                name="Empty Bottle",
                winery="N/A",
                rating_average=0,
                location="N/A",
                image_path300="images/empty300.png",
                image_path600="images/empty600.png",
                description="This is an empty slot.",
                wine_type="N/A",
                volume=0
            )
            session.add(empty_bottle)
        for state in states:
            status = await session.execute(select(TerminalState).where(TerminalState.state == state))
            if status.scalars().first() is None:
                new_state = TerminalState(state=state)
                session.add(new_state)
        await session.commit()


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
    """
    Logs incoming requests and their processing time.

    Args:
        request (Request): The incoming request.
        call_next (Callable): The next middleware or route handler.

    Returns:
        Response: The response to the request.

    Raises:
        HTTPException: If the response is None.

    Logs:
        - Information about incoming requests.
        - Information about processed requests, including category, status code, method, URL, and processing time.
    """
    start_time = time.time()

    # Логирование информации о запросе
    log.bind(type="app").info(f"Incoming request: {request.method} {request.url}")

    response = await call_next(request)

    if response is None:
        log.bind(type="app").error(f"Response is None for request: {request.method} {request.url}")
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

    log.bind(type="app").info(
        f"Request processed: {category} - {status_code} - {request.method} | {request.url} | ({process_time:.2f}s)")

    return response


@app.middleware("http")
async def detect_suspicious_requests(request: Request, call_next):
    """
    Middleware function that detects suspicious requests and redirects them to a 404 page.

    Args:
        request (Request): The incoming request.
        call_next (Callable): The next middleware or route handler.

    Returns:
        Response: The response to the request.

    Raises:
        None

    Logs:
        - A warning message if a suspicious request is detected.
        - An error message if the response is None.
    """
    if any(word in request.url.path.lower() for word in
           ["select", "drop", "insert", "wget", "php", "xml", "%"]):
        log.bind(type="app").warning(f"Suspicious request detected: {request.method} | {request.url}")
        return RedirectResponse("404.html", 303)

    response = await call_next(request)
    if response is None:
        log.bind(type="app").error(f"Response is None for request: {request.method} {request.url}")
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
    return response


@app.get("/learning", response_class=HTMLResponse)
async def read_learn(request: Request):
    from topics import topics
    return app_templates.TemplateResponse("lol.html", {"request": request, "topics": topics})


@app.get("/")
async def for_huckers(request: Request):
    return app_templates.TemplateResponse("index.html", {"request": request})

@app.get("/lol", response_class=JSONResponse)
async def for_scanner(request: Request):
    return app_templates.TemplateResponse("scaner.html", {"request": request, "topics": topics})
@app.get("/static/{image_name}")
async def get_image(image_name: str):
    """
    Get an image from the static directory.

    Args:
        image_name (str): The name of the image file.

    Returns:
        FileResponse: The requested image file.

    Raises:
        HTTPException: If the image file is not found.
    """
    file_path = f"app/static/{image_name}"
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    else:
        raise HTTPException(status_code=404, detail="Image not found")


@app.post("/", response_class=JSONResponse)
async def is_server_online(request: IsServerOnline):
    """
        Check if the server is online.

        Args:
            request (IsServerOnline): The request object containing a terminal ID and a token.

        Returns:
            dict: A dictionary with a boolean value indicating if the server is online.

        Raises:
            HTTPException: If the token is invalid or the terminal ID in the token does not match the one in the request.
    """
    payload = verify_terminal(request.token)
    if payload["terminal_id"] != request.terminal_id:
        raise HTTPException(status_code=403, detail="Invalid terminal ID")
    return {"is_online": True}


def main():
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=80, reload=True)


if __name__ == "__main__":
    main()
