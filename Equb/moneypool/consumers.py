import json
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
import logging

from .models import *

logger = logging.getLogger(__name__)


class EqubConsumer(WebsocketConsumer):

    def connect(self):
        logger.info("WebSocket connection attempt started")
        
        try:
            user = self.scope.get('user')
            
            if user.is_anonymous:
                logger.warning("Anonymous user attempted to connect - rejecting")
                self.close()
                return
              
            self.equbs = user.joined_equbs.filter(is_completed=False)
            logger.info(f"User has {self.equbs.count()} incomplete equbs")

            for equb in self.equbs:
                async_to_sync(self.channel_layer.group_add)(
                    f"equb_{equb.id}",
                    self.channel_name
                )

            self.accept()
            
        except Exception as e:
            logger.error(f"Error during WebSocket connect: {e}")
            self.close()

    def disconnect(self, code):
        logger.info(f"WebSocket disconnected with code: {code}")
        for equb in self.equbs:
            async_to_sync(self.channel_layer.group_discard)(
                f"equb_{equb.id}",
                self.channel_name
            )

    def receive(self,  text_data=None, bytes_data=None):
       # messages are sent from post save signals, not from websocket clients
        pass

    # Receive bid_amount from room group
    def send_equb_update(self, event):
        equb_id = event['equb_id']

        # Send bid_amount to WebSocket
        self.send(text_data=json.dumps({
                  'equb_id': equb_id
        }))
        logger.info(f'sending update to {equb_id} to all users')
