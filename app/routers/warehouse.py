from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.exceptions import HTTPException
from sqlalchemy.orm import selectinload

from app.database import get_db

from sqlalchemy.ext.asyncio import (AsyncSession)
from sqlalchemy.future import (select)

from app.dependencies import get_current_user
from app.models import Bottle, WarehouseBottle, User
from app.schemas import UpdateStockRequest
from app.templates import app_templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def get_warehouse_data(request: Request,
                             current_user: User = Depends(get_current_user),
                             db: AsyncSession = Depends(get_db)):
    # Получаем данные о бутылках на складе с присоединением информации о бутылке
    warehouse_data = await db.execute(
        select(WarehouseBottle).options(selectinload(WarehouseBottle.bottle))
    )
    warehouse_data = warehouse_data.scalars().all()

    return app_templates.TemplateResponse("warehouse.html", {"request": request,
                                                             "current_user": current_user,
                                                             "warehouse_data": warehouse_data})


# Роут для обновления количества бутылок
@router.post("/update-stock")
async def update_warehouse_stock(request: UpdateStockRequest,
                                 current_user: User = Depends(get_current_user),
                                 db: AsyncSession = Depends(get_db)):
    """
    Обновление стока бутылок на складе (увеличение количества).
    """
    # Поиск записи о бутылке на складе по bottle_id
    warehouse_bottle = await db.execute(
        select(WarehouseBottle).filter(WarehouseBottle.bottle_id == request.bottle_id)
    )
    warehouse_bottle = warehouse_bottle.scalars().first()

    # Если бутылка не найдена, возвращаем ошибку
    if not warehouse_bottle:
        raise HTTPException(status_code=404, detail="Warehouse bottle not found")

    # Увеличиваем количество бутылок на складе
    warehouse_bottle.quantity += request.quantity
    await db.commit()

    return {"message": f"Stock updated successfully. New quantity: {warehouse_bottle.quantity}"}
