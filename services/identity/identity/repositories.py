from .models import BalanceTransaction, User


class UserRepository:
    def get_by_id(self, user_id):
        return User.objects.filter(pk=user_id).first()

    def get_by_email(self, email):
        return User.objects.filter(email__iexact=email).first()

    def email_exists(self, email):
        return User.objects.filter(email__iexact=email).exists()

    def iin_exists(self, iin):
        from ekomek_common.crypto import hmac_hash

        return User.objects.filter(iin_hash=hmac_hash(iin)).exists()

    def list_all(self):
        return User.objects.order_by("-created_at")

    def list_moderators(self):
        from ekomek_common.constants import Role

        return User.objects.filter(role=Role.MODERATOR).order_by("full_name")

    def list_filtered(self, status=None, role=None):
        queryset = User.objects.all()
        if status:
            queryset = queryset.filter(status=status)
        if role:
            queryset = queryset.filter(role=role)
        return queryset.order_by("-created_at")


class BalanceTransactionRepository:
    def list_for_user(self, user):
        return BalanceTransaction.objects.filter(user=user).order_by("-created_at")
