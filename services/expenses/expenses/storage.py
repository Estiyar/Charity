from django.core.files.storage import FileSystemStorage
from django.conf import settings


def private_expense_storage():
    return FileSystemStorage(location=str(settings.PRIVATE_MEDIA_ROOT), base_url=None)
