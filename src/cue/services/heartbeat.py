import asyncio
import logging
from typing import Optional
from datetime import datetime, timedelta

from ..schemas.event_message import EventMessage, EventMessageType, PingPongEventPayload

logger = logging.getLogger(__name__)


class WebSocketHeartbeat:
    def __init__(
        self,
        ws_transport: "AioHTTPWebSocketTransport",  # noqa: F821
        heartbeat_interval: float = 30.0,
        heartbeat_timeout: float = 10.0,
        max_missed_heartbeats: int = 3,
    ):
        self.ws_transport = ws_transport
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        self.max_missed_heartbeats = max_missed_heartbeats
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._last_pong: Optional[datetime] = None
        self._missed_heartbeats = 0
        self._running = False

    async def start(self):
        """Start the heartbeat mechanism"""
        if self._running:
            return

        self._running = True
        self._last_pong = datetime.now()
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("WebSocket heartbeat started")

    async def stop(self):
        """Stop the heartbeat mechanism"""
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        logger.info("WebSocket heartbeat stopped")

    def pong_received(self):
        """Call this method when a pong message is received"""
        self._last_pong = datetime.now()
        self._missed_heartbeats = 0
        logger.debug("Pong received, heartbeat acknowledged")

    async def _heartbeat_loop(self):
        """Main heartbeat loop"""
        while self._running:
            try:
                # Send ping message
                event = EventMessage(
                    type=EventMessageType.PING.value,
                    payload=PingPongEventPayload(type="PING"),
                )
                await self.ws_transport.send(event.model_dump_json())
                logger.debug("Ping sent")

                # Wait for the timeout period
                await asyncio.sleep(self.heartbeat_timeout)

                # Check if we received a pong
                if self._last_pong and datetime.now() - self._last_pong > timedelta(seconds=self.heartbeat_timeout):
                    self._missed_heartbeats += 1
                    logger.warning(f"Missed heartbeat {self._missed_heartbeats}/{self.max_missed_heartbeats}")

                    if self._missed_heartbeats >= self.max_missed_heartbeats:
                        logger.error("Maximum missed heartbeats reached, reconnecting...")
                        await self.ws_transport.disconnect()
                        await self.ws_transport.connect()
                        self._missed_heartbeats = 0
                        self._last_pong = datetime.now()

                # Wait for the remaining interval
                remaining_interval = max(0, self.heartbeat_interval - self.heartbeat_timeout)
                await asyncio.sleep(remaining_interval)

            except Exception as e:
                logger.error(f"Error in heartbeat loop: {str(e)}")
                await asyncio.sleep(self.heartbeat_interval)
