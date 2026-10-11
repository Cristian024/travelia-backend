from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.user import SubscriptionType


class ChangeSubscriptionRequest(BaseModel):
    subscription_type: SubscriptionType


class SubscriptionResponse(BaseModel):
    subscription_type: SubscriptionType
    is_premium: bool
    premium_since: Optional[datetime]
    monthly_planning_limit: Optional[int]
    monthly_plannings_used: int
    max_total_days: int
    max_destinations: int
