from .settings import *

DATABASES['default']['PORT'] = os.getenv('POSTGRES_PORT', '5432')
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
