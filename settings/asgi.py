import os

from django.core.asgi import get_asgi_application

from settings.conf import ENV_ID


assert ENV_ID, "Environmental value is not set"

os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    f'settings.env.{ENV_ID}'
)

application = get_asgi_application()