# error_handlers.py
from fastapi import Request, HTTPException, Depends
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import HTMLResponse, RedirectResponse, Response

from app.dependencies import get_current_user
from app.schemas import User
from app.templates import app_templates


async def custom_404_handler(request: Request, exc: StarletteHTTPException,
                             current_user: User = Depends(get_current_user)) -> HTMLResponse:
    return app_templates.TemplateResponse("404.html", {"request": request,
                                                       "current_user": current_user}, status_code=404)


async def custom_403_handler(request: Request, exc: HTTPException,
                             current_user: User = Depends(get_current_user)):
    return app_templates.TemplateResponse("403.html", {"request": request,
                                                       "current_user": current_user}, status_code=403)


async def custom_401_handler(request: Request, exc: HTTPException,
                             current_user: User = Depends(get_current_user)):
    if request.url.path != "/auth/login":
        return RedirectResponse("/auth/login", status_code=303)
    else:
        return app_templates.TemplateResponse("login_register.html",
                                              {"request": request})
