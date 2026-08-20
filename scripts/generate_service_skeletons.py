#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICES = [
    ("identity", "identity", 8001, True),
    ("profile", "profile", 8002, False),
    ("cards", "cards", 8003, False),
    ("verification", "verification", 8004, False),
    ("documents", "documents", 8005, False),
    ("payments", "payments", 8006, False),
    ("moderation", "moderation", 8007, False),
    ("expenses", "expenses", 8008, False),
    ("notifications", "notifications", 8009, False),
    ("admin", "admin_service", 8010, False),
]

MANAGE = '''#!/usr/bin/env python
import os
import sys

def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)

if __name__ == "__main__":
    main()
'''

WSGI = '''import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_wsgi_application()
'''

ASGI = '''import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_asgi_application()
'''

CELERY = '''from ekomek_common.celery import create_celery_app

app = create_celery_app("{service}")
'''

REQUIREMENTS = '''Django>=5.0,<6.0
djangorestframework>=3.15
djangorestframework-simplejwt>=5.3
django-filter>=24.0
psycopg2-binary>=2.9
Pillow>=10.0
python-dotenv>=1.0
gunicorn>=22.0
celery>=5.4
redis>=5.0
httpx>=0.27
prometheus-client>=0.21
'''

ENV_EXAMPLE = '''SERVICE_NAME={service}
SECRET_KEY=change-me-in-production
JWT_SIGNING_KEY=change-me-in-production
DEBUG=True
ALLOWED_HOSTS=*
DB_NAME=ekomek
DB_USER=ekomek
DB_PASSWORD=ekomek
DB_HOST=postgres
DB_PORT=5432
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=amqp://ekomek:ekomek@rabbitmq:5672//
CELERY_RESULT_BACKEND=redis://redis:6379/1
INTERNAL_SERVICE_TOKEN=dev-internal-token
IDENTITY_SERVICE_URL=http://identity-service:8000
PROFILE_SERVICE_URL=http://profile-service:8000
CARDS_SERVICE_URL=http://cards-service:8000
VERIFICATION_SERVICE_URL=http://verification-service:8000
DOCUMENTS_SERVICE_URL=http://documents-service:8000
PAYMENTS_SERVICE_URL=http://payments-service:8000
MODERATION_SERVICE_URL=http://moderation-service:8000
EXPENSES_SERVICE_URL=http://expenses-service:8000
NOTIFICATIONS_SERVICE_URL=http://notifications-service:8000
ADMIN_SERVICE_URL=http://admin-service:8000
'''

APPS = '''from django.apps import AppConfig

class {class_name}Config(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "{app}"
'''

SETTINGS = '''from pathlib import Path
import os

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

from ekomek_common.django_settings import build_settings

globals().update(
    build_settings(
        service_name="{service}",
        schema="{schema}",
        base_dir=Path(__file__).resolve().parent.parent,
        extra_apps=["{app}"],
        auth_user_model={auth_user_model},
        use_identity_jwt={use_identity_jwt},
    )
)
'''


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def main():
    for service, app, _port, is_identity in SERVICES:
        root = ROOT / "services" / service
        schema = "admin" if service == "admin" else service
        class_name = "Admin" if app == "admin_service" else app.capitalize()
        auth_user_model = '"identity.User"' if is_identity else "None"
        write(root / "manage.py", MANAGE)
        write(root / "requirements.txt", REQUIREMENTS)
        write(root / ".env.example", ENV_EXAMPLE.format(service=service))
        write(root / "config" / "__init__.py", "")
        write(
            root / "config" / "settings.py",
            SETTINGS.format(
                service=service,
                schema=schema,
                app=app,
                auth_user_model=auth_user_model,
                use_identity_jwt="True" if is_identity else "False",
            ),
        )
        write(root / "config" / "wsgi.py", WSGI)
        write(root / "config" / "asgi.py", ASGI)
        write(root / "config" / "celery.py", CELERY.format(service=service))
        write(root / app / "__init__.py", "")
        write(
            root / app / "apps.py",
            APPS.format(class_name=class_name, app=app),
        )
        write(root / app / "migrations" / "__init__.py", "")
        write(root / app / "repositories.py", "")
        write(root / app / "events.py", "EVENT_HANDLERS = {}\n")


if __name__ == "__main__":
    main()
