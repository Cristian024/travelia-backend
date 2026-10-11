from dataclasses import dataclass
from typing import Optional

from app.models.plan import PlanCode


@dataclass(frozen=True)
class PlanLimits:
    subscription_type: str
    monthly_planning_limit: Optional[int]
    max_total_days: int
    max_question_depth: int
    max_destinations: int
    questions_per_round: int

    @property
    def is_premium(self) -> bool:
        return self.subscription_type == PlanCode.PREMIUM


class SubscriptionPolicy:
    """
    Reglas de negocio de los dos niveles (FREE / PREMIUM).

    La LISTA de suscripciones disponibles vive en la tabla `plans`; aquí solo
    se definen los límites de negocio de los niveles conocidos. Un código de
    plan desconocido se trata como FREE.
    """

    # --- Plan FREE ---
    FREE_MONTHLY_PLANNINGS = 3
    FREE_MAX_TOTAL_DAYS = 4
    FREE_MAX_QUESTION_DEPTH = 1
    FREE_MAX_DESTINATIONS = 3
    FREE_QUESTIONS_PER_ROUND = 3

    # --- Plan PREMIUM ---
    PREMIUM_MAX_TOTAL_DAYS = 30
    PREMIUM_MAX_QUESTION_DEPTH = 5
    PREMIUM_MAX_DESTINATIONS = 8
    PREMIUM_QUESTIONS_PER_ROUND = 5

    def limits_for(self, subscription_type: str) -> PlanLimits:
        if subscription_type == PlanCode.PREMIUM:
            return PlanLimits(
                subscription_type=subscription_type,
                monthly_planning_limit=None,
                max_total_days=self.PREMIUM_MAX_TOTAL_DAYS,
                max_question_depth=self.PREMIUM_MAX_QUESTION_DEPTH,
                max_destinations=self.PREMIUM_MAX_DESTINATIONS,
                questions_per_round=self.PREMIUM_QUESTIONS_PER_ROUND,
            )
        return PlanLimits(
            subscription_type=subscription_type,
            monthly_planning_limit=self.FREE_MONTHLY_PLANNINGS,
            max_total_days=self.FREE_MAX_TOTAL_DAYS,
            max_question_depth=self.FREE_MAX_QUESTION_DEPTH,
            max_destinations=self.FREE_MAX_DESTINATIONS,
            questions_per_round=self.FREE_QUESTIONS_PER_ROUND,
        )
