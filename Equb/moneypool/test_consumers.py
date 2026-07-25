import json

import pytest
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from rest_framework_simplejwt.tokens import RefreshToken

from .factories import EqubFactory, UserFactory
from .jwt_middleware import JWTAuthMiddleware
from .routing import websocket_urlpatterns

application = JWTAuthMiddleware(URLRouter(websocket_urlpatterns))


def _ws_url(token=None):
    return f"/ws/moneypool/?token={token}" if token else "/ws/moneypool/"


