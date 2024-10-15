from typing import Optional

from pydantic import BaseModel


class FeatureFlag(BaseModel):
    is_eval: Optional[bool] = False
    is_cli: Optional[bool] = False
