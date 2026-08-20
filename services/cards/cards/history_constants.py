PUBLIC_HISTORY_TYPES = frozenset(
    {
        "card_created",
        "target_amount_changed",
        "diagnosis_changed",
        "description_changed",
        "deadline_changed",
        "clinic_changed",
        "document_added",
        "document_replaced",
        "status_changed",
        "moderation_decision",
        "suspended",
        "unsuspended",
    }
)

EVENT_SUMMARIES = {
    "card_created": "Сбор создан",
    "target_amount_changed": "Целевая сумма изменена",
    "diagnosis_changed": "Диагноз обновлён",
    "description_changed": "Описание обновлено",
    "deadline_changed": "Срок сбора изменён",
    "beneficiary_changed": "Получатель обновлён",
    "clinic_changed": "Клиника обновлена",
    "document_added": "Добавлен медицинский документ",
    "document_replaced": "Документ заменён",
    "payout_details_changed": "Платёжные реквизиты изменены",
    "status_changed": "Статус сбора изменён",
    "moderation_decision": "Модератор принял решение",
    "suspended": "Сбор приостановлен",
    "unsuspended": "Приостановка сбора снята",
}

FIELD_EVENT_TYPES = {
    "target_amount": "target_amount_changed",
    "diagnosis": "diagnosis_changed",
    "description": "description_changed",
    "end_date": "deadline_changed",
    "clinic": "clinic_changed",
    "payout_details_hash": "payout_details_changed",
}

CRITICAL_FIELDS = frozenset(
    {
        "target_amount",
        "diagnosis",
        "end_date",
        "clinic",
        "beneficiary_id",
        "iin_hash",
        "payout_details_hash",
    }
)

HIDDEN_PAYLOAD_KEYS = frozenset(
    {
        "iin",
        "cms",
        "phone",
        "iin_encrypted",
        "iin_hash",
        "document_number",
        "document_number_hash",
        "payout_details_hash",
        "contact_phone",
    }
)
