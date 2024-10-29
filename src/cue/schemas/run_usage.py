from typing import Optional
from datetime import datetime

from pydantic import BaseModel


class RunUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0


class RunUsageAndLimits(BaseModel):
    usage: RunUsage  # current usage
    usage_limits: RunUsage  # max usage
    start_time: datetime = datetime.now()
    end_time: Optional[datetime] = None
    duration: Optional[int] = None
