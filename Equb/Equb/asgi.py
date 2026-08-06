"""
ASGI config for Equb project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/asgi/
"""

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Equb.settings')

from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

django_asgi_app = get_asgi_application()

from moneypool.routing import websocket_urlpatterns
from moneypool.jwt_middleware import JWTAuthMiddleware

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": JWTAuthMiddleware(AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )),
    }
)
