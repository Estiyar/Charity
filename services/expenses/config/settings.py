from pathlib import Path
import os

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

from ekomek_common.django_settings import build_settings

_BASE_DIR = Path(__file__).resolve().parent.parent

globals().update(
    build_settings(
        service_name="expenses",
        schema="expenses",
        base_dir=_BASE_DIR,
        extra_apps=["expenses"],
        auth_user_model=None,
        use_identity_jwt=False,
    )
)

PRIVATE_MEDIA_ROOT = Path(os.environ.get("PRIVATE_MEDIA_ROOT", str(_BASE_DIR / "private_media")))
PRIVATE_MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
PAYOUT_ADAPTER = os.environ.get("PAYOUT_ADAPTER", "dev")
PAYOUT_DEV_SECRET = os.environ.get("PAYOUT_DEV_SECRET", "dev-payout-secret")
CELERY_BEAT_SCHEDULE = {
    **globals().get("CELERY_BEAT_SCHEDULE", {}),
    "reconcile-ledgers": {
        "task": "expenses.tasks.reconcile_ledgers",
        "schedule": 120.0,
    },
}
