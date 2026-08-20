import logging

import httpx
from django.conf import settings

from ekomek_common.correlation import current_correlation_id, current_request_id
from ekomek_common.logging import redact_sensitive

logger = logging.getLogger(__name__)


class ServiceClientError(Exception):
    def __init__(self, message, status_code=None, payload=None):
        self.status_code = status_code
        self.payload = payload
        super().__init__(message)


class ServiceClient:
    def __init__(self, base_url, timeout=10.0):
        self.base_url = (base_url or "").rstrip("/")
        self.timeout = timeout

    def _headers(self, extra=None):
        headers = {
            "X-Internal-Token": getattr(settings, "INTERNAL_SERVICE_TOKEN", ""),
            "X-Request-ID": current_request_id() or "",
            "X-Correlation-ID": current_correlation_id() or "",
        }
        if extra:
            headers.update(extra)
        return {key: value for key, value in headers.items() if value}

    def request(self, method, path, json=None, data=None, files=None, params=None, headers=None):
        if not self.base_url:
            raise ServiceClientError("Service URL is not configured")
        url = f"{self.base_url}{path}"
        try:
            response = httpx.request(
                method,
                url,
                json=None if files is not None else json,
                data=data,
                files=files,
                params=params,
                headers=self._headers(headers),
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            safe_url = redact_sensitive(url)
            logger.exception("service_call_failed method=%s url=%s", method, safe_url)
            raise ServiceClientError(redact_sensitive(str(exc))) from exc
        if response.status_code >= 400:
            payload = None
            try:
                payload = response.json()
            except ValueError:
                payload = {"detail": redact_sensitive(response.text)}
            raise ServiceClientError(
                redact_sensitive(f"{method} {url} failed with {response.status_code}"),
                status_code=response.status_code,
                payload=payload,
            )
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self.request("POST", path, **kwargs)

    def patch(self, path, **kwargs):
        return self.request("PATCH", path, **kwargs)


def identity_client():
    return ServiceClient(getattr(settings, "IDENTITY_SERVICE_URL", ""))


def profile_client():
    return ServiceClient(getattr(settings, "PROFILE_SERVICE_URL", ""))


def cards_client():
    return ServiceClient(getattr(settings, "CARDS_SERVICE_URL", ""))


def verification_client():
    return ServiceClient(getattr(settings, "VERIFICATION_SERVICE_URL", ""))


def documents_client():
    return ServiceClient(getattr(settings, "DOCUMENTS_SERVICE_URL", ""))


def payments_client():
    return ServiceClient(getattr(settings, "PAYMENTS_SERVICE_URL", ""))


def moderation_client():
    return ServiceClient(getattr(settings, "MODERATION_SERVICE_URL", ""))


def expenses_client():
    return ServiceClient(getattr(settings, "EXPENSES_SERVICE_URL", ""))


def notifications_client():
    return ServiceClient(getattr(settings, "NOTIFICATIONS_SERVICE_URL", ""))


def admin_client():
    return ServiceClient(getattr(settings, "ADMIN_SERVICE_URL", ""))
