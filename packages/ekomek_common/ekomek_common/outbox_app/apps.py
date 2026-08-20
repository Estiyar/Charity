from django.apps import AppConfig


class EkomekOutboxConfig(AppConfig):
    name = "ekomek_common.outbox_app"
    label = "ekomek_outbox"
    verbose_name = "Outbox"
