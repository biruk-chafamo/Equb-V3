import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from ..ports.live_updates import LiveUpdates

logger = logging.getLogger(__name__)


class ChannelsLiveUpdates:
    def equb_updated(self, equb_id) -> None:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"equb_{equb_id}",
                {
                    "type": "send_equb_update",
                    "equb_id": equb_id,
                },
            )
            logger.info(f"sent live update for equb {equb_id}")
        else:
            logger.warning("channel layer not configured, skipping live update")


default_live_updates: LiveUpdates = ChannelsLiveUpdates()
