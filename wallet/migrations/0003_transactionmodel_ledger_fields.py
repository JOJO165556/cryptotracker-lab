from django.db import migrations, models
import django.db.models.deletion


def migrate_wallet_reference(apps, schema_editor):
    transaction_model = apps.get_model("wallet", "TransactionModel")
    for transaction in transaction_model.objects.all():
        if transaction.type == "DEPOSIT":
            transaction.recipient_wallet_id = transaction.wallet_id
        else:
            transaction.sender_wallet_id = transaction.wallet_id
        transaction.save(update_fields=("sender_wallet", "recipient_wallet"))


def reverse_wallet_reference(apps, schema_editor):
    transaction_model = apps.get_model("wallet", "TransactionModel")
    for transaction in transaction_model.objects.all():
        transaction.wallet_id = (
            transaction.recipient_wallet_id or transaction.sender_wallet_id
        )
        transaction.save(update_fields=("wallet",))


class Migration(migrations.Migration):
    dependencies = [
        ("wallet", "0002_transactionmodel"),
    ]

    operations = [
        migrations.AddField(
            model_name="transactionmodel",
            name="failure_reason",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="transactionmodel",
            name="idempotency_key",
            field=models.CharField(blank=True, max_length=255, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="transactionmodel",
            name="recipient_wallet",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="received_transactions",
                to="wallet.walletmodel",
            ),
        ),
        migrations.AddField(
            model_name="transactionmodel",
            name="sender_wallet",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="sent_transactions",
                to="wallet.walletmodel",
            ),
        ),
        migrations.RunPython(migrate_wallet_reference, reverse_wallet_reference),
        migrations.RemoveField(
            model_name="transactionmodel",
            name="wallet",
        ),
    ]
