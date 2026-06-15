from decimal import Decimal

from apps.cards.models import FundraisingCard
from apps.common.card_status import CardStatus, InvalidStatusTransition, transition
from apps.moderation.models import RedistributionDecision


class RedistributionError(Exception):
    pass


REDISTRIBUTION_CASES = {
    "deceased": "Получатель умер",
    "completed_balance": "Сбор завершён, есть остаток",
    "no_documents": "Нет подтверждённых документов расходов",
    "unused_funds": "Неиспользованные средства",
}


def get_redistribution_case(card):
    if card.status == CardStatus.DECEASED:
        return "deceased"
    if card.status == CardStatus.COMPLETED and Decimal(str(card.escrow_balance)) > 0:
        return "completed_balance"
    has_verified_expenses = card.expenses.filter(status="approved").exists()
    if Decimal(str(card.collected_amount)) > 0 and not has_verified_expenses:
        return "no_documents"
    if Decimal(str(card.escrow_available)) > 0:
        return "unused_funds"
    return None


def is_eligible_for_redistribution(card):
    if card.status == CardStatus.REDISTRIBUTION:
        return Decimal(str(card.escrow_balance)) > 0
    if card.status not in {
        CardStatus.ACTIVE,
        CardStatus.COMPLETED,
        CardStatus.DECEASED,
    }:
        return False
    return (
        Decimal(str(card.escrow_balance)) > 0
        or Decimal(str(card.escrow_available)) > 0
    )


def create_redistribution_decision(card, actor, decision_type, target_card=None, comment=""):
    if not is_eligible_for_redistribution(card):
        raise RedistributionError("Карточка не подходит для перераспределения средств.")
    if decision_type == RedistributionDecision.DecisionType.TRANSFER:
        if not target_card:
            raise RedistributionError("Укажите целевую карточку для перераспределения.")
        if target_card.id == card.id:
            raise RedistributionError("Нельзя перераспределить средства на ту же карточку.")
        if target_card.status != CardStatus.ACTIVE:
            raise RedistributionError("Целевая карточка должна быть активной.")
    decision = RedistributionDecision.objects.create(
        card=card,
        decision_type=decision_type,
        target_card=target_card,
        comment=comment,
        created_by=actor,
    )
    if decision_type != RedistributionDecision.DecisionType.HOLD:
        try:
            transition(card, CardStatus.REDISTRIBUTION)
        except InvalidStatusTransition as exc:
            raise RedistributionError(str(exc)) from exc
    return decision


def get_eligible_redistribution_cards():
    queryset = FundraisingCard.objects.select_related("author").order_by("-updated_at")
    return [card for card in queryset if is_eligible_for_redistribution(card)]
