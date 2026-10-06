import structlog

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from pydantic import ValidationError

from payment.application.use_cases import RecordPaymentUseCase
from payment.domain import signing
from payment.domain.exceptions import InvalidSignatureError, StaleWebhookError
from payment.infrastructure.repositories import PaymentRepository
from payment.interfaces.schemas import PaymentWebhookIn

logger = structlog.get_logger(__name__)


@csrf_exempt
@require_POST
def payment_webhook(request):
    """Point d'entrée du webhook de paiement

    Le prestataire n'a pas de compte, sa signature tient lieu de jeton, d'où
    l'exemption CSRF
    """
    body = request.body

    try:
        signing.verify(
            secret=settings.PAYMENT_WEBHOOK_SECRET,
            timestamp=request.headers.get("X-Timestamp", ""),
            body=body,
            signature=request.headers.get("X-Signature", ""),
        )
    except StaleWebhookError:
        # 4xx et non 5xx : un rejeu est définitif, le faire réessayer
        # martèlerait le prestataire sans fin
        logger.warning("webhook_stale")
        return JsonResponse({"detail": "Webhook expire"}, status=400)
    except InvalidSignatureError:
        logger.warning("webhook_invalid_signature")
        return JsonResponse({"detail": "Signature invalide"}, status=401)

    try:
        payload = PaymentWebhookIn.model_validate_json(body)
    except ValidationError:
        return JsonResponse({"detail": "Corps de webhook invalide"}, status=400)

    payment, created = RecordPaymentUseCase(PaymentRepository()).execute(
        wallet_id=payload.wallet_id,
        amount=payload.amount,
        provider_ref=payload.provider_ref,
    )

    # Un doublon ne réempile pas : chaque redelivery grossirait la file
    if created:
        from payment.interfaces.tasks import process_payment

        process_payment.delay(str(payment.id), payload.status.value)

    logger.info("webhook_recorded", provider_ref=payload.provider_ref, created=created)

    return JsonResponse(
        {"received": True, "payment_id": str(payment.id), "duplicate": not created},
        status=200,
    )
