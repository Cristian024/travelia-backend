import logging
from typing import Any, Optional

import httpx

from app.core.exceptions import PaymentGatewayError
from app.ports.external import GatewayTransactionResult, PaymentGatewayPort

logger = logging.getLogger(__name__)


class WompiApiClient(PaymentGatewayPort):
    """Adaptador del puerto PaymentGatewayPort sobre la API server-side de Wompi.

    Usa la llave privada (WOMPI_PRIVATE_KEY) para crear transacciones sin pasar
    por el Widget. Requiere un `payment_method` tokenizado/definido según Wompi.
    """

    def __init__(self, private_key: str, base_url: str) -> None:
        self._private_key = private_key
        self._base_url = base_url.rstrip("/")

    async def create_transaction(
        self,
        *,
        amount_in_cents: int,
        currency: str,
        customer_email: str,
        reference: str,
        payment_method: dict[str, Any],
        redirect_url: Optional[str] = None,
    ) -> GatewayTransactionResult:
        if not self._private_key:
            logger.error("Wompi: WOMPI_PRIVATE_KEY no está configurado")
            raise PaymentGatewayError("WOMPI_PRIVATE_KEY no está configurado")

        logger.info(
            "Wompi: creando transacción ref=%s amount=%s %s método=%s",
            reference, amount_in_cents, currency, payment_method.get("type"),
        )
        payload: dict[str, Any] = {
            "amount_in_cents": amount_in_cents,
            "currency": currency,
            "customer_email": customer_email,
            "reference": reference,
            "payment_method": payment_method,
        }
        if redirect_url:
            payload["redirect_url"] = redirect_url

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{self._base_url}/transactions",
                    headers={
                        "Authorization": f"Bearer {self._private_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
        except httpx.HTTPError as exc:
            logger.error("Wompi: error de red creando transacción ref=%s: %s", reference, exc)
            raise PaymentGatewayError(f"No se pudo contactar a Wompi: {exc}") from exc

        if response.status_code >= 400:
            detail = _extract_error(response)
            logger.error(
                "Wompi: transacción rechazada ref=%s status=%s: %s",
                reference, response.status_code, detail,
            )
            raise PaymentGatewayError(f"Wompi rechazó la transacción: {detail}")

        data = response.json().get("data", {})
        logger.info(
            "Wompi: transacción creada id=%s status=%s ref=%s",
            data.get("id"), data.get("status"), reference,
        )
        return GatewayTransactionResult(
            transaction_id=str(data.get("id", "")),
            status=str(data.get("status", "")),
            reference=str(data.get("reference", reference)),
            raw=data,
        )


def _extract_error(response: httpx.Response) -> str:
    try:
        body = response.json()
        error = body.get("error", body)
        messages = error.get("messages") if isinstance(error, dict) else None
        return str(messages or error)
    except Exception:
        return response.text
