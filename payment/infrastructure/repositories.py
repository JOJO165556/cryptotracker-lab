from uuid import UUID

from django.db import IntegrityError
from django.db.models import Q

from payment.domain.entities import Payment
from payment.domain.value_objects import PaymentStatus
from payment.models import PaymentModel


class DuplicateProviderRefError(Exception):
    """Levée quand un provider_ref existe déjà en base, le webhook est un doublon"""


def _to_entity(model: PaymentModel) -> Payment:
    """Traduit une ligne de la table payments en entité domain"""
    return Payment(
        id=model.id,
        wallet_id=model.wallet_id,
        amount=model.amount,
        provider_ref=model.provider_ref,
        status=PaymentStatus(model.status),
        created_at=model.created_at,
    )


def _to_model(payment: Payment) -> dict:
    """Champs d'insertion d'un paiement, utilisés par create()"""
    return {
        "id": payment.id,
        "wallet_id": payment.wallet_id,
        "amount": payment.amount,
        "provider_ref": payment.provider_ref,
        "status": payment.status.value,
        "created_at": payment.created_at,
    }


class PaymentRepository:
    """Accès à la table payments"""

    def get_by_id(self, payment_id: UUID) -> Payment | None:
        """Retourne un paiement par son id, None s'il n'existe pas"""
        model = PaymentModel.objects.filter(id=payment_id).first()
        return _to_entity(model) if model else None

    def get_by_provider_ref(self, provider_ref: str) -> Payment | None:
        """Retourne un paiement par sa référence prestataire, None s'il n'existe pas"""
        model = PaymentModel.objects.filter(provider_ref=provider_ref).first()
        return _to_entity(model) if model else None

    def create(self, payment: Payment) -> Payment:
        """Crée un paiement, lève DuplicateProviderRefError si la référence est connue"""
        if PaymentModel.objects.filter(provider_ref=payment.provider_ref).exists():
            raise DuplicateProviderRefError(payment.provider_ref)
        try:
            PaymentModel.objects.create(**_to_model(payment))
        except IntegrityError as exc:
            raise DuplicateProviderRefError(payment.provider_ref) from exc
        return payment

    def save(self, payment: Payment) -> None:
        """Enregistre ou met à jour un paiement"""
        PaymentModel.objects.filter(id=payment.id).update(
            amount=payment.amount,
            status=payment.status.value,
        )

    def transition_status(
        self, payment: Payment, expected_status: PaymentStatus
    ) -> bool:
        """Compare-and-set du statut, Returns True si la transition a eu lieu

        Le WHERE porte sur le statut attendu, donc deux tâches concurrentes ne
        peuvent pas confirmer deux fois le même paiement
        """
        updated = PaymentModel.objects.filter(
            Q(id=payment.id) & Q(status=expected_status.value)
        ).update(status=payment.status.value, amount=payment.amount)
        return updated > 0
