"""Caso de uso de pagos (Wompi).

No conoce HTTP ni FastAPI:
  - Widget: crea intento de pago + firma de integridad.
  - Server-side: crea la transacción contra la API de Wompi (llave privada).
  - Webhook: valida eventos y activa PREMIUM.
Depende solo de puertos y de `WompiParams`. El PRECIO vive en la tabla `plans`.
"""
import hashlib
import hmac
import logging
import uuid
from dataclasses import dataclass
from typing import Any

from app.core.exceptions import BusinessRuleError, ForbiddenError, NotFoundError, PaymentGatewayError
from app.models.payment import Payment, PaymentStatus
from app.models.plan import PlanCode
from app.ports.external import PaymentGatewayPort
from app.ports.repositories import (
    PaymentRepositoryPort,
    PlanRepositoryPort,
    UserRepositoryPort,
)
from app.schemas.payment import (
    CheckoutResponse,
    CreateTransactionRequest,
    PaginatedPaymentsResponse,
    PaymentResponse,
    TransactionResponse,
)
from app.schemas.wompi import WompiEvent

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WompiParams:
    """Parámetros de la pasarela (sin precio: el precio viene del plan en BD)."""

    events_secret: str
    integrity_secret: str
    public_key: str
    redirect_url: str


@dataclass
class PaymentWebhookResult:
    received: bool = True
    signature_valid: bool = False
    processed: bool = False
    detail: str = ""


