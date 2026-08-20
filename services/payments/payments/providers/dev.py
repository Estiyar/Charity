import hashlib
import hmac
import json
import sys
import uuid
from decimal import Decimal, InvalidOperation

from django.conf import settings

from .exceptions import InvalidProviderSignature, PaymentConfigError, PaymentProviderError
from .types import ProviderResult, ProviderSession


def _decimal(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise PaymentProviderError("Некорректная сумма.") from exc


class DevPaymentAdapter:
    name = "dev"

    def __init__(self):
        if not self._allowed():
            raise PaymentConfigError("Dev-провайдер оплаты запрещён вне DEBUG/тестов.")
        self.secret = getattr(settings, "PAYMENT_DEV_SECRET", "") or "dev-payment-secret"

    def create_session(self, donation, urls):
        frontend = (getattr(settings, "PAYMENT_FRONTEND_URL", "") or "http://localhost:5173").rstrip("/")
        provider_payment_id = f"dev-{uuid.uuid4().hex[:16]}"
        redirect_url = f"{frontend}/payments/dev-checkout/{donation.id}"
        return ProviderSession(self.name, provider_payment_id, redirect_url)

    def parse_result(self, payload, headers=None, raw_body=b"", script_name="dev"):
        headers = headers or {}
        received = headers.get("X-Dev-Signature") or headers.get("x-dev-signature") or payload.get("signature")
        body = raw_body.decode("utf-8") if raw_body else json.dumps(payload, sort_keys=True, separators=(",", ":"))
        expected = hmac.new(self.secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
        if not received or not hmac.compare_digest(expected, str(received)):
            raise InvalidProviderSignature()
        status = str(payload.get("status") or "failed")
        payment_id = str(payload.get("provider_payment_id") or "")
        return ProviderResult(
            provider=self.name,
            provider_payment_id=payment_id,
            order_id=str(payload.get("order_id") or ""),
            amount=_decimal(payload.get("amount")),
            currency=str(payload.get("currency") or "KZT"),
            card_id=int(payload.get("card_id") or 0),
            status=status,
            failed_reason=str(payload.get("failed_reason") or ""),
            event_key=f"{payment_id}:{status}",
            raw=dict(payload),
        )

    def sign_payload(self, payload):
        body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        signature = hmac.new(self.secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
        return body, signature

    def success_response(self, script_name="dev"):
        return json.dumps({"status": "ok"}), "application/json"

    def _allowed(self):
        if getattr(settings, "DEBUG", False):
            return True
        return "test" in sys.argv
