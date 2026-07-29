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


@pytest.mark.django_db(transaction=True)
class TestConnectAuth:
    def test_valid_token_connects(self):
        async def body():
            user = await _acreate_user()
            token = str(RefreshToken.for_user(user).access_token)
            communicator = WebsocketCommunicator(application, _ws_url(token))
            connected, _ = await communicator.connect()
            assert connected is True
            await communicator.disconnect()

        async_to_sync(body)()

    def test_missing_token_rejected(self):
        async def body():
            communicator = WebsocketCommunicator(application, _ws_url())
            connected, _ = await communicator.connect()
            assert connected is False

        async_to_sync(body)()

    def test_garbage_token_rejected(self):
        async def body():
            communicator = WebsocketCommunicator(application, _ws_url("not-a-real-jwt"))
            connected, _ = await communicator.connect()
            assert connected is False

        async_to_sync(body)()

    def test_expired_or_invalid_signature_token_rejected(self):
        async def body():
            import jwt as pyjwt

            bogus_token = pyjwt.encode({"user_id": 1}, "wrong-secret-key", algorithm="HS256")
            communicator = WebsocketCommunicator(application, _ws_url(bogus_token))
            connected, _ = await communicator.connect()
            assert connected is False

        async_to_sync(body)()


