import re

from django.db import migrations, models

from ekomek_common.crypto import SensitiveDataConfigError, decrypt_value


def _plaintext_iin(value):
    raw = (value or "").strip()
    if re.fullmatch(r"\d{12}", raw):
        return raw
    if not raw:
        return ""
    try:
        decrypted = decrypt_value(raw)
    except SensitiveDataConfigError:
        return ""
    return decrypted if re.fullmatch(r"\d{12}", decrypted or "") else ""


def protect_existing_cards(apps, schema_editor):
    from ekomek_common.crypto import protect_document_number, protect_identifier, protect_phone

    Card = apps.get_model("cards", "FundraisingCard")
    for card in Card.objects.all():
        raw_iin = _plaintext_iin(card.recipient_iin) or _plaintext_iin(card.iin_encrypted)
        if raw_iin:
            protected = protect_identifier(raw_iin)
            card.iin_hash = protected["hash"]
            card.iin_masked = protected["masked"]
            card.iin_encrypted = protected["encrypted"]
        raw_document = (card.document_number_encrypted or "").strip()
        if raw_document:
            try:
                decrypted_document = decrypt_value(raw_document)
            except SensitiveDataConfigError:
                decrypted_document = raw_document
            protected_document = protect_document_number(decrypted_document)
            card.document_number_hash = protected_document["hash"]
            card.document_number_masked = protected_document["masked"]
            card.document_number_encrypted = protected_document["encrypted"]
        raw_phone = card.contact_phone or ""
        if raw_phone:
            phone = protect_phone(raw_phone)
            card.contact_phone_encrypted = phone["encrypted"]
            card.contact_phone_masked = phone["masked"]
        card.save()


def noop_reverse(apps, schema_editor):
    return None


class Migration(migrations.Migration):
    dependencies = [
        ("cards", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="fundraisingcard",
            name="iin_hash",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AddField(
            model_name="fundraisingcard",
            name="document_number_hash",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AddField(
            model_name="fundraisingcard",
            name="contact_phone_encrypted",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="fundraisingcard",
            name="contact_phone_masked",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AlterField(
            model_name="fundraisingcard",
            name="iin_encrypted",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="fundraisingcard",
            name="document_number_encrypted",
            field=models.TextField(blank=True),
        ),
        migrations.RunPython(protect_existing_cards, noop_reverse),
        migrations.RemoveField(model_name="fundraisingcard", name="recipient_iin"),
        migrations.RemoveField(model_name="fundraisingcard", name="contact_phone"),
    ]
