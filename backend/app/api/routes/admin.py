"""Роуты для OS Dashboard — управление платформой (superadmin only)."""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    ApplicationCreate,
    ApplicationOut,
    ApplicationUpdate,
    HotelCreate,
    HotelOut,
    HotelUpdate,
)
from app.core.auth import get_platform_admin, hash_password
from app.db.database import get_session
from app.db.models.models import (
    Application,
    ApplicationStatus,
    Conversation,
    ConversationStatus,
    Hotel,
    HotelStatus,
    Operator,
    PlatformUser,
)

router = APIRouter(prefix="/admin", tags=["Admin (Platform)"])


# --- Hotels ---

@router.get("/hotels", response_model=list[HotelOut])
async def list_hotels(
    session: AsyncSession = Depends(get_session),
    admin: PlatformUser = Depends(get_platform_admin),
):
    """Список всех отелей."""
    result = await session.execute(
        select(Hotel).order_by(Hotel.created_at.desc())
    )
    return result.scalars().all()


@router.post("/hotels", response_model=HotelOut, status_code=201)
async def create_hotel(
    data: HotelCreate,
    session: AsyncSession = Depends(get_session),
    admin: PlatformUser = Depends(get_platform_admin),
):
    """Создать новый отель."""
    # Проверяем уникальность slug
    existing = await session.execute(
        select(Hotel).where(Hotel.slug == data.slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Slug уже используется")

    hotel = Hotel(
        name=data.name,
        slug=data.slug,
        system_prompt=data.system_prompt,
        telegram_bot_token=data.telegram_bot_token,
        wappi_api_key=data.wappi_api_key,
        wappi_profile_id=data.wappi_profile_id,
        pms_type=data.pms_type,
        pms_api_key=data.pms_api_key,
        pms_hotel_code=data.pms_hotel_code,
        ai_model=data.ai_model,
        config=data.config,
    )
    session.add(hotel)
    await session.commit()
    await session.refresh(hotel)
    return hotel


@router.get("/hotels/{hotel_id}", response_model=HotelOut)
async def get_hotel(
    hotel_id: int,
    session: AsyncSession = Depends(get_session),
    admin: PlatformUser = Depends(get_platform_admin),
):
    """Детали отеля."""
    result = await session.execute(
        select(Hotel).where(Hotel.id == hotel_id)
    )
    hotel = result.scalar_one_or_none()
    if not hotel:
        raise HTTPException(status_code=404, detail="Отель не найден")
    return hotel


@router.patch("/hotels/{hotel_id}", response_model=HotelOut)
async def update_hotel(
    hotel_id: int,
    data: HotelUpdate,
    session: AsyncSession = Depends(get_session),
    admin: PlatformUser = Depends(get_platform_admin),
):
    """Обновить настройки отеля."""
    result = await session.execute(
        select(Hotel).where(Hotel.id == hotel_id)
    )
    hotel = result.scalar_one_or_none()
    if not hotel:
        raise HTTPException(status_code=404, detail="Отель не найден")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(hotel, field, value)

    await session.commit()
    await session.refresh(hotel)
    return hotel


@router.post("/hotels/{hotel_id}/pause", response_model=HotelOut)
async def pause_hotel(
    hotel_id: int,
    session: AsyncSession = Depends(get_session),
    admin: PlatformUser = Depends(get_platform_admin),
):
    """Приостановить бота отеля."""
    result = await session.execute(select(Hotel).where(Hotel.id == hotel_id))
    hotel = result.scalar_one_or_none()
    if not hotel:
        raise HTTPException(status_code=404, detail="Отель не найден")
    hotel.status = HotelStatus.paused
    await session.commit()
    await session.refresh(hotel)
    return hotel


@router.post("/hotels/{hotel_id}/resume", response_model=HotelOut)
async def resume_hotel(
    hotel_id: int,
    session: AsyncSession = Depends(get_session),
    admin: PlatformUser = Depends(get_platform_admin),
):
    """Возобновить бота отеля."""
    result = await session.execute(select(Hotel).where(Hotel.id == hotel_id))
    hotel = result.scalar_one_or_none()
    if not hotel:
        raise HTTPException(status_code=404, detail="Отель не найден")
    hotel.status = HotelStatus.active
    await session.commit()
    await session.refresh(hotel)
    return hotel


# --- Applications ---

@router.get("/applications", response_model=list[ApplicationOut])
async def list_applications(
    status_filter: Optional[ApplicationStatus] = Query(None, alias="status"),
    session: AsyncSession = Depends(get_session),
    admin: PlatformUser = Depends(get_platform_admin),
):
    """Список заявок."""
    query = select(Application).order_by(Application.created_at.desc())
    if status_filter:
        query = query.where(Application.status == status_filter)
    result = await session.execute(query)
    return result.scalars().all()


@router.post("/applications", response_model=ApplicationOut, status_code=201)
async def create_application(
    data: ApplicationCreate,
    session: AsyncSession = Depends(get_session),
):
    """Создать заявку на подключение (публичный эндпоинт — без авторизации)."""
    app = Application(
        hotel_name=data.hotel_name,
        contact_name=data.contact_name,
        contact_phone=data.contact_phone,
        contact_email=data.contact_email,
        form_data=data.form_data,
    )
    session.add(app)
    await session.commit()
    await session.refresh(app)
    return app


@router.patch("/applications/{app_id}", response_model=ApplicationOut)
async def update_application(
    app_id: int,
    data: ApplicationUpdate,
    session: AsyncSession = Depends(get_session),
    admin: PlatformUser = Depends(get_platform_admin),
):
    """Обновить заявку (статус, данные)."""
    result = await session.execute(
        select(Application).where(Application.id == app_id)
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(app, field, value)

    await session.commit()
    await session.refresh(app)
    return app


@router.post("/applications/{app_id}/activate", response_model=HotelOut)
async def activate_application(
    app_id: int,
    data: HotelCreate,
    session: AsyncSession = Depends(get_session),
    admin: PlatformUser = Depends(get_platform_admin),
):
    """Активировать заявку — создать отель и связать."""
    result = await session.execute(
        select(Application).where(Application.id == app_id)
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    if app.status == ApplicationStatus.active:
        raise HTTPException(status_code=400, detail="Заявка уже активирована")

    # Создаём отель
    hotel = Hotel(
        name=data.name or app.hotel_name,
        slug=data.slug,
        system_prompt=data.system_prompt or app.generated_prompt,
        telegram_bot_token=data.telegram_bot_token,
        wappi_api_key=data.wappi_api_key,
        wappi_profile_id=data.wappi_profile_id,
        pms_type=data.pms_type,
        pms_api_key=data.pms_api_key,
        pms_hotel_code=data.pms_hotel_code,
        ai_model=data.ai_model,
        config=data.config,
    )
    session.add(hotel)
    await session.flush()  # Получаем hotel.id

    # Связываем заявку с отелем
    app.hotel_id = hotel.id
    app.status = ApplicationStatus.active

    await session.commit()
    await session.refresh(hotel)
    return hotel


# --- Platform Stats ---

@router.get("/stats")
async def get_platform_stats(
    session: AsyncSession = Depends(get_session),
    admin: PlatformUser = Depends(get_platform_admin),
):
    """Общая статистика платформы."""
    # Отели
    hotels_result = await session.execute(
        select(Hotel.status, func.count()).group_by(Hotel.status)
    )
    hotels_by_status = {row[0]: row[1] for row in hotels_result.all()}

    # Диалоги за сегодня
    now = datetime.utcnow() + timedelta(hours=6)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    today_convs = await session.execute(
        select(func.count(Conversation.id))
        .where(Conversation.created_at >= today_start)
    )
    today_total = today_convs.scalar() or 0

    # Всего диалогов
    total_convs = await session.execute(
        select(func.count(Conversation.id))
    )
    total = total_convs.scalar() or 0

    # Заявки pending
    pending_apps = await session.execute(
        select(func.count(Application.id))
        .where(Application.status == ApplicationStatus.pending)
    )
    pending = pending_apps.scalar() or 0

    return {
        "hotels": {
            "active": hotels_by_status.get(HotelStatus.active, 0),
            "paused": hotels_by_status.get(HotelStatus.paused, 0),
            "archived": hotels_by_status.get(HotelStatus.archived, 0),
            "total": sum(hotels_by_status.values()),
        },
        "conversations": {
            "today": today_total,
            "total": total,
        },
        "applications": {
            "pending": pending,
        },
    }
