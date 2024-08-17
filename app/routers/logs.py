from fastapi import Request, APIRouter, Depends
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import (AsyncSession)
from sqlalchemy.future import (select)
from app.database import get_db
from app.dependencies import get_superadmin_user
from app.models import User

router = APIRouter()

app_templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def get_logs(request: Request, db: AsyncSession = Depends(get_db)):
    with open('/logs/app.log', 'r') as file:
        logs = file.readlines()

    # blocked_ips = await db.execute(select(BlockedIP))
    # ip_count = len(blocked_ips.scalars().all())

    return app_templates.TemplateResponse("logs.html",
                                          {"request": request,
                                           "logs": logs})


@router.get("/download/{log_type}")
async def download_logs(log_type: str, current_user: User = Depends(get_superadmin_user)):
    types = {"app": "/logs/app.log",
             "db": "/logs/db.log",
             "users": "/logs/users.log",
             "admins": "/logs/admins/log",
             "terminals": "/logs/terminals.log"}

    def iter_file(path_to_log_file: str):
        with open(path_to_log_file, mode='rb') as file_like:
            while True:
                chunk = file_like.read(8192)
                if not chunk:
                    break
                yield chunk

    return StreamingResponse(iter_file(types[log_type]), media_type="text/plain",
                             headers={"Content-Disposition": "attachment; filename=app.log"})
