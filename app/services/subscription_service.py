import logging
from datetime import datetime

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.plan import PlanCode
from app.ports.repositories import (
    PlanRepositoryPort,
    PlanningRepositoryPort,
    UserRepositoryPort,
)
from app.schemas.plan import PlanResponse
from app.schemas.subscription import SubscriptionResponse
from app.services.subscription_policy import SubscriptionPolicy

logger = logging.getLogger(__name__)


class SubscriptionService:
    def __init__(
        self,
        user_repo: UserRepositoryPort,
        planning_repo: PlanningRepositoryPort,
        plan_repo: PlanRepositoryPort,
        policy: SubscriptionPolicy | None = None,
    ) -> None:
        self._user_repo = user_repo
        self._planning_repo = planning_repo
        self._plan_repo = plan_repo
        self._policy = policy or SubscriptionPolicy()

    async def list_available_plans(self) -> list[PlanResponse]:
        """Suscripciones disponibles (planes activos) leídas de la base de datos."""
        plans = await self._plan_repo.list_all()
        return [PlanResponse.from_domain(p) for p in plans if p.is_active]

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

    async def change_plan(self, user_id: str, subscription_type: str) -> SubscriptionResponse:
        user = await self._user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError("User")

        code = (subscription_type or "").upper()
        plan = await self._plan_repo.find_by_code(code)
        if not plan or not plan.is_active:
            raise BusinessRuleError(f"El plan '{code}' no está disponible")

        updates: dict = {
            "subscription_type": code,
            "premium_since": datetime.utcnow() if code == PlanCode.PREMIUM else None,
            "updated_at": datetime.utcnow(),
        }
        await self._user_repo.update_by_id(user_id, updates)
        logger.info("Suscripción de usuario %s cambiada a %s", user_id, code)
        return await self.get_status(user_id)


def _start_of_month() -> datetime:
    now = datetime.utcnow()
    return datetime(now.year, now.month, 1)
