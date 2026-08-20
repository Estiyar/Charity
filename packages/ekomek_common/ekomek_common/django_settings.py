from datetime import timedelta
from pathlib import Path
import os
import sys

from ekomek_common.logging import configure_logging


def env(name, default=""):
    return os.environ.get(name, default)


def build_settings(
    *,
    service_name,
    schema,
    base_dir,
    extra_apps,
    auth_user_model=None,
    use_identity_jwt=False,
):
    base_dir = Path(base_dir)
    debug = env("DEBUG", "True") == "True"
    using_sqlite = env("DB_ENGINE", "") == "sqlite" or "test" in sys.argv
    if using_sqlite:
        databases = {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": env("SQLITE_NAME", str(base_dir / "db.sqlite3")),
            }
        }
    else:
        databases = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": env("DB_NAME", "ekomek"),
                "USER": env("DB_USER", "ekomek"),
                "PASSWORD": env("DB_PASSWORD", "ekomek"),
                "HOST": env("DB_HOST", "localhost"),
                "PORT": env("DB_PORT", "5432"),
                "OPTIONS": {"options": f"-c search_path={schema},public"},
            }
        }

    installed_apps = [
        "django.contrib.contenttypes",
        "django.contrib.auth",
        "django.contrib.sessions",
        "django.contrib.staticfiles",
        "rest_framework",
        "rest_framework_simplejwt",
        "django_filters",
        "ekomek_common.outbox_app",
        "ekomek_common.audit_app",
        *extra_apps,
    ]

    jwt_auth = (
        "ekomek_common.auth.IdentityJWTAuthentication"
        if use_identity_jwt
        else "ekomek_common.auth.ServiceJWTAuthentication"
    )

    settings = {
        "SERVICE_NAME": service_name,
        "BASE_DIR": base_dir,
        "SECRET_KEY": env("SECRET_KEY", "dev-insecure-change-me-use-32-bytes-min"),
        "JWT_SIGNING_KEY": env("JWT_SIGNING_KEY", env("SECRET_KEY", "dev-insecure-change-me-use-32-bytes-min")),
        "DEBUG": debug,
        "ALLOWED_HOSTS": env("ALLOWED_HOSTS", "*").split(","),
        "INSTALLED_APPS": installed_apps,
        "MIDDLEWARE": [
            "ekomek_common.correlation.CorrelationIdMiddleware",
            "django.middleware.security.SecurityMiddleware",
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.middleware.common.CommonMiddleware",
            "django.middleware.csrf.CsrfViewMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "django.middleware.clickjacking.XFrameOptionsMiddleware",
        ],
        "ROOT_URLCONF": "config.urls",
        "WSGI_APPLICATION": "config.wsgi.application",
        "TEMPLATES": [
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [],
                "APP_DIRS": True,
                "OPTIONS": {"context_processors": []},
            }
        ],
        "DATABASES": databases,
        "LANGUAGE_CODE": "ru-ru",
        "TIME_ZONE": "Asia/Almaty",
        "USE_I18N": True,
        "USE_TZ": True,
        "STATIC_URL": "static/",
        "STATIC_ROOT": base_dir / "staticfiles",
        "MEDIA_URL": "/media/",
        "MEDIA_ROOT": Path(env("MEDIA_ROOT", str(base_dir / "media"))),
        "DEFAULT_AUTO_FIELD": "django.db.models.BigAutoField",
        "REST_FRAMEWORK": {
            "DEFAULT_AUTHENTICATION_CLASSES": (jwt_auth,),
            "DEFAULT_PERMISSION_CLASSES": (
                "rest_framework.permissions.IsAuthenticatedOrReadOnly",
            ),
            "DEFAULT_FILTER_BACKENDS": (
                "django_filters.rest_framework.DjangoFilterBackend",
                "rest_framework.filters.SearchFilter",
                "rest_framework.filters.OrderingFilter",
            ),
            "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
            "PAGE_SIZE": 12,
        },
        "SIMPLE_JWT": {
            "ACCESS_TOKEN_LIFETIME": timedelta(hours=12),
            "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
            "SIGNING_KEY": env("JWT_SIGNING_KEY", env("SECRET_KEY", "dev-insecure-change-me-use-32-bytes-min")),
            "AUTH_HEADER_TYPES": ("Bearer",),
            "UPDATE_LAST_LOGIN": True,
        },
        "CELERY_BROKER_URL": env("CELERY_BROKER_URL", "amqp://ekomek:ekomek@localhost:5672//"),
        "CELERY_RESULT_BACKEND": env("CELERY_RESULT_BACKEND", "redis://localhost:6379/1"),
        "CELERY_TASK_DEFAULT_QUEUE": f"{service_name}.tasks",
        "CELERY_BEAT_SCHEDULE": {
            "publish-outbox": {
                "task": "ekomek_common.publish_outbox",
                "schedule": 2.0,
            }
        },
        "REDIS_URL": env("REDIS_URL", "redis://localhost:6379/0"),
        "INTERNAL_SERVICE_TOKEN": env("INTERNAL_SERVICE_TOKEN", "dev-internal-token"),
        "IDENTITY_SERVICE_URL": env("IDENTITY_SERVICE_URL", "http://localhost:8001"),
        "PROFILE_SERVICE_URL": env("PROFILE_SERVICE_URL", "http://localhost:8002"),
        "CARDS_SERVICE_URL": env("CARDS_SERVICE_URL", "http://localhost:8003"),
        "VERIFICATION_SERVICE_URL": env("VERIFICATION_SERVICE_URL", "http://localhost:8004"),
        "DOCUMENTS_SERVICE_URL": env("DOCUMENTS_SERVICE_URL", "http://localhost:8005"),
        "PAYMENTS_SERVICE_URL": env("PAYMENTS_SERVICE_URL", "http://localhost:8006"),
        "MODERATION_SERVICE_URL": env("MODERATION_SERVICE_URL", "http://localhost:8007"),
        "EXPENSES_SERVICE_URL": env("EXPENSES_SERVICE_URL", "http://localhost:8008"),
        "NOTIFICATIONS_SERVICE_URL": env("NOTIFICATIONS_SERVICE_URL", "http://localhost:8009"),
        "ADMIN_SERVICE_URL": env("ADMIN_SERVICE_URL", "http://localhost:8010"),
        "ALLOWED_UPLOAD_EXTENSIONS": ["pdf", "jpg", "jpeg", "png"],
        "MAX_UPLOAD_SIZE_MB": 10,
        "IIN_HMAC_PEPPER": env(
            "IIN_HMAC_PEPPER",
            "test-only-hmac-pepper" if using_sqlite or debug else "",
        ),
        "SENSITIVE_ENCRYPTION_KEY": env(
            "SENSITIVE_ENCRYPTION_KEY",
            "test-only-encryption-key" if using_sqlite or debug else "",
        ),
        "CACHES": {
            "default": {
                "BACKEND": (
                    "django.core.cache.backends.locmem.LocMemCache"
                    if using_sqlite
                    else "django.core.cache.backends.redis.RedisCache"
                ),
                "LOCATION": "ecp-cache" if using_sqlite else env("REDIS_URL", "redis://localhost:6379/0"),
            }
        },
        "ECP_ADAPTER": env("ECP_ADAPTER", "dev" if using_sqlite else "ncalayer"),
        "ECP_VERIFIER_URL": env("ECP_VERIFIER_URL", ""),
        "ECP_OCSP_URL": env("ECP_OCSP_URL", "http://ocsp.pki.gov.kz/"),
        "ECP_OCSP_REQUIRED": env("ECP_OCSP_REQUIRED", "False") == "True",
        "ECP_REQUIRE_NCA_ISSUER": env(
            "ECP_REQUIRE_NCA_ISSUER",
            "False" if using_sqlite or debug else "True",
        )
        == "True",
        "ECP_CHALLENGE_TTL_SECONDS": int(env("ECP_CHALLENGE_TTL_SECONDS", "300")),
        "ECP_SESSION_TTL_SECONDS": int(env("ECP_SESSION_TTL_SECONDS", "900")),
        "MEDICAL_SOURCE_ADAPTER": env(
            "MEDICAL_SOURCE_ADAPTER",
            "dev" if using_sqlite else "official",
        ),
        "MEDICAL_SOURCE_URL": env("MEDICAL_SOURCE_URL", ""),
        "RECIPIENT_SESSION_TTL_SECONDS": int(env("RECIPIENT_SESSION_TTL_SECONDS", "900")),
        "CATALOG_CACHE_TTL_SECONDS": int(env("CATALOG_CACHE_TTL_SECONDS", "60")),
        "PAYMENT_ADAPTER": env("PAYMENT_ADAPTER", "dev" if using_sqlite or debug else "freedompay"),
        "PAYMENT_CURRENCY": env("PAYMENT_CURRENCY", "KZT"),
        "PAYMENT_FRONTEND_URL": env("PAYMENT_FRONTEND_URL", "http://localhost:5173"),
        "PAYMENT_PUBLIC_API_URL": env("PAYMENT_PUBLIC_API_URL", "http://localhost:8080"),
        "PAYMENT_DEV_SECRET": env("PAYMENT_DEV_SECRET", "dev-payment-secret"),
        "FREEDOMPAY_MERCHANT_ID": env("FREEDOMPAY_MERCHANT_ID", ""),
        "FREEDOMPAY_SECRET": env("FREEDOMPAY_SECRET", ""),
        "FREEDOMPAY_API_URL": env("FREEDOMPAY_API_URL", "https://api.freedompay.kz"),
        "FREEDOMPAY_TESTING_MODE": env("FREEDOMPAY_TESTING_MODE", "True") == "True",
        "EVENT_HANDLERS": {},
        "LOGGING": configure_logging(service_name),
        "AUTH_PASSWORD_VALIDATORS": [
            {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
        ],
    }
    if auth_user_model:
        settings["AUTH_USER_MODEL"] = auth_user_model
    return settings
