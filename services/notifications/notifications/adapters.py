from uuid import uuid4

from django.conf import settings


class DeliveryAdapterResult:
    def __init__(self, provider, provider_message_id, response_payload=None):
        self.provider = provider
        self.provider_message_id = provider_message_id
        self.response_payload = response_payload or {}


class DevDeliveryAdapter:
    channel = ""

    def send(self, *, destination, title, body, payload):
        return DeliveryAdapterResult(
            provider=f"dev-{self.channel}",
            provider_message_id=str(uuid4()),
            response_payload={
                "destination": destination,
                "title": title,
                "body": body,
                "payload": payload,
            },
        )


class DevEmailAdapter(DevDeliveryAdapter):
    channel = "email"


class DevSmsAdapter(DevDeliveryAdapter):
    channel = "sms"


class DevPushAdapter(DevDeliveryAdapter):
    channel = "push"


def get_delivery_adapter(channel):
    adapter_type = ""
    if channel == "email":
        adapter_type = getattr(settings, "NOTIFICATION_EMAIL_ADAPTER", "dev")
    elif channel == "sms":
        adapter_type = getattr(settings, "NOTIFICATION_SMS_ADAPTER", "dev")
    elif channel == "push":
        adapter_type = getattr(settings, "NOTIFICATION_PUSH_ADAPTER", "dev")
    if adapter_type != "dev":
        raise ValueError(f"Unsupported notification adapter: {adapter_type}")
    if channel == "email":
        return DevEmailAdapter()
    if channel == "sms":
        return DevSmsAdapter()
    if channel == "push":
        return DevPushAdapter()
    raise ValueError(f"Unsupported notification channel: {channel}")
