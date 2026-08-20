from datetime import date
from decimal import Decimal

from django.test import TestCase

from ekomek_common.constants import CardStatus

from .models import CollectionReceipt, FundraisingCard
from .services import collect_amount


class CollectAmountIdempotencyTestCase(TestCase):
    def setUp(self):
        self.card = FundraisingCard.objects.create(
            author_id=11,
            full_name="Test",
            diagnosis="X",
            city="Almaty",
            target_amount=Decimal("5000.00"),
            collected_amount=Decimal("0.00"),
            end_date=date(2027, 1, 1),
            status=CardStatus.ACTIVE,
        )

    def test_duplicate_idempotency_key_does_not_double_collect(self):
        collect_amount(self.card.id, Decimal("1000.00"), idempotency_key="payment:7")
        collect_amount(self.card.id, Decimal("1000.00"), idempotency_key="payment:7")
        self.card.refresh_from_db()
        self.assertEqual(self.card.collected_amount, Decimal("1000.00"))
        self.assertEqual(CollectionReceipt.objects.filter(idempotency_key="payment:7").count(), 1)
