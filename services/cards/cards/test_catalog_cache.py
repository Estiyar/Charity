from decimal import Decimal

from django.core.cache import cache
from rest_framework.test import APITestCase

from ekomek_common.constants import CardStatus

from .catalog_cache import invalidate_catalog_cache
from .models import FundraisingCard
from .services import collect_amount
from .test_catalog import make_card


class CatalogCacheInvalidationTestCase(APITestCase):
    def setUp(self):
        cache.clear()
        self.card = make_card(collected_amount=Decimal("0.00"))

    def catalog(self):
        return self.client.get("/api/catalog/")

    def test_queryset_update_without_invalidation_stays_stale(self):
        first = self.catalog()
        self.assertEqual(first.data["count"], 1)
        FundraisingCard.objects.filter(pk=self.card.pk).update(status=CardStatus.DRAFT)
        stale = self.catalog()
        self.assertEqual(stale.data["count"], 1)
        invalidate_catalog_cache()
        fresh = self.catalog()
        self.assertEqual(fresh.data["count"], 0)

    def test_save_invalidates_catalog_cache(self):
        self.catalog()
        self.card.status = CardStatus.DRAFT
        self.card.save(update_fields=["status"])
        response = self.catalog()
        self.assertEqual(response.data["count"], 0)

    def test_collect_amount_invalidates_catalog_cache(self):
        first = self.catalog()
        self.assertEqual(first.data["results"][0]["collected_amount"], "0.00")
        collect_amount(self.card.id, Decimal("1500.00"), idempotency_key="payment:catalog")
        response = self.catalog()
        self.assertEqual(response.data["results"][0]["collected_amount"], "1500.00")
