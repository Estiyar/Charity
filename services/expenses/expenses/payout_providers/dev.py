import hashlib
import hmac
import json
import sys
import uuid
from decimal import Decimal, InvalidOperation

from django.conf import settings

from .exceptions import InvalidPayoutSignature, PayoutConfigError, PayoutProviderError
from .types import ProviderPayout, ProviderPayoutResult


def _decimal(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise PayoutProviderError("Некорректная сумма.") from exc


class DevPayoutAdapter:
    name = "dev"

    def __init__(self):
        if not self._allowed():
            raise PayoutConfigError("Dev-провайдер выплат запрещён вне DEBUG/тестов.")
        self.secret = getattr(settings, "PAYOUT_DEV_SECRET", "") or "dev-payout-secret"

    def create_payout(self, payout, iban=""):
        return ProviderPayout(self.name, f"dev-payout-{uuid.uuid4().hex[:16]}")

    def parse_result(self, payload, headers=None, raw_body=b""):
        headers = headers or {}
        received = headers.get("X-Dev-Signature") or headers.get("x-dev-signature") or payload.get("signature")
        body = raw_body.decode("utf-8") if raw_body else json.dumps(payload, sort_keys=True, separators=(",", ":"))
        expected = hmac.new(self.secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
        if not received or not hmac.compare_digest(expected, str(received)):
            raise InvalidPayoutSignature()
        status = str(payload.get("status") or "failed")
        payout_id = str(payload.get("payout_id") or "")
        provider_id = str(payload.get("provider_payout_id") or "")
        return ProviderPayoutResult(
            provider=self.name,
            provider_payout_id=provider_id,
            payout_id=payout_id,
            amount=_decimal(payload.get("amount")),
            currency=str(payload.get("currency") or "KZT"),
            card_id=int(payload.get("card_id") or 0),
            status=status,
            failed_reason=str(payload.get("failed_reason") or ""),
            event_key=f"{provider_id}:{status}",
        )

    def sign_payload(self, payload):
        body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        signature = hmac.new(self.secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
        return body, signature

    def _allowed(self):
        if getattr(settings, "DEBUG", False):
            return True
        return "test" in sys.argv
