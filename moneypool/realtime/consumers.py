import json
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
import logging

from ..models import *

logger = logging.getLogger(__name__)


class EqubConsumer(WebsocketConsumer):

    def connect(self):
        logger.info("WebSocket connection attempt started")
        self.subscribed_equb_ids = set()

        try:
            user = self.scope.get('user')

            if user.is_anonymous:
                logger.warning("Anonymous user attempted to connect - rejecting")
                self.close()
                return

            equbs = user.joined_equbs.filter(is_completed=False)
            logger.info(f"User has {equbs.count()} incomplete equbs")

            for equb in equbs:
                self._subscribe(equb.id)

            self.accept()

        except Exception as e:
            logger.error(f"Error during WebSocket connect: {e}")
            self.close()

    def disconnect(self, code):
        logger.info(f"WebSocket disconnected with code: {code}")
        for equb_id in self.subscribed_equb_ids:
            async_to_sync(self.channel_layer.group_discard)(
                f"equb_{equb_id}",
                self.channel_name
            )

    def receive(self, text_data=None, bytes_data=None):
        # Clients send {"equb_id": <id>} to (re-)subscribe to an equb's live
        # updates - needed because the connect-time snapshot above misses any
        # equb the user joins after the socket is already open.
        try:
            equb_id = json.loads(text_data).get('equb_id')
        except (TypeError, ValueError, AttributeError):
            return

        user = self.scope.get('user')
        if equb_id is None or user is None or user.is_anonymous:
            return

        if not user.joined_equbs.filter(id=equb_id).exists():
            logger.warning(f"user {user.id} tried to subscribe to equb {equb_id} without membership")
            return

        self._subscribe(equb_id)

    def _subscribe(self, equb_id):
        if equb_id in self.subscribed_equb_ids:
            return
        async_to_sync(self.channel_layer.group_add)(
            f"equb_{equb_id}",
            self.channel_name
        )
        self.subscribed_equb_ids.add(equb_id)

    # Receive bid_amount from room group
    def send_equb_update(self, event):
        equb_id = event['equb_id']

        # Send bid_amount to WebSocket
        self.send(text_data=json.dumps({
                  'equb_id': equb_id
        }))
        logger.info(f'sending update to {equb_id} to all users')
