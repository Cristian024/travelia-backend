from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ChangeSubscriptionRequest(BaseModel):
    subscription_type: str


class SubscriptionResponse(BaseModel):
    subscription_type: str
    is_premium: bool
    premium_since: Optional[datetime]
    monthly_planning_limit: Optional[int]
    monthly_plannings_used: int
    max_total_days: int
    max_destinations: int
