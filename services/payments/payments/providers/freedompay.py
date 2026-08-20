import hashlib
import hmac
import secrets
import xml.etree.ElementTree as ElementTree
from decimal import Decimal, InvalidOperation
from xml.etree.ElementTree import ParseError

import httpx
from django.conf import settings

from .exceptions import InvalidProviderSignature, PaymentConfigError, PaymentProviderError
from .types import ProviderResult, ProviderSession


SCRIPT_INIT = "init_payment.php"


def _decimal(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise PaymentProviderError("Некорректная сумма в ответе провайдера.") from exc


def make_freedompay_signature(script_name, params, secret):
    values = []
    for key in sorted(params):
        if key == "pg_sig" or params[key] is None:
            continue
        values.append(str(params[key]))
    raw = ";".join([script_name, *values, secret])
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def signature_matches(script_name, params, secret, received):
    expected = make_freedompay_signature(script_name, params, secret)
    return hmac.compare_digest(expected, str(received or ""))


class FreedomPayAdapter:
    name = "freedompay"

    def __init__(self):
        self.merchant_id = getattr(settings, "FREEDOMPAY_MERCHANT_ID", "") or ""
        self.secret = getattr(settings, "FREEDOMPAY_SECRET", "") or ""
        self.api_url = (getattr(settings, "FREEDOMPAY_API_URL", "") or "https://api.freedompay.kz").rstrip("/")
        self.testing_mode = getattr(settings, "FREEDOMPAY_TESTING_MODE", True)

    def _require_credentials(self):
        if not self.merchant_id or not self.secret:
            raise PaymentConfigError(
                "Freedom Pay не настроен: задайте FREEDOMPAY_MERCHANT_ID и FREEDOMPAY_SECRET "
                "(официальный sandbox/stage мерчанта)."
            )

    def create_session(self, donation, urls):
        self._require_credentials()
        params = {
            "pg_merchant_id": self.merchant_id,
            "pg_order_id": str(donation.id),
            "pg_amount": str(donation.amount),
            "pg_currency": donation.currency,
            "pg_description": f"Пожертвование на сбор {donation.card_id}",
            "pg_salt": secrets.token_hex(16),
            "pg_result_url": urls["result_url"],
            "pg_success_url": urls["success_url"],
            "pg_failure_url": urls["failure_url"],
            "pg_user_contact_email": donation.email or "",
            "pg_user_phone": donation.phone or "",
            "pg_param1": str(donation.card_id),
        }
        if self.testing_mode:
            params["pg_testing_mode"] = "1"
        params["pg_sig"] = make_freedompay_signature(SCRIPT_INIT, params, self.secret)
        try:
            response = httpx.post(
                f"{self.api_url}/init_payment.php",
                data=params,
                timeout=15.0,
            )
        except httpx.HTTPError as exc:
            raise PaymentProviderError("Freedom Pay недоступен.") from exc
        payload = self._parse_xml(response.text)
        if payload.get("pg_status") != "ok":
            raise PaymentProviderError(payload.get("pg_error_description") or "Freedom Pay отклонил сессию.")
        payment_id = payload.get("pg_payment_id") or ""
        redirect_url = payload.get("pg_redirect_url") or ""
        if not payment_id or not redirect_url:
            raise PaymentProviderError("Freedom Pay не вернул данные платёжной сессии.")
        return ProviderSession(self.name, str(payment_id), redirect_url)

    def parse_result(self, payload, headers=None, raw_body=b"", script_name="freedompay"):
        self._require_credentials()
        params = {key: payload[key] for key in payload if str(key).startswith("pg_")}
        if not signature_matches(script_name, params, self.secret, params.get("pg_sig")):
            raise InvalidProviderSignature()
        result_flag = str(params.get("pg_result", ""))
        if result_flag == "1":
            status = "success"
        elif result_flag == "0":
            status = "failed"
        else:
            status = "failed"
        order_id = str(params.get("pg_order_id") or "")
        payment_id = str(params.get("pg_payment_id") or "")
        card_id = int(params.get("pg_param1") or 0)
        return ProviderResult(
            provider=self.name,
            provider_payment_id=payment_id,
            order_id=order_id,
            amount=_decimal(params.get("pg_amount")),
            currency=str(params.get("pg_currency") or "KZT"),
            card_id=card_id,
            status=status,
            failed_reason=str(params.get("pg_failure_description") or ""),
            event_key=f"{payment_id}:{status}",
            raw=params,
        )

    def success_response(self, script_name="freedompay"):
        self._require_credentials()
        params = {
            "pg_status": "ok",
            "pg_description": "Accepted",
            "pg_salt": secrets.token_hex(8),
        }
        params["pg_sig"] = make_freedompay_signature(script_name, params, self.secret)
        xml = "".join(
            [
                '<?xml version="1.0" encoding="utf-8"?>',
                "<response>",
                f"<pg_status>{params['pg_status']}</pg_status>",
                f"<pg_description>{params['pg_description']}</pg_description>",
                f"<pg_salt>{params['pg_salt']}</pg_salt>",
                f"<pg_sig>{params['pg_sig']}</pg_sig>",
                "</response>",
            ]
        )
        return xml, "application/xml"

    def _parse_xml(self, text):
        try:
            root = ElementTree.fromstring(text)
        except ParseError as exc:
            raise PaymentProviderError("Freedom Pay вернул некорректный XML.") from exc
        return {child.tag: (child.text or "") for child in root}
