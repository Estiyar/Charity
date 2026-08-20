from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont

from .masking import contains_iin, mask_iin

COVER_SIZE = (800, 1100)
IMAGE_TYPES = {"jpg", "jpeg", "png"}


def bytes_look_confidential(file_bytes, metadata, file_name):
    return contains_iin(file_bytes) or contains_iin(metadata) or contains_iin(file_name)


def build_public_copy(version, file_bytes):
    confidential = version.has_confidential or bytes_look_confidential(
        file_bytes, version.metadata, version.file_name
    )
    if confidential or version.file_type not in IMAGE_TYPES:
        content = _cover_image(version)
        version.has_confidential = True
        return ContentFile(content, name=f"{version.version_number}.png")
    return ContentFile(_strip_image_metadata(file_bytes, version.file_type), name=_public_name(version))


def _public_name(version):
    extension = "jpg" if version.file_type in {"jpg", "jpeg"} else version.file_type
    return f"{version.version_number}.{extension}"


def _strip_image_metadata(file_bytes, file_type):
    image = Image.open(BytesIO(file_bytes))
    converted = image.convert("RGB") if file_type in {"jpg", "jpeg"} else image.convert("RGBA")
    buffer = BytesIO()
    if file_type in {"jpg", "jpeg"}:
        converted.save(buffer, format="JPEG", quality=85)
    else:
        converted.save(buffer, format="PNG")
    return buffer.getvalue()


def _cover_image(version):
    image = Image.new("RGB", COVER_SIZE, "#f8fafc")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    lines = [
        "Медицинский документ",
        mask_iin(version.document.get_document_type_display()),
        f"Организация: {mask_iin(version.issuer) or 'скрыто'}",
        f"Дата выдачи: {version.issued_at or 'не указана'}",
        f"Статус: {version.verification_status}",
        "Персональные данные скрыты",
    ]
    top = 80
    for line in lines:
        draw.text((48, top), str(line), fill="#0f172a", font=font)
        top += 48
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
