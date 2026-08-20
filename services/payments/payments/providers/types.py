from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ProviderSession:
    provider: str
    provider_payment_id: str
    redirect_url: str


@dataclass(frozen=True)
class ProviderResult:
    provider: str
    provider_payment_id: str
    order_id: str
    amount: Decimal
    currency: str
    card_id: int
    status: str
    failed_reason: str = ""
    event_key: str = ""
    raw: dict = None
