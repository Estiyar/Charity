import json
import sys
from datetime import datetime, timezone

import httpx
from django.conf import settings

from .cms import parse_and_verify_cms, verify_rsa_or_ecdsa
from .exceptions import EcpConfigError, EcpVerificationError
from .extract import extract_certificate_fields, issuer_is_nca


def _utcnow():
    return datetime.now(timezone.utc)


def _check_validity_window(certificate):
    now = _utcnow()
    if certificate.not_valid_before_utc > now:
        raise EcpVerificationError("Срок действия сертификата ещё не начался.", code="not_yet_valid")
    if certificate.not_valid_after_utc < now:
        raise EcpVerificationError("Срок действия сертификата истёк.", code="expired")


def _check_issuer(certificate):
    if not getattr(settings, "ECP_REQUIRE_NCA_ISSUER", True):
        return
    if not issuer_is_nca(certificate):
        raise EcpVerificationError("Сертификат выдан не НУЦ РК.", code="untrusted_issuer")


def _check_revocation_via_verifier(cms, challenge, verifier_payload):
    revocation = verifier_payload.get("revocation") or verifier_payload.get("ocsp") or {}
    if revocation.get("revoked") or verifier_payload.get("revoked"):
        raise EcpVerificationError("Сертификат отозван.", code="revoked")


class NcaLayerVerifierAdapter:
    name = "ncalayer"

    def verify(self, challenge, cms):
        parsed = parse_and_verify_cms(cms, challenge)
        certificate = parsed["certificate"]
        _check_validity_window(certificate)
        _check_issuer(certificate)
        if parsed["gost"]:
            self._verify_gost(parsed, challenge)
        else:
            verify_rsa_or_ecdsa(
                certificate,
                parsed["signature"],
                parsed["payload"],
                parsed["digest"],
            )
        fields = extract_certificate_fields(certificate)
        fields["adapter"] = self.name
        fields["cms_hash"] = parsed["cms_hash"]
        fields["revocation_checked"] = False
        return fields

    def _verify_gost(self, parsed, challenge):
        verifier_url = getattr(settings, "ECP_VERIFIER_URL", "") or ""
        if not verifier_url:
            raise EcpConfigError(
                "GOST-подпись НУЦ нельзя проверить без ECP_VERIFIER_URL "
                "(nca-node / KalkanCrypt или официальный совместимый сервис)."
            )
        import base64

        cms_b64 = base64.b64encode(parsed["cms_der"]).decode("ascii")
        data_b64 = base64.b64encode(challenge).decode("ascii")
        url = verifier_url.rstrip("/")
        endpoint = url if url.endswith("/cms/verify") else f"{url}/cms/verify"
        try:
            response = httpx.post(
                endpoint,
                json={"cms": cms_b64, "data": data_b64, "revocation": "ocsp"},
                timeout=10.0,
            )
        except httpx.HTTPError as exc:
            raise EcpVerificationError("Сервис проверки ЭЦП недоступен.", code="verifier_unavailable") from exc
        if response.status_code >= 400:
            raise EcpVerificationError("Сервис проверки ЭЦП отклонил подпись.", code="verifier_rejected")
        payload = response.json()
        if payload.get("valid") is False or payload.get("success") is False:
            raise EcpVerificationError("Официальный верификатор отклонил подпись ЭЦП.")
        _check_revocation_via_verifier(parsed["cms_der"], challenge, payload)


class DevEcpAdapter:
    name = "dev"

    def verify(self, challenge, cms):
        if not self._allowed():
            raise EcpConfigError("Dev ECP adapter is not allowed in production")
        import base64

        raw = cms.strip() if isinstance(cms, str) else cms
        try:
            decoded = base64.b64decode(raw).decode("utf-8")
            payload = json.loads(decoded)
        except Exception as exc:
            raise EcpVerificationError("Dev-подпись должна быть JSON в Base64.") from exc
        if payload.get("challenge") != challenge.decode("utf-8"):
            raise EcpVerificationError("Подпись относится к другому challenge.")
        iin = payload.get("iin")
        from ekomek_common.validators import validate_iin

        validate_iin(iin)
        return {
            "iin": iin,
            "full_name": payload.get("full_name") or "",
            "birth_date": payload.get("birth_date") or "",
            "certificate_type": payload.get("certificate_type") or "individual",
            "serial_number": payload.get("serial_number") or "dev",
            "issuer": payload.get("issuer") or "DEV NCA",
            "valid_from": payload.get("valid_from") or _utcnow().isoformat(),
            "valid_to": payload.get("valid_to") or _utcnow().isoformat(),
            "fingerprint": payload.get("fingerprint") or "dev",
            "adapter": self.name,
            "cms_hash": payload.get("cms_hash") or "dev",
            "revocation_checked": False,
            "certificate_der": b"",
        }

    def _allowed(self):
        if getattr(settings, "DEBUG", False):
            return True
        return "test" in sys.argv


def get_ecp_adapter():
    name = getattr(settings, "ECP_ADAPTER", "ncalayer")
    if name == "dev":
        adapter = DevEcpAdapter()
        if not adapter._allowed():
            raise EcpConfigError("Dev ECP adapter is not allowed in production")
        return adapter
    return NcaLayerVerifierAdapter()
