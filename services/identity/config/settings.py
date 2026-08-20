from pathlib import Path
import os

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

from ekomek_common.django_settings import build_settings

globals().update(
    build_settings(
        service_name="identity",
        schema="identity",
        base_dir=Path(__file__).resolve().parent.parent,
        extra_apps=["identity"],
        auth_user_model="identity.User",
        use_identity_jwt=True,
    )
)
