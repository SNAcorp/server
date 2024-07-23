from typing import Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime


class TerminalCreate(BaseModel):
    key: str


class TerminalResponse(BaseModel):
    id: int

    class Config:
        from_attributes = True


class TerminalBottleCreate(BaseModel):
    bottle_id: int
    slot_number: int
    remaining_volume: float


class BottleCreate(BaseModel):
    name: str
    winery: str
    rating_average: float
    location: str
    url300: str
    url600: str
    description: str
    wine_type: str
    volume: float


class BottleResponse(BaseModel):
    id: int

    class Config:
        from_attributes = True


class RegisterTerminalResponse(BaseModel):
    terminal_id: int
    token: str


class UseTerminalRequest(BaseModel):
    terminal_id: int
    rfid_code: str
    slot_number: int
    volume: int
    token: str


class ResetTerminalRequest(BaseModel):
    terminal_id: int
    token: str


class IsServerOnline(BaseModel):
    terminal_id: int
    token: str


class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    phone_number: str


class UserCreate(UserBase):
    password: str
    confirm_password: str


class UserLogin(BaseModel):
    email: str
    password: str


class UserInDBBase(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    is_verified: bool
    role: str
    registration_date: datetime
    block_date: Optional[datetime] = None

    class Config:
        orm_mode = True


class User(UserInDBBase):
    pass


class UserInDB(UserInDBBase):
    hashed_password: str
