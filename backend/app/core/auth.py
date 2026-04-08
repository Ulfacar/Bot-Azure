from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import get_session
from app.db.models.models import Operator, PlatformUser

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(
    operator_id: int,
    hotel_id: int | None = None,
    role: str = "operator",
) -> str:
    """Создать JWT токен для оператора отеля."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "sub": str(operator_id),
        "hotel_id": hotel_id,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_platform_token(platform_user_id: int) -> str:
    """Создать JWT токен для админа платформы."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "sub": str(platform_user_id),
        "role": "superadmin",
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def _decode_token(token: str) -> dict:
    """Декодировать JWT, вернуть payload или бросить 401."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Неверный токен",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        if payload.get("sub") is None:
            raise credentials_exception
        return payload
    except (JWTError, TypeError, ValueError):
        raise credentials_exception


async def get_current_operator(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> Operator:
    """Получить текущего оператора из JWT. Проверяет hotel_id."""
    payload = _decode_token(token)
    operator_id = int(payload["sub"])

    result = await session.execute(
        select(Operator).where(Operator.id == operator_id, Operator.is_active == True)
    )
    operator = result.scalar_one_or_none()
    if operator is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный токен",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return operator


async def get_current_hotel_id(
    token: str = Depends(oauth2_scheme),
) -> int:
    """Извлечь hotel_id из JWT. Для фильтрации данных по отелю."""
    payload = _decode_token(token)
    hotel_id = payload.get("hotel_id")
    if hotel_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Токен не содержит hotel_id",
        )
    return int(hotel_id)


async def get_platform_admin(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> PlatformUser:
    """Получить админа платформы из JWT. Только для /api/admin/* роутов."""
    payload = _decode_token(token)
    if payload.get("role") != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для администраторов платформы",
        )
    user_id = int(payload["sub"])
    result = await session.execute(
        select(PlatformUser).where(
            PlatformUser.id == user_id, PlatformUser.is_active == True
        )
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный токен",
        )
    return user
