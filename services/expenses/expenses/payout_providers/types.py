from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ProviderPayout:
    provider: str
    provider_payout_id: str


@dataclass(frozen=True)
class ProviderPayoutResult:
    provider: str
    provider_payout_id: str
    payout_id: str
    amount: Decimal
    currency: str
    card_id: int
    status: str
    failed_reason: str = ""
    event_key: str = ""
