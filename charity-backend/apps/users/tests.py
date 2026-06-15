from django.contrib.auth.hashers import check_password
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase

from .models import Role, User, UserStatus
from .permissions import IsAdmin, IsAuthor, IsDonor, IsModerator


class RegisterAPITestCase(APITestCase):
    url = "/api/auth/register"

    def _payload(self, **overrides):
        data = {
            "full_name": "Иван Иванов",
            "email": "ivan@example.com",
            "phone": "+7 777 123 45 67",
            "password": "securepass123",
            "repeat_password": "securepass123",
            "role": Role.DONOR,
        }
        data.update(overrides)
        return data

    def test_register_donor_success(self):
        response = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["role"], Role.DONOR)
        self.assertEqual(response.data["email"], "ivan@example.com")

        user = User.objects.get(email="ivan@example.com")
        self.assertTrue(check_password("securepass123", user.password))
        self.assertNotEqual(user.password, "securepass123")

    def test_register_author_success(self):
        response = self.client.post(
            self.url,
            self._payload(email="author@example.com", role=Role.AUTHOR),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["role"], Role.AUTHOR)

    def test_register_moderator_role_rejected(self):
        response = self.client.post(
            self.url,
            self._payload(email="mod@example.com", role=Role.MODERATOR),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("role", response.data)

    def test_register_admin_role_rejected(self):
        response = self.client.post(
            self.url,
            self._payload(email="admin@example.com", role=Role.ADMIN),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("role", response.data)

    def test_register_password_mismatch_rejected(self):
        response = self.client.post(
            self.url,
            self._payload(repeat_password="differentpass"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("repeat_password", response.data)


class LoginLogoutMeAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            password="securepass123",
            full_name="Тест Пользователь",
            phone="+7 700 000 00 00",
            role=Role.DONOR,
        )

    def test_login_returns_jwt_tokens(self):
        response = self.client.post(
            "/api/auth/login",
            {"email": "user@example.com", "password": "securepass123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_wrong_password_rejected(self):
        response = self.client.post(
            "/api/auth/login",
            {"email": "user@example.com", "password": "wrongpassword"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_blocked_user_cannot_login(self):
        self.user.status = UserStatus.BLOCKED
        self.user.save(update_fields=["status"])

        response = self.client.post(
            "/api/auth/login",
            {"email": "user@example.com", "password": "securepass123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Пользователь заблокирован.", str(response.data))

    def test_admin_can_unblock_user(self):
        admin = User.objects.create_user(
            email="admin@example.com",
            password="securepass123",
            full_name="Админ",
            role=Role.ADMIN,
        )
        self.user.status = UserStatus.BLOCKED
        self.user.save(update_fields=["status"])

        self.client.force_authenticate(user=admin)
        unblock_response = self.client.patch(
            f"/api/admin/users/{self.user.id}/",
            {"status": UserStatus.ACTIVE},
            format="json",
        )
        self.assertEqual(unblock_response.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=None)
        login_response = self.client.post(
            "/api/auth/login",
            {"email": "user@example.com", "password": "securepass123"},
            format="json",
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

    def test_non_admin_cannot_unblock(self):
        moderator = User.objects.create_user(
            email="mod@example.com",
            password="securepass123",
            full_name="Модератор",
            role=Role.MODERATOR,
        )
        self.user.status = UserStatus.BLOCKED
        self.user.save(update_fields=["status"])

        self.client.force_authenticate(user=moderator)
        response = self.client.patch(
            f"/api/admin/users/{self.user.id}/",
            {"status": UserStatus.ACTIVE},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_logout_requires_authentication(self):
        response = self.client.post("/api/auth/logout")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_success(self):
        login_response = self.client.post(
            "/api/auth/login",
            {"email": "user@example.com", "password": "securepass123"},
            format="json",
        )
        access = login_response.data["access"]

        response = self.client.post(
            "/api/auth/logout",
            HTTP_AUTHORIZATION=f"Bearer {access}",
        )

        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)

    def test_me_returns_current_user(self):
        login_response = self.client.post(
            "/api/auth/login",
            {"email": "user@example.com", "password": "securepass123"},
            format="json",
        )
        access = login_response.data["access"]

        response = self.client.get(
            "/api/auth/me",
            HTTP_AUTHORIZATION=f"Bearer {access}",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "user@example.com")
        self.assertEqual(response.data["full_name"], "Тест Пользователь")
        self.assertEqual(response.data["role"], Role.DONOR)

    def test_me_requires_authentication(self):
        response = self.client.get("/api/auth/me")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RolePermissionsTestCase(APITestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def _request_for_user(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def _create_user(self, role):
        return User.objects.create_user(
            email=f"{role}@example.com",
            password="securepass123",
            full_name="Роль Тест",
            role=role,
        )

    def test_is_donor_permission(self):
        donor = self._create_user(Role.DONOR)
        author = self._create_user(Role.AUTHOR)

        self.assertTrue(IsDonor().has_permission(self._request_for_user(donor), None))
        self.assertFalse(IsDonor().has_permission(self._request_for_user(author), None))

    def test_is_author_permission(self):
        author = self._create_user(Role.AUTHOR)
        donor = self._create_user(Role.DONOR)

        self.assertTrue(IsAuthor().has_permission(self._request_for_user(author), None))
        self.assertFalse(IsAuthor().has_permission(self._request_for_user(donor), None))

    def test_is_moderator_permission(self):
        moderator = self._create_user(Role.MODERATOR)
        donor = self._create_user(Role.DONOR)

        self.assertTrue(
            IsModerator().has_permission(self._request_for_user(moderator), None)
        )
        self.assertFalse(
            IsModerator().has_permission(self._request_for_user(donor), None)
        )

    def test_is_admin_permission(self):
        admin = self._create_user(Role.ADMIN)
        moderator = self._create_user(Role.MODERATOR)

        self.assertTrue(IsAdmin().has_permission(self._request_for_user(admin), None))
        self.assertFalse(
            IsAdmin().has_permission(self._request_for_user(moderator), None)
        )
