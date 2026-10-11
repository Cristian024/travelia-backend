from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import get_payment_service
from app.schemas.wompi import WompiEvent, WompiWebhookAck
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/wompi", response_model=WompiWebhookAck, status_code=200)
async def wompi_webhook(
    payload: WompiEvent,
    service: Annotated[PaymentService, Depends(get_payment_service)],
) -> WompiWebhookAck:
    """
    Endpoint público (sin Bearer token) que Wompi invoca asíncronamente.
    La única barrera de seguridad es la validación del checksum en el servicio.
    Siempre responde 200 para que Wompi marque la notificación como entregada.
    """
    result = await service.process_payment_webhook(payload)
    return WompiWebhookAck(
        received=result.received,
        signature_valid=result.signature_valid,
        processed=result.processed,
        detail=result.detail,
    )
