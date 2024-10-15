from typing import Optional

from pydantic import BaseModel


class User(BaseModel):
    id: str
    email: str
    is_active: bool = True
    is_superuser: bool = False
    full_name: str = None


# Properties to receive via API on creation
class UserCreate(BaseModel):
    email: str
    password: str
    name: Optional[str] = None
    phone_number: Optional[str] = None
    invite_code: Optional[str] = None
    is_superuser: Optional[bool] = False
