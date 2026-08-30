from .settings import *

DATABASES['default']['PORT'] = os.getenv('POSTGRES_PORT', '5432')
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# never reach for S3 in tests, whatever USE_S3 says in the developer's .env
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "public_media": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
