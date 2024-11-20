from typing import Optional

from pydantic import BaseModel


class FeatureFlag(BaseModel):
    enable_services: bool = False
    enable_storage: Optional[bool] = False
