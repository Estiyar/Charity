"""Статусная машина карточки (ТЗ раздел 6).
Вся логика переходов — здесь. Добавить статус = добавить в CardStatus
и прописать разрешённые переходы в TRANSITIONS."""

from django.db import models


class CardStatus(models.TextChoices):
    DRAFT = "draft", "Черновик"
    PENDING_MODERATION = "pending_moderation", "На модерации"
    REVISION_REQUIRED = "revision_required", "Требуется доработка"
    APPROVED = "approved", "Одобрена"
    ACTIVE = "active", "Активна"
    REJECTED = "rejected", "Отклонена"
    COMPLETED = "completed", "Завершена"
    DECEASED = "deceased", "Получатель умер"
    REDISTRIBUTION = "redistribution", "Перераспределение средств"
    ARCHIVED = "archived", "Архив"


# Какие статусы видны публично (ТЗ раздел 12)
PUBLIC_STATUSES = {
    CardStatus.ACTIVE,
    CardStatus.COMPLETED,
    CardStatus.REDISTRIBUTION,
}

# Разрешённые переходы статусов
TRANSITIONS = {
    CardStatus.DRAFT: {CardStatus.PENDING_MODERATION},
    CardStatus.PENDING_MODERATION: {
        CardStatus.APPROVED,
        CardStatus.REVISION_REQUIRED,
        CardStatus.REJECTED,
    },
    CardStatus.REVISION_REQUIRED: {CardStatus.PENDING_MODERATION},
    CardStatus.APPROVED: {CardStatus.ACTIVE},
    CardStatus.ACTIVE: {
        CardStatus.COMPLETED,
        CardStatus.DECEASED,
        CardStatus.REDISTRIBUTION,
        CardStatus.ARCHIVED,
    },
    CardStatus.COMPLETED: {CardStatus.REDISTRIBUTION, CardStatus.ARCHIVED},
    CardStatus.DECEASED: {CardStatus.REDISTRIBUTION, CardStatus.ARCHIVED},
    CardStatus.REDISTRIBUTION: {CardStatus.ARCHIVED, CardStatus.COMPLETED},
    CardStatus.REJECTED: {CardStatus.ARCHIVED},
    CardStatus.ARCHIVED: set(),
}


class InvalidStatusTransition(Exception):
    pass


def can_transition(current: str, target: str) -> bool:
    return target in TRANSITIONS.get(current, set())


def transition(card, target: str, save: bool = True):
    if not can_transition(card.status, target):
        raise InvalidStatusTransition(
            f"Нельзя перейти из '{card.status}' в '{target}'"
        )
    card.status = target
    if save:
        card.save(update_fields=["status", "updated_at"])
    return card
