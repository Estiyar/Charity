from django.conf import settings

from .dev import DevPaymentAdapter
from .exceptions import PaymentConfigError
from .freedompay import FreedomPayAdapter


def get_payment_adapter(name=None):
    adapter_name = name or getattr(settings, "PAYMENT_ADAPTER", "freedompay")
    if adapter_name == "dev":
        return DevPaymentAdapter()
    if adapter_name == "freedompay":
        return FreedomPayAdapter()
    raise PaymentConfigError(f"Неизвестный платёжный адаптер: {adapter_name}")
