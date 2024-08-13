# error_handlers.py
from fastapi import Request, HTTPException
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import HTMLResponse, RedirectResponse


templates = Jinja2Templates(directory="app/templates")


async def custom_404_handler(request: Request, exc: StarletteHTTPException) -> HTMLResponse:
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)


async def custom_401_handler(request: Request, exc: HTTPException) -> RedirectResponse:
    return RedirectResponse("/login", status_code=303)
