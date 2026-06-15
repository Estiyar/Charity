"""Валидация загружаемых файлов (ТЗ раздел 32):
только PDF/JPG/PNG, проверка размера."""

from django.conf import settings
from django.core.exceptions import ValidationError


def validate_upload(file):
    ext = file.name.rsplit(".", 1)[-1].lower() if "." in file.name else ""
    if ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
        raise ValidationError(
            f"Недопустимый тип файла. Разрешены: {', '.join(settings.ALLOWED_UPLOAD_EXTENSIONS)}"
        )
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file.size > max_bytes:
        raise ValidationError(f"Файл больше {settings.MAX_UPLOAD_SIZE_MB} МБ")
    return file
