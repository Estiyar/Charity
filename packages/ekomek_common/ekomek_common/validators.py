import re

from django.conf import settings
from django.core.exceptions import ValidationError

IIN_PATTERN = re.compile(r"^\d{12}$")


def validate_iin(value):
    if not value or not IIN_PATTERN.match(str(value)):
        raise ValidationError("ИИН должен содержать ровно 12 цифр.")
    return value


def validate_upload(file):
    extension = file.name.rsplit(".", 1)[-1].lower() if "." in file.name else ""
    allowed = getattr(settings, "ALLOWED_UPLOAD_EXTENSIONS", ["pdf", "jpg", "jpeg", "png"])
    if extension not in allowed:
        raise ValidationError(
            f"Недопустимый тип файла. Разрешены: {', '.join(allowed)}"
        )
    max_mb = getattr(settings, "MAX_UPLOAD_SIZE_MB", 10)
    if file.size > max_mb * 1024 * 1024:
        raise ValidationError(f"Файл больше {max_mb} МБ")
    return file
