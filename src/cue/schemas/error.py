from typing import Optional

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    message: str
    code: Optional[str] = None
