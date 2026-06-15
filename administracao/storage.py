from django.conf import settings
from django.core.files.storage import FileSystemStorage


armazenamento_backups = FileSystemStorage(
    location=settings.BACKUP_ROOT,
    base_url=None,
)
