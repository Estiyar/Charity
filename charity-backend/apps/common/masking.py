"""Маскирование конфиденциальных данных (ТЗ разделы 8, 28).
Публично показываются только замаскированные значения."""


def mask_iin(iin: str) -> str:
    if not iin:
        return ""
    return iin[:6] + "******"


def mask_document_number(number: str) -> str:
    if not number:
        return ""
    return number[:4] + "****"


def mask_phone(phone: str) -> str:
    """+7 777 *** ** 45 — последние 2 цифры видны."""
    if not phone:
        return ""
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) < 4:
        return "***"
    return f"+7 {digits[1:4]} *** ** {digits[-2:]}"
