from django.conf import settings

from .dev import DevPayoutAdapter
from .exceptions import PayoutConfigError


def get_payout_adapter(name=None):
    adapter_name = name or getattr(settings, "PAYOUT_ADAPTER", "dev")
    if adapter_name == "dev":
        return DevPayoutAdapter()
    raise PayoutConfigError(f"Неизвестный адаптер выплат: {adapter_name}")
