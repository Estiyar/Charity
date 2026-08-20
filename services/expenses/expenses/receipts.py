from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont

from .masking import contains_sensitive, mask_sensitive_text

COVER_SIZE = (800, 1100)
IMAGE_TYPES = {"jpg", "jpeg", "png"}


def build_public_receipt(record, file_bytes, file_name, title=None):
    purpose = getattr(record, "purpose", "") or getattr(record, "payee_name", "")
    confidential = contains_sensitive(file_bytes) or contains_sensitive(file_name) or contains_sensitive(purpose)
    extension = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    if confidential or extension not in IMAGE_TYPES:
        return ContentFile(_cover_image(record, title=title), name="receipt.png")
    return ContentFile(_strip_image_metadata(file_bytes, extension), name=f"receipt.{extension}")


def _strip_image_metadata(file_bytes, file_type):
    image = Image.open(BytesIO(file_bytes))
    converted = image.convert("RGB") if file_type in {"jpg", "jpeg"} else image.convert("RGBA")
    buffer = BytesIO()
    converted.save(buffer, format="JPEG" if file_type in {"jpg", "jpeg"} else "PNG")
    return buffer.getvalue()


def _cover_image(record, title=None):
    image = Image.new("RGB", COVER_SIZE, "#f8fafc")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    category = record.get_category_display() if hasattr(record, "get_category_display") else getattr(record, "payee_name", "")
    lines = [
        title or "Подтверждающий документ расхода",
        mask_sensitive_text(category),
        f"Сумма: {record.amount}",
        f"Дата: {record.date}",
        "Персональные данные скрыты",
    ]
    top = 80
    for line in lines:
        draw.text((48, top), str(line), fill="#0f172a", font=font)
        top += 48
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
