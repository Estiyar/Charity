class MedicalSourceError(Exception):
    def __init__(self, message, code="medical_source_error"):
        self.message = message
        self.code = code
        super().__init__(message)


class MedicalSourceUnavailable(MedicalSourceError):
    def __init__(self, message="Медицинский источник временно недоступен."):
        super().__init__(message, code="medical_source_unavailable")


class MedicalSourceConfigError(MedicalSourceError):
    def __init__(self, message):
        super().__init__(message, code="medical_source_not_configured")
