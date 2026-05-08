import json
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from django.contrib import messages
from django.utils import timezone

from .models import Event, Category, Nominee, Transaction, Vote
from .forms import VoteForm
from .paystack import initialize_transaction, verify_transaction, verify_webhook_signature
from .tasks import _confirm_transaction

logger = logging.getLogger(__name__)


# ─── Public Pages ─────────────────────────────────────────────────────────────

def home(request):
    events = Event.objects.filter(is_active=True).order_by('-start_date')
    now = timezone.now()
    context = {
        'active_events': [e for e in events if e.is_open],
        'upcoming_events': [e for e in events if e.start_date > now],
        'past_events': Event.objects.filter(
            is_active=True, end_date__lt=now
        ).order_by('-end_date')[:6],
    }
    return render(request, 'voting/home.html', context)


def event_detail(request, slug):
    event = get_object_or_404(Event, slug=slug, is_active=True)
    categories = event.categories.prefetch_related('nominees').all()
    context = {
        'event': event,
        'categories': categories,
    }
    return render(request, 'voting/event_detail.html', context)


def category_detail(request, slug, category_id):
    event = get_object_or_404(Event, slug=slug, is_active=True)
    category = get_object_or_404(Category, pk=category_id, event=event)
    nominees = category.nominees.filter(is_active=True)
    context = {
        'event': event,
        'category': category,
        'nominees': nominees,
    }
    return render(request, 'voting/category_detail.html', context)


def nominee_detail(request, slug, nominee_id):
    event = get_object_or_404(Event, slug=slug, is_active=True)
    nominee = get_object_or_404(Nominee, pk=nominee_id, category__event=event, is_active=True)
    form = VoteForm()
    context = {
        'event': event,
        'nominee': nominee,
        'form': form,
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
    }
    return render(request, 'voting/nominee_detail.html', context)


# ─── Voting & Payment ─────────────────────────────────────────────────────────

def initiate_vote(request, slug, nominee_id):
    """User submits the vote form → create a pending transaction → redirect to Paystack."""
    event = get_object_or_404(Event, slug=slug, is_active=True)
    nominee = get_object_or_404(Nominee, pk=nominee_id, category__event=event, is_active=True)

    if not event.is_open:
        messages.error(request, "Voting for this event is not currently open.")
        return redirect('event_detail', slug=slug)

    form = VoteForm(request.POST)
    if not form.is_valid():
        context = {
            'event': event,
            'nominee': nominee,
            'form': form,
            'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
        }
        return render(request, 'voting/nominee_detail.html', context)

    num_votes = form.cleaned_data['num_votes']
    amount = event.get_price_for_votes(num_votes)

    # Create pending transaction
    txn = Transaction.objects.create(
        nominee=nominee,
        voter_email=settings.NOTIFICATION_EMAIL,
        num_votes=num_votes,
        amount=amount,
        price_per_vote_snapshot=event.price_per_vote,
        ip_address=get_client_ip(request),
    )

    callback_url = request.build_absolute_uri(f'/vote/callback/{txn.reference_str}/')
    auth_url = initialize_transaction(
        email=settings.NOTIFICATION_EMAIL,
        amount_ghs=txn.amount,
        reference=txn.reference_str,
        callback_url=callback_url,
        metadata={
            'nominee_name': nominee.name,
            'event_name': event.name,
            'num_votes': num_votes,
            'transaction_id': str(txn.pk),
        }
    )

    if not auth_url:
        txn.status = Transaction.Status.FAILED
        txn.save(update_fields=['status'])
        messages.error(request, "Could not connect to payment gateway. Please try again.")
        return redirect('nominee_detail', slug=slug, nominee_id=nominee_id)

    return redirect(auth_url)


def payment_callback(request, reference):
    """Paystack redirects user here after payment attempt."""
    txn = get_object_or_404(Transaction, reference=reference)

    # Verify directly with Paystack
    data = verify_transaction(str(reference))
    if data and data.get('status') == 'success':
        _confirm_transaction(txn, data.get('reference', ''))
        messages.success(request, f"🎉 Your {txn.num_votes} vote(s) for {txn.nominee.name} have been recorded!")
        return render(request, 'voting/payment_success.html', {'transaction': txn})
    else:
        txn.status = Transaction.Status.FAILED
        txn.save(update_fields=['status', 'updated_at'])
        messages.error(request, "Payment was not successful. Please try again.")
        return render(request, 'voting/payment_failed.html', {'transaction': txn})


@csrf_exempt
@require_POST
def paystack_webhook(request):
    """
    Paystack sends payment events here.
    This is the backup for cases where the user closes the browser before callback.
    """
    signature = request.headers.get('X-Paystack-Signature', '')
    if not verify_webhook_signature(request.body, signature):
        logger.warning("Invalid Paystack webhook signature received.")
        return HttpResponse(status=400)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    event_type = payload.get('event')
    if event_type == 'charge.success':
        data = payload.get('data', {})
        reference = data.get('reference')
        try:
            txn = Transaction.objects.get(reference=reference)
            _confirm_transaction(txn, reference)
        except Transaction.DoesNotExist:
            logger.error(f"Webhook: Transaction not found for reference {reference}")

    return HttpResponse(status=200)


# ─── AJAX: Get price for N votes ──────────────────────────────────────────────

def get_vote_price(request, slug):
    """AJAX endpoint: returns price for a given number of votes."""
    event = get_object_or_404(Event, slug=slug)
    try:
        num_votes = int(request.GET.get('votes', 1))
    except (ValueError, TypeError):
        num_votes = 1
    price = event.get_price_for_votes(num_votes)
    return JsonResponse({
        'price': float(price),
        'num_votes': num_votes,
        'currency': 'GHS',
    })


# ─── Results ──────────────────────────────────────────────────────────────────

def event_results(request, slug):
    event = get_object_or_404(Event, slug=slug, is_active=True)
    if not event.show_results and not request.user.is_staff:
        messages.info(request, "Results for this event are not yet public.")
        return redirect('event_detail', slug=slug)

    categories = event.categories.prefetch_related('nominees').all()
    context = {'event': event, 'categories': categories}
    return render(request, 'voting/results.html', context)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')
