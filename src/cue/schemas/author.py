from typing import Dict, Optional

from pydantic import BaseModel


class Author(BaseModel):
    name: Optional[str] = None
    role: str
    metadata: Optional[Dict] = None
