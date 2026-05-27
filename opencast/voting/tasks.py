from celery import shared_task
from django.utils import timezone
from datetime import timedelta


@shared_task
def check_pending_transactions():
    """
    Periodically verify transactions that have been Pending for >30 minutes.
    Run this every 30 minutes via Celery Beat.
    """
    from .models import Transaction
    from .paystack import verify_transaction

    cutoff = timezone.now() - timedelta(minutes=30)
    pending = Transaction.objects.filter(
        status=Transaction.Status.PENDING,
        created_at__lte=cutoff,
    )

    for txn in pending:
        data = verify_transaction(txn.reference_str)
        if data:
            ps_status = data.get('status')
            if ps_status == 'success':
                _confirm_transaction(txn, data.get('reference', ''))
            elif ps_status in ('failed', 'abandoned'):
                txn.status = Transaction.Status.FAILED
                txn.save(update_fields=['status', 'updated_at'])
        else:
            # If still no response and it's been >24h, mark abandoned
            if txn.created_at <= timezone.now() - timedelta(hours=24):
                txn.status = Transaction.Status.ABANDONED
                txn.save(update_fields=['status', 'updated_at'])


def _confirm_transaction(txn, paystack_ref=''):
    """Shared logic: mark transaction success and create a Vote."""
    from .models import Transaction, Vote

    # Idempotency guard
    if txn.status == Transaction.Status.SUCCESS:
        return

    txn.status = Transaction.Status.SUCCESS
    if paystack_ref:
        txn.paystack_reference = paystack_ref
    txn.save(update_fields=['status', 'paystack_reference', 'updated_at'])

    # Create the Vote record
    Vote.objects.get_or_create(
        transaction=txn,
        defaults={
            'nominee': txn.nominee,
            'num_votes': txn.num_votes,
        }
    )

    # Atomically increment vote count
    txn.nominee.increment_votes(txn.num_votes)
