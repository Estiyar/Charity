from rest_framework import status
from rest_framework.test import APITestCase

from ekomek_common.auth import make_principal
from ekomek_common.constants import Role
from ekomek_common.risk import DEFAULT_RISK_FACTOR_WEIGHTS, DEFAULT_RISK_THRESHOLDS

from .models import AdminAuditEvent, RiskConfig, RiskConfigAudit


class RiskConfigTest(APITestCase):
    def setUp(self):
        self.admin = make_principal(1, Role.ADMIN, email="admin@test.com", full_name="Администратор")

    def test_get_active_creates_default(self):
        config = RiskConfig.get_active()
        self.assertTrue(config.active)
        self.assertEqual(config.factor_weights, dict(DEFAULT_RISK_FACTOR_WEIGHTS))

    def test_admin_can_read_risk_config(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/admin/risk-config/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("factor_weights", response.data)
        self.assertIn("risk_thresholds", response.data)
        self.assertIn("business_limits", response.data)

    def test_admin_can_update_weights(self):
        self.client.force_authenticate(self.admin)
        new_weights = dict(DEFAULT_RISK_FACTOR_WEIGHTS)
        new_weights["new_account"] = 25
        response = self.client.patch(
            "/api/admin/risk-config/",
            {"factor_weights": new_weights},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["factor_weights"]["new_account"], 25)
        self.assertEqual(RiskConfigAudit.objects.count(), 1)
        self.assertEqual(AdminAuditEvent.objects.filter(action="risk_config_updated").count(), 1)

    def test_admin_can_update_thresholds(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            "/api/admin/risk-config/",
            {"risk_thresholds": {"low_max": 20, "medium_max": 50, "high_max": 75}},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["risk_thresholds"]["low_max"], 20)

    def test_admin_can_update_business_limits(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            "/api/admin/risk-config/",
            {"business_limits": {"max_fundraisers_per_author_per_month": 5}},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["business_limits"]["max_fundraisers_per_author_per_month"], 5)

    def test_history_endpoint(self):
        self.client.force_authenticate(self.admin)
        self.client.patch(
            "/api/admin/risk-config/",
            {"factor_weights": {"new_account": 30}},
            format="json",
        )
        response = self.client.get("/api/admin/risk-config/history/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_internal_risk_config(self):
        RiskConfig.get_active()
        response = self.client.get(
            "/internal/risk-config/",
            HTTP_X_INTERNAL_TOKEN="dev-internal-token",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("factor_weights", response.data)
        self.assertIn("business_limits", response.data)

    def test_non_admin_cannot_access(self):
        moderator = make_principal(2, Role.MODERATOR, email="mod@test.com")
        self.client.force_authenticate(moderator)
        response = self.client.get("/api/admin/risk-config/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
