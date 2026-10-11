"""Esquemas del webhook de eventos de Wompi (pasarela de pagos).

Tipan estrictamente el JSON que Wompi envía a la URL de Eventos:

    {
      "event": "transaction.updated",
      "data": {
        "transaction": {
          "id": "1234-5678-...",
          "reference": "<user_id o planning_id>",
          "status": "APPROVED",
          "amount_in_cents": 500000,
          "currency": "COP",
          ...
        }
      },
      "signature": {
        "properties": ["transaction.id", "transaction.status", "transaction.amount_in_cents"],
        "checksum": "<sha256 hex>"
      },
      "timestamp": 1710000000
    }
"""
from typing import Optional

from pydantic import BaseModel, ConfigDict


class WompiTransaction(BaseModel):
    """Transacción notificada por Wompi."""

    model_config = ConfigDict(extra="allow")

    id: str
    reference: str
    status: str
    amount_in_cents: int
    currency: str
    customer_email: Optional[str] = None
    payment_method_type: Optional[str] = None
    finalized_at: Optional[str] = None


class WompiEventData(BaseModel):
    model_config = ConfigDict(extra="allow")

    transaction: WompiTransaction


class WompiSignature(BaseModel):
    """Contiene la lista de propiedades firmadas y el checksum a validar."""

    model_config = ConfigDict(extra="allow")

    properties: list[str]
    checksum: str


class WompiEvent(BaseModel):
    """Payload completo del evento enviado por Wompi."""

    model_config = ConfigDict(extra="allow")

    event: str
    data: WompiEventData
    signature: WompiSignature
    timestamp: int
    environment: Optional[str] = None
    sent_at: Optional[str] = None

    @property
    def transaction(self) -> WompiTransaction:
        return self.data.transaction


class WompiWebhookAck(BaseModel):
    """Acuse de recibo que el backend devuelve a Wompi (siempre HTTP 200)."""

    received: bool = True
    signature_valid: bool
    processed: bool
    detail: str
