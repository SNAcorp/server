import os
import json
import aiofiles
from fastapi import APIRouter, Request, Depends, Query, HTTPException, WebSocket
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from typing import Optional, Dict
from datetime import datetime

from app.templates import app_templates
from app.logging_config import log
from app.dependencies import get_superadmin_user
from app.schemas import User

router = APIRouter()

log_paths: Dict[str, str] = {
    "app": "/logs/app.json",
    "db": "/logs/db.json",
    "users": "/logs/users.json",
    "admins": "/logs/admins.json",
    "terminals": "/logs/terminals.json",
    "system": "/logs/system.json"
}


@router.get("/", response_class=HTMLResponse)
async def show_logs(request: Request, current_user: User = Depends(get_superadmin_user)):
    log.bind(type="admins",
             method=request.method,
             current_user_id=current_user.id,
             url=str(request.url),
             headers=dict(request.headers),
             params=dict(request.query_params),
             ).info(f"Gained logs template")

    return app_templates.TemplateResponse("logs.html", {
        "request": request,
        "current_user": current_user,
        "log_type": "app",
        "log_content": "",
        "log_paths": log_paths
    })


@router.get("/download/{log_type}")
async def download_logs(request: Request, log_type: str, current_user: User = Depends(get_superadmin_user)):
    path = log_paths.get(log_type)

    async def iter_file(path_to_log_file: str):
        async with aiofiles.open(path_to_log_file, mode='rb') as file_like:
            while True:
                chunk = await file_like.read(8192)
                if not chunk:
                    break
                yield chunk

    log.bind(type="admins",
             method=request.method,
             current_user_id=current_user.id,
             url=str(request.url),
             headers=dict(request.headers),
             params=dict(request.query_params),
             ).info(f"Downloading logs for {log_type}")
    return StreamingResponse(iter_file(path), media_type="application/json",
                             headers={"Content-Disposition": f"attachment; filename={log_type}.json"})


@router.delete("/delete_all_logs", response_class=JSONResponse)
async def delete_all_logs(request: Request, current_user: User = Depends(get_superadmin_user)):
    cleared_logs = []
    for log_type, path in log_paths.items():
        try:
            if os.path.exists(path):
                async with aiofiles.open(path, 'w') as file:
                    await file.write("")
                cleared_logs.append(log_type)
                log.bind(type="admins",
                         method=request.method,
                         current_user_id=current_user.id,
                         url=str(request.url),
                         headers=dict(request.headers),
                         params=dict(request.query_params),
                         ).info(f"Delete logs for {log_type}")
        except Exception as e:
            log.bind(type="admins",
                     method=request.method,
                     current_user_id=current_user.id,
                     url=str(request.url),
                     headers=dict(request.headers),
                     params=dict(request.query_params),
                     ).info(f"Tried to delete logs for {log_type} but an error occurred: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to clear {log_type} logs: {str(e)}")

    if not cleared_logs:
        log.bind(type="admins",
                 method=request.method,
                 current_user_id=current_user.id,
                 url=str(request.url),
                 headers=dict(request.headers),
                 params=dict(request.query_params),
                 ).info(f"Tried to clear all logs, but all logs are empty")
        return JSONResponse(content={"detail": "No log files were found or cleared."}, status_code=200)
    log.bind(type="admins",
             method=request.method,
             current_user_id=current_user.id,
             url=str(request.url),
             headers=dict(request.headers),
             params=dict(request.query_params),
             ).info(f"Delete all logs")
    return JSONResponse(content={"detail": f"Cleared logs for: {', '.join(cleared_logs)}"}, status_code=200)