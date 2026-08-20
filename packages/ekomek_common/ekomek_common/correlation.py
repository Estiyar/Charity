import uuid

from django.utils.deprecation import MiddlewareMixin

REQUEST_ID_HEADER = "HTTP_X_REQUEST_ID"
CORRELATION_ID_HEADER = "HTTP_X_CORRELATION_ID"
RESPONSE_REQUEST_ID = "X-Request-ID"
RESPONSE_CORRELATION_ID = "X-Correlation-ID"

_request_id = ""
_correlation_id = ""


def current_request_id():
    return _request_id


def current_correlation_id():
    return _correlation_id or _request_id


def set_context(request_id, correlation_id):
    global _request_id, _correlation_id
    _request_id = request_id
    _correlation_id = correlation_id


def new_id():
    return str(uuid.uuid4())


class CorrelationIdMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request_id = request.META.get(REQUEST_ID_HEADER) or new_id()
        correlation_id = request.META.get(CORRELATION_ID_HEADER) or request_id
        request.request_id = request_id
        request.correlation_id = correlation_id
        set_context(request_id, correlation_id)

    def process_response(self, request, response):
        response[RESPONSE_REQUEST_ID] = getattr(request, "request_id", new_id())
        response[RESPONSE_CORRELATION_ID] = getattr(
            request, "correlation_id", response[RESPONSE_REQUEST_ID]
        )
        return response
