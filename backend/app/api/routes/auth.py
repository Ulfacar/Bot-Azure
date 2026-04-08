from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    LoginRequest,
    OperatorCreate,
    OperatorOut,
    PlatformLoginRequest,
    TokenResponse,
)
from app.core.auth import (
    create_access_token,
    create_platform_token,
    get_current_operator,
    hash_password,
    verify_password,
)
from app.db.database import get_session
from app.db.models.models import Operator, PlatformUser

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, session: AsyncSession = Depends(get_session)):
    """Вход менеджера отеля — возвращает JWT токен с hotel_id."""
    result = await session.execute(
        select(Operator).where(Operator.email == data.email)
    )
    operator = result.scalar_one_or_none()

    if not operator or not verify_password(data.password, operator.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    if not operator.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт деактивирован",
        )

    token = create_access_token(operator.id, hotel_id=operator.hotel_id)
    return TokenResponse(
        access_token=token,
        hotel_id=operator.hotel_id,
    )


@router.post("/platform-login", response_model=TokenResponse)
async def platform_login(
    data: PlatformLoginRequest, session: AsyncSession = Depends(get_session)
):
    """Вход администратора платформы — возвращает JWT с role=superadmin."""
    result = await session.execute(
        select(PlatformUser).where(PlatformUser.email == data.email)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт деактивирован",
        )

    token = create_platform_token(user.id)
    return TokenResponse(access_token=token, role="superadmin")


@router.post("/register", response_model=OperatorOut, status_code=201)
async def register_first_admin(
    data: OperatorCreate, session: AsyncSession = Depends(get_session)
):
    """Регистрация первого админа для отеля. Работает только если в БД нет ни одного оператора."""
    result = await session.execute(select(Operator).limit(1))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Админ уже существует. Используйте /login",
        )

    operator = Operator(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        is_admin=True,
        telegram_id=data.telegram_id,
        hotel_id=data.hotel_id,
    )
    session.add(operator)
    await session.commit()
    await session.refresh(operator)
    return operator


@router.get("/me", response_model=OperatorOut)
async def get_me(operator: Operator = Depends(get_current_operator)):
    """Текущий авторизованный менеджер."""
    return operator
