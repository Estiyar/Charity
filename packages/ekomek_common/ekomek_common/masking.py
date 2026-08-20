def mask_iin(iin):
    if not iin:
        return ""
    return iin[:6] + "******"


def mask_document_number(number):
    if not number:
        return ""
    return number[:4] + "****"


def mask_phone(phone):
    if not phone:
        return ""
    digits = "".join(character for character in phone if character.isdigit())
    if len(digits) < 4:
        return "***"
    return f"+7 {digits[1:4]} *** ** {digits[-2:]}"
