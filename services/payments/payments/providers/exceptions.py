class PaymentProviderError(Exception):
    def __init__(self, message, code="provider_error", status_code=502):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class PaymentConfigError(PaymentProviderError):
    def __init__(self, message):
        super().__init__(message, code="provider_not_configured", status_code=503)


class InvalidProviderSignature(PaymentProviderError):
    def __init__(self, message="Недействительная подпись платёжного провайдера."):
        super().__init__(message, code="invalid_signature", status_code=400)


class ProviderMismatchError(PaymentProviderError):
    def __init__(self, message):
        super().__init__(message, code="provider_mismatch", status_code=400)
