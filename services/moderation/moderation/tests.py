from rest_framework.test import APITestCase


class ModerationHealthTest(APITestCase):
    def test_health(self):
        self.assertEqual(self.client.get("/health/").status_code, 200)
