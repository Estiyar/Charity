from datetime import date
from decimal import Decimal

from django.core.cache import cache
from rest_framework.test import APITestCase

from ekomek_common.constants import CardStatus

from .models import FundraisingCard


def make_card(**overrides):
    payload = {
        "author_id": 1,
        "full_name": "Айгуль Смагулова",
        "diagnosis": "Онкология",
        "city": "Алматы",
        "description": "Нужна операция",
        "age": 10,
        "target_amount": Decimal("100000.00"),
        "collected_amount": Decimal("10000.00"),
        "end_date": date(2027, 6, 1),
        "status": CardStatus.ACTIVE,
    }
    payload.update(overrides)
    return FundraisingCard.objects.create(**payload)


class CatalogFilterPaginationTestCase(APITestCase):
    def setUp(self):
        cache.clear()
        self.almaty = make_card()
        self.astana = make_card(
            full_name="Нурлан Беков",
            diagnosis="Кардиология",
            city="Астана",
            description="Реабилитация после операции",
            age=42,
            target_amount=Decimal("50000.00"),
            collected_amount=Decimal("40000.00"),
            end_date=date(2027, 3, 1),
        )
        self.completed = make_card(
            full_name="Завершённый сбор",
            diagnosis="Травма",
            city="Шымкент",
            age=8,
            target_amount=Decimal("20000.00"),
            collected_amount=Decimal("20000.00"),
            status=CardStatus.COMPLETED,
        )
        make_card(
            full_name="Черновик",
            city="Алматы",
            status=CardStatus.DRAFT,
        )

    def catalog(self, **params):
        return self.client.get("/api/catalog/", params)

    def test_hides_non_public_cards(self):
        response = self.catalog()
        names = [item["full_name"] for item in response.data["results"]]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 3)
        self.assertNotIn("Черновик", names)

    def test_hides_manual_review_and_suspended_cards(self):
        make_card(full_name="Высокий риск", status=CardStatus.MANUAL_REVIEW)
        make_card(full_name="Приостановлен", status=CardStatus.SUSPENDED)
        cache.clear()
        names = [item["full_name"] for item in self.catalog().data["results"]]
        self.assertNotIn("Высокий риск", names)
        self.assertNotIn("Приостановлен", names)

    def test_filter_city_diagnosis_status_amount_age(self):
        by_city = self.catalog(city="Алматы")
        self.assertEqual(by_city.data["count"], 1)
        self.assertEqual(by_city.data["results"][0]["city"], "Алматы")

        by_diagnosis = self.catalog(diagnosis="Кардиология")
        self.assertEqual(by_diagnosis.data["count"], 1)

        by_status = self.catalog(status="completed")
        self.assertEqual(by_status.data["count"], 1)
        self.assertEqual(by_status.data["results"][0]["status"], CardStatus.COMPLETED)

        by_amount = self.catalog(target_amount_min="60000", target_amount_max="150000")
        self.assertEqual(by_amount.data["count"], 1)
        self.assertEqual(by_amount.data["results"][0]["id"], self.almaty.id)

        by_age = self.catalog(age_min="30", age_max="50")
        self.assertEqual(by_age.data["count"], 1)
        self.assertEqual(by_age.data["results"][0]["id"], self.astana.id)

    def test_search_full_name_city_diagnosis_description(self):
        self.assertEqual(self.catalog(search="Нурлан").data["count"], 1)
        self.assertEqual(self.catalog(search="Шымкент").data["count"], 1)
        self.assertEqual(self.catalog(search="Онкология").data["count"], 1)
        self.assertEqual(self.catalog(search="Реабилитация").data["count"], 1)

    def test_sort_target_amount_and_progress(self):
        by_target = self.catalog(ordering="-target_amount")
        self.assertEqual(
            [item["id"] for item in by_target.data["results"]],
            [self.almaty.id, self.astana.id, self.completed.id],
        )
        by_progress = self.catalog(ordering="-progress")
        self.assertEqual(by_progress.data["results"][0]["id"], self.completed.id)
        self.assertEqual(by_progress.data["results"][1]["id"], self.astana.id)

    def test_page_and_page_size(self):
        response = self.catalog(page=1, page_size=2)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["page"], 1)
        self.assertEqual(response.data["page_size"], 2)
        page_two = self.catalog(page=2, page_size=2)
        self.assertEqual(len(page_two.data["results"]), 1)

    def test_limit_and_offset(self):
        response = self.catalog(limit=1, offset=1, ordering="full_name")
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(len(response.data["results"]), 1)

    def test_references_list_public_cities_and_diagnoses(self):
        response = self.client.get("/api/catalog/references/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Алматы", response.data["cities"])
        self.assertIn("Онкология", response.data["diagnoses"])
        self.assertNotIn("", response.data["cities"])
