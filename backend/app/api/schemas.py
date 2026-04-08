from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.db.models.models import (
    ApplicationStatus,
    ChannelType,
    ConversationCategory,
    ConversationStatus,
    HotelStatus,
    Language,
    MessageSender,
    PlatformRole,
)


# --- Auth ---

class LoginRequest(BaseModel):
    email: str
    password: str


class PlatformLoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    hotel_id: Optional[int] = None
    role: Optional[str] = None


# --- Operator ---

class OperatorCreate(BaseModel):
    name: str
    email: str
    password: str
    is_admin: bool = False
    telegram_id: Optional[str] = None
    hotel_id: Optional[int] = None


class OperatorOut(BaseModel):
    id: int
    hotel_id: Optional[int] = None
    name: str
    email: str
    is_admin: bool
    telegram_id: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Hotel ---

class HotelCreate(BaseModel):
    name: str
    slug: str
    system_prompt: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    wappi_api_key: Optional[str] = None
    wappi_profile_id: Optional[str] = None
    pms_type: Optional[str] = None
    pms_api_key: Optional[str] = None
    pms_hotel_code: Optional[str] = None
    ai_model: str = "anthropic/claude-3.5-haiku"
    config: Optional[dict] = None


class HotelUpdate(BaseModel):
    name: Optional[str] = None
    system_prompt: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    wappi_api_key: Optional[str] = None
    wappi_profile_id: Optional[str] = None
    pms_type: Optional[str] = None
    pms_api_key: Optional[str] = None
    pms_hotel_code: Optional[str] = None
    ai_model: Optional[str] = None
    status: Optional[HotelStatus] = None
    config: Optional[dict] = None


class HotelOut(BaseModel):
    id: int
    name: str
    slug: str
    ai_model: str
    status: HotelStatus
    pms_type: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- Application ---

class ApplicationCreate(BaseModel):
    hotel_name: str
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    form_data: Optional[dict] = None


class ApplicationUpdate(BaseModel):
    status: Optional[ApplicationStatus] = None
    form_data: Optional[dict] = None
    generated_prompt: Optional[str] = None


class ApplicationOut(BaseModel):
    id: int
    status: ApplicationStatus
    hotel_name: str
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    form_data: Optional[dict] = None
    hotel_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- Platform User ---

class PlatformUserOut(BaseModel):
    id: int
    email: str
    role: PlatformRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Client ---

class ClientOut(BaseModel):
    id: int
    name: Optional[str]
    phone: Optional[str]
    username: Optional[str]
    channel: ChannelType
    channel_user_id: str
    language: Language
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Conversation ---

class ConversationOut(BaseModel):
    id: int
    client_id: int
    status: ConversationStatus
    category: ConversationCategory
    assigned_operator_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    client: Optional[ClientOut] = None

    model_config = {"from_attributes": True}


class ConversationUpdate(BaseModel):
    status: Optional[ConversationStatus] = None
    category: Optional[ConversationCategory] = None
    assigned_operator_id: Optional[int] = None


# --- Message ---

class MessageOut(BaseModel):
    id: int
    conversation_id: int
    sender: MessageSender
    text: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)


# --- Notes ---

class NoteCreate(BaseModel):
    phone: str = Field(..., min_length=5, max_length=50)
    text: str = Field(..., min_length=1, max_length=2000)


class NoteUpdate(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class NoteOut(BaseModel):
    id: int
    phone: str
    text: str
    added_by_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
