"""
Created by Epic at 9/5/20
"""

from asyncio import Event, Lock, AbstractEventLoop, sleep
from aiohttp import ClientWebSocketResponse, WSMessage, WSMsgType
import logging
from sys import platform


class DefaultShard:
    def __init__(self, shard_id, client, loop: AbstractEventLoop):
        self.id = shard_id
        self.client = client
        self.loop = loop

        self.ws: ClientWebSocketResponse = None
        self.gateway_url = None
        self.ws_ratelimiting_lock = Lock(loop=self.loop)
        self.logger = logging.getLogger(f"speedcord.shard.{self.id}")
        self.connected = Event(loop=self.loop)  # Some bots might wanna know which shards is online at all times
        self.received_heartbeat_ack = True
        self.heartbeat_interval = None
        self.heartbeat_count = None
        self.session_id = None
        self.last_event_id = None  # This gets modified by gateway.py

        # Default events
        self.client.opcode_dispatcher.register(10, self.handle_hello)
        self.client.opcode_dispatcher.register(11, self.handle_heartbeat_ack)
        self.client.opcode_dispatcher.register(9, self.handle_invalid_session)

        self.client.event_dispatcher.register("READY", self.handle_ready)

    async def connect(self, gateway_url):
        if self.ws is not None:
            if not self.ws.closed:
                await self.ws.close()
            self.ws = None
        self.gateway_url = gateway_url
        self.ws = await self.client.http.create_ws(gateway_url, compression=0)
        self.loop.create_task(self.read_loop())
        self.connected.set()
        if self.session_id is None:
            await self.identify()
        else:
            await self.resume()

    async def close(self):
        if self.ws is not None and not self.ws.closed:
            await self.ws.close()

    async def read_loop(self):
        message: WSMessage  # Fix typehinting
        async for message in self.ws:
            if message.type == WSMsgType.TEXT:
                await self.client.gateway_handler.on_receive(message.json(), self)
            elif message.type in [WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED]:
                self.logger.warning(
                    f"WebSocket is closing! Details: {message.json()}. Close code: {self.ws.close_code}")
            else:
                self.logger.warning("Unknown message type: " + str(type(message)))

    async def send(self, data: dict):
        await self.ws_ratelimiting_lock.acquire()
        self.logger.debug("Data sent: " + str(data))
        await self.ws.send_json(data)
        await sleep(.5)
        self.ws_ratelimiting_lock.release()

    async def identify(self):
        await self.send({
            "op": 2,
            "d": {
                "token": self.client.token,
                "properties": {
                    "$os": platform,
                    "$browser": "SpeedCord",
                    "$device": "SpeedCord"
                },
                "intents": self.client.intents,
                "shard": (self.id, self.client.shard_count)
            }
        })

    async def resume(self):
        await self.send({
            "op": 6,
            "d": {
                "token": self.client.token,
                "session_id": self.session_id,
                "seq": self.last_event_id
            }
        })

    async def heartbeat_loop(self):
        while self.connected.is_set():
            if not self.received_heartbeat_ack:
                self.logger.warning("WebSocket is no longer responding to heartbeats!")
            self.received_heartbeat_ack = False
            await self.send({
                "op": 1,
                "d": self.heartbeat_count
            })
            if self.heartbeat_count is not None:
                self.heartbeat_count += 1
            else:
                self.heartbeat_count = 0
            await sleep(self.heartbeat_interval)

    async def handle_hello(self, data, shard):
        if shard.id != self.id:
            return
        self.received_heartbeat_ack = True
        self.heartbeat_interval = data["d"]["heartbeat_interval"] / 1000
        self.loop.create_task(self.heartbeat_loop())
        self.logger.debug("Started heartbeat loop")

    async def handle_heartbeat_ack(self, data, shard):
        if shard.id != self.id:
            return
        self.received_heartbeat_ack = True

    async def handle_ready(self, data, shard):
        if shard.id != self.id:
            return
        self.session_id = data["session_id"]

    async def handle_invalid_session(self, data, shard):
        if shard.id != self.id:
            return
        if not data.get("d", False):
            # Session is no longer valid, create a new session
            self.session_id = None
        await self.connect(self.gateway_url)


