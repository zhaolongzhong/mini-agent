from pydantic import BaseModel


class ErrorResponse(BaseModel):
    message: str
    code: str | None = None
