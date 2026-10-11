from datetime import datetime

from app.core.exceptions import ConflictError, NotFoundError
from app.models.plan import Plan
from app.ports.repositories import PlanRepositoryPort
from app.schemas.plan import CreatePlanRequest, PlanResponse, UpdatePlanRequest


class PlanService:
    """Casos de uso de administración de planes (precios/configuración)."""

    def __init__(self, plan_repo: PlanRepositoryPort) -> None:
        self._repo = plan_repo

    async def list_plans(self) -> list[PlanResponse]:
        plans = await self._repo.list_all()
        return [PlanResponse.from_domain(p) for p in plans]

    async def create_plan(self, request: CreatePlanRequest) -> PlanResponse:
        if await self._repo.find_by_code(request.code):
            raise ConflictError(f"El plan '{request.code.upper()}' ya existe")

        plan = Plan(
            code=request.code.upper(),
            name=request.name,
            amount_in_cents=request.amount_in_cents,
            currency=request.currency,
            duration_days=request.duration_days,
            is_active=request.is_active,
        )
        plan_id = await self._repo.upsert(plan)
        created = await self._repo.find_by_id(plan_id)
        return PlanResponse.from_domain(created)

    async def update_plan(self, plan_id: str, request: UpdatePlanRequest) -> PlanResponse:
        plan = await self._repo.find_by_id(plan_id)
        if not plan:
            raise NotFoundError("Plan")

        updates = request.model_dump(exclude_none=True)
        for field, value in updates.items():
            setattr(plan, field, value)
        plan.updated_at = datetime.utcnow()

        # upsert actualiza la fila existente (misma clave `code`).
        await self._repo.upsert(plan)
        updated = await self._repo.find_by_id(plan_id)
        return PlanResponse.from_domain(updated)

    async def delete_plan(self, plan_id: str) -> None:
        plan = await self._repo.find_by_id(plan_id)
        if not plan:
            raise NotFoundError("Plan")
        await self._repo.delete(plan_id)
