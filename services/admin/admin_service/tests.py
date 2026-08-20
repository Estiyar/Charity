from rest_framework.test import APITestCase

from ekomek_common.auth import make_principal
from ekomek_common.constants import Role


class AdminServiceTest(APITestCase):
    def test_health(self):
        self.assertEqual(self.client.get("/health/").status_code, 200)

    def test_settings_requires_admin(self):
        response = self.client.get("/api/admin/settings/")
        self.assertEqual(response.status_code, 401)

    def test_admin_can_read_settings(self):
        self.client.force_authenticate(make_principal(1, Role.ADMIN, email="admin@test.com"))
        response = self.client.get("/api/admin/settings/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["site_name"], "е-Көмек")
