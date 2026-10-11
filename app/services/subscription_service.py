import logging
from datetime import datetime

from app.core.exceptions import NotFoundError
from app.models.user import SubscriptionType
from app.ports.repositories import PlanningRepositoryPort, UserRepositoryPort
from app.schemas.subscription import SubscriptionResponse
from app.services.subscription_policy import SubscriptionPolicy

logger = logging.getLogger(__name__)


class SubscriptionService:
    def __init__(
        self,
        user_repo: UserRepositoryPort,
        planning_repo: PlanningRepositoryPort,
        policy: SubscriptionPolicy | None = None,
    ) -> None:
        self._user_repo = user_repo
        self._planning_repo = planning_repo
        self._policy = policy or SubscriptionPolicy()

    async def get_status(self, user_id: str) -> SubscriptionResponse:
        user = await self._user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError("User")

        limits = self._policy.limits_for(user.subscription_type)
        used = await self._planning_repo.count_by_user_since(user_id, _start_of_month())

        return SubscriptionResponse(
            subscription_type=user.subscription_type,
            is_premium=user.is_premium,
            premium_since=user.premium_since,
            monthly_planning_limit=limits.monthly_planning_limit,
            monthly_plannings_used=used,
            max_total_days=limits.max_total_days,
            max_destinations=limits.max_destinations,
        )

    async def change_plan(
        self, user_id: str, subscription_type: SubscriptionType
    ) -> SubscriptionResponse:
        user = await self._user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError("User")

        updates: dict = {
            "subscription_type": subscription_type.value,
            "premium_since": datetime.utcnow() if subscription_type == SubscriptionType.premium else None,
            "updated_at": datetime.utcnow(),
        }
        await self._user_repo.update_by_id(user_id, updates)
        logger.info("Suscripción de usuario %s cambiada a %s", user_id, subscription_type.value)
        return await self.get_status(user_id)


def _start_of_month() -> datetime:
    now = datetime.utcnow()
    return datetime(now.year, now.month, 1)
