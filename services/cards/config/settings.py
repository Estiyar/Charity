from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

from ekomek_common.django_settings import build_settings

globals().update(
    build_settings(
        service_name="cards",
        schema="cards",
        base_dir=Path(__file__).resolve().parent.parent,
        extra_apps=["cards"],
        auth_user_model=None,
        use_identity_jwt=False,
    )
)
