class EcpVerificationError(Exception):
    def __init__(self, message, code="invalid_signature"):
        self.message = message
        self.code = code
        super().__init__(message)


class EcpConfigError(EcpVerificationError):
    def __init__(self, message):
        super().__init__(message, code="ecp_not_configured")
