from typing import Optional

from pydantic import BaseModel


class FeatureFlag(BaseModel):
    enable_services: bool = False
    enable_storage: Optional[bool] = False
    is_eval: Optional[bool] = False
    is_cli: Optional[bool] = True
    is_test: Optional[bool] = False
