import hashlib
import hmac
import requests
from django.conf import settings

PAYSTACK_BASE = "https://api.paystack.co"


def _headers():
    return {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }


def initialize_transaction(email, amount_ghs, reference, callback_url, metadata=None):
    """
    Initialize a Paystack transaction.
    amount_ghs: Decimal — will be converted to pesewas (×100).
    Returns the authorization_url to redirect the user to, or None on error.
    """
    amount_pesewas = int(amount_ghs * 100)
    payload = {
        "email": email,
        "amount": amount_pesewas,
        "reference": str(reference),
        "callback_url": callback_url,
        "currency": "GHS",
        "metadata": metadata or {},
    }
    try:
        resp = requests.post(
            f"{PAYSTACK_BASE}/transaction/initialize",
            json=payload,
            headers=_headers(),
            timeout=10,
        )
        data = resp.json()
        if data.get("status"):
            return data["data"]["authorization_url"]
    except requests.RequestException:
        pass
    return None


def verify_transaction(reference):
    """
    Verify a transaction by reference.
    Returns the full data dict from Paystack, or None on failure.
    """
    try:
        resp = requests.get(
            f"{PAYSTACK_BASE}/transaction/verify/{reference}",
            headers=_headers(),
            timeout=10,
        )
        data = resp.json()
        if data.get("status"):
            return data["data"]
    except requests.RequestException:
        pass
    return None


def verify_webhook_signature(payload_bytes, signature_header):
    """
    Validate that a webhook POST actually came from Paystack.
    payload_bytes: raw request body (bytes)
    signature_header: value of X-Paystack-Signature header
    """
    secret = settings.PAYSTACK_SECRET_KEY.encode('utf-8')
    computed = hmac.new(secret, payload_bytes, hashlib.sha512).hexdigest()
    return hmac.compare_digest(computed, signature_header)
