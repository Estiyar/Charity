from django.db import transaction
from django.db.models import F

from .models import BalanceTransaction, BalanceTransactionType, User


class BalanceError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


@transaction.atomic
def credit_user_balance(user, amount, description=""):
    if amount <= 0:
        return user
    User.objects.filter(pk=user.pk).update(balance=F("balance") + amount)
    BalanceTransaction.objects.create(
        user=user,
        amount=amount,
        transaction_type=BalanceTransactionType.REFUND_IN,
        description=description,
    )
    user.refresh_from_db()
    return user


@transaction.atomic
def withdraw_user_balance(user, amount):
    if amount <= 0:
        raise BalanceError("Сумма вывода должна быть больше нуля.")
    user = User.objects.select_for_update().get(pk=user.pk)
    if user.balance < amount:
        raise BalanceError("Недостаточно средств на балансе.")
    User.objects.filter(pk=user.pk).update(balance=F("balance") - amount)
    transaction_record = BalanceTransaction.objects.create(
        user=user,
        amount=amount,
        transaction_type=BalanceTransactionType.WITHDRAW_OUT,
        description="Заявка на вывод принята",
    )
    user.refresh_from_db()
    return user, transaction_record