class PaymentService:
    APPROVED_STATUS = "APPROVED"

    def __init__(
        self,
        user_repo: UserRepositoryPort,
        payment_repo: PaymentRepositoryPort,
        plan_repo: PlanRepositoryPort,
        gateway: PaymentGatewayPort,
        params: WompiParams,
    ) -> None:
        self._user_repo = user_repo
        self._payment_repo = payment_repo
        self._plan_repo = plan_repo
        self._gateway = gateway
        self._params = params

    # ------------------------------------------------------------------
    # Plan (precio desde BD)
    # ------------------------------------------------------------------
    async def _get_premium_plan(self):
        plan = await self._plan_repo.find_by_code(PlanCode.PREMIUM)
        if not plan or not plan.is_active:
            raise BusinessRuleError("El plan Premium no está disponible")
        return plan

    # ------------------------------------------------------------------
    # Checkout con Widget: intento de pago + firma de integridad
    # ------------------------------------------------------------------
    def compute_integrity_signature(
        self, reference: str, amount_in_cents: int, currency: str
    ) -> str:
        """SHA256(reference + amount + currency + WOMPI_INTEGRITY_SECRET)."""
        if not self._params.integrity_secret:
            raise BusinessRuleError("WOMPI_INTEGRITY_SECRET no está configurado")
        base = f"{reference}{amount_in_cents}{currency}{self._params.integrity_secret}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    async def create_checkout(self, user_id: str) -> CheckoutResponse:
        user = await self._user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError("User")
        plan = await self._get_premium_plan()

        reference = str(uuid.uuid4())
        payment = Payment(
            user_id=user_id,
            reference=reference,
            amount_in_cents=plan.amount_in_cents,
            currency=plan.currency,
        )
        payment_id = await self._payment_repo.insert(payment)

        signature = self.compute_integrity_signature(
            reference, plan.amount_in_cents, plan.currency
        )
        return CheckoutResponse(
            payment_id=payment_id,
            reference=reference,
            amount_in_cents=plan.amount_in_cents,
            currency=plan.currency,
            public_key=self._params.public_key,
            signature_integrity=signature,
            redirect_url=self._params.redirect_url,
        )

    # ------------------------------------------------------------------
    # Server-side: crea la transacción contra la API de Wompi
    # ------------------------------------------------------------------
    async def create_transaction(
        self, user_id: str, request: CreateTransactionRequest
    ) -> TransactionResponse:
        user = await self._user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError("User")
        plan = await self._get_premium_plan()

        reference = str(uuid.uuid4())
        payment = Payment(
            user_id=user_id,
            reference=reference,
            amount_in_cents=plan.amount_in_cents,
            currency=plan.currency,
        )
        payment_id = await self._payment_repo.insert(payment)

        try:
            result = await self._gateway.create_transaction(
                amount_in_cents=plan.amount_in_cents,
                currency=plan.currency,
                customer_email=request.customer_email or user.email,
                reference=reference,
                payment_method=request.payment_method,
                redirect_url=self._params.redirect_url,
            )
        except PaymentGatewayError:
            await self._payment_repo.update_status(reference, PaymentStatus.error)
            raise

        status = _map_status(result.status)
        await self._payment_repo.update_status(reference, status, result.transaction_id)
        if status == PaymentStatus.approved:
            await self._user_repo.activate_premium(user_id)

        return TransactionResponse(
            payment_id=payment_id,
            reference=reference,
            transaction_id=result.transaction_id or None,
            status=status,
            amount_in_cents=plan.amount_in_cents,
            currency=plan.currency,
        )

    async def get_payment(self, user_id: str, reference: str) -> PaymentResponse:
        payment = await self._payment_repo.find_by_reference(reference)
        if not payment:
            raise NotFoundError("Payment")
        if payment.user_id != user_id:
            raise ForbiddenError()
        return PaymentResponse.from_domain(payment)

    # --- Administración ---

    async def list_payments(self, page: int, page_size: int) -> PaginatedPaymentsResponse:
        offset = (page - 1) * page_size
        payments = await self._payment_repo.list_all(limit=page_size, offset=offset)
        total = await self._payment_repo.count_all()
        total_pages = (total + page_size - 1) // page_size if page_size else 0
        return PaginatedPaymentsResponse(
            items=[PaymentResponse.from_domain(p) for p in payments],
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )

    async def get_payment_admin(self, reference: str) -> PaymentResponse:
        payment = await self._payment_repo.find_by_reference(reference)
        if not payment:
            raise NotFoundError("Payment")
        return PaymentResponse.from_domain(payment)

    # ------------------------------------------------------------------
    # Firma de eventos (checksum SHA-256)
    # ------------------------------------------------------------------
    def compute_checksum(self, event: WompiEvent) -> str:
        base = self._build_signature_base(event)
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    def _build_signature_base(self, event: WompiEvent) -> str:
        data = event.data.model_dump()
        concatenated = "".join(
            self._resolve_property(data, prop) for prop in event.signature.properties
        )
        return f"{concatenated}{event.timestamp}{self._params.events_secret}"

    @staticmethod
    def _resolve_property(data: dict[str, Any], path: str) -> str:
        current: Any = data
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                raise BusinessRuleError(f"Propiedad de firma inválida: '{path}'")
            current = current[part]
        if isinstance(current, bool):
            return "true" if current else "false"
        return str(current)

    def verify_signature(self, event: WompiEvent) -> bool:
        if not self._params.events_secret:
            raise BusinessRuleError("WOMPI_EVENTS_SECRET no está configurado")
        expected = self.compute_checksum(event)
        provided = (event.signature.checksum or "").strip().lower()
        return hmac.compare_digest(expected, provided)

    # ------------------------------------------------------------------
    # Webhook
    # ------------------------------------------------------------------
    async def process_payment_webhook(self, event: WompiEvent) -> PaymentWebhookResult:
        try:
            signature_valid = self.verify_signature(event)
        except BusinessRuleError as exc:
            logger.error("Wompi webhook: %s", exc)
            return PaymentWebhookResult(signature_valid=False, detail=str(exc))

        if not signature_valid:
            logger.warning("Wompi webhook: firma inválida (ref=%s)", event.transaction.reference)
            return PaymentWebhookResult(signature_valid=False, detail="invalid_signature")

        transaction = event.transaction
        status = (transaction.status or "").upper()
        reference = transaction.reference

        payment = await self._payment_repo.find_by_reference(reference)
        user_id = payment.user_id if payment else reference

        if status != self.APPROVED_STATUS:
            if payment:
                await self._payment_repo.update_status(reference, _map_status(status))
            return PaymentWebhookResult(signature_valid=True, detail=f"status:{transaction.status}")

        user = await self._user_repo.find_by_id(user_id)
        if not user:
            logger.warning("Wompi webhook: usuario no encontrado (ref=%s)", reference)
            return PaymentWebhookResult(signature_valid=True, detail="user_not_found")

        await self._user_repo.activate_premium(user_id)
        if payment:
            await self._payment_repo.update_status(
                reference, PaymentStatus.approved, transaction.id
            )
        logger.info("Wompi webhook: usuario %s actualizado a PREMIUM", user_id)
        return PaymentWebhookResult(
            signature_valid=True, processed=True, detail="premium_activated"
        )


def _map_status(status: str) -> PaymentStatus:
    try:
        return PaymentStatus((status or "").upper())
    except ValueError:
        return PaymentStatus.error
