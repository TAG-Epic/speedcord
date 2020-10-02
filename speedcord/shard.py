"""
Created by Epic at 9/5/20
"""

from asyncio import Event, Lock, AbstractEventLoop, sleep
from aiohttp import WSMessage, WSMsgType
import logging
from sys import platform
from ujson import loads, dumps
from time import time


class DefaultShard:
    def __init__(self, shard_id, client, loop: AbstractEventLoop):
        self.id = shard_id
        self.client = client
        self.loop = loop

        self.ws = None
        self.gateway_url = None
        self.ws_ratelimiting_lock = Lock(loop=self.loop)
        self.logger = logging.getLogger(f"speedcord.shard.{self.id}")
        self.connected = Event(loop=self.loop)  # Some bots might wanna know which shards is online at all times
        self.received_heartbeat_ack = True
        self.heartbeat_interval = None
        self.heartbeat_count = None
        self.failed_heartbeats = 0
        self.session_id = None
        self.last_event_id = None  # This gets modified by gateway.py
        self.gateway_send_lock = Lock(loop=self.loop)
        self.gateway_send_limit = 120
        self.gateway_send_per = 60
        self.gateway_send_left = self.gateway_send_limit
        self.gateway_send_reset = time() + self.gateway_send_per

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
            async with self.client.connection_lock:
                self.client.remaining_connections -= 1
                if self.client.remaining_connections <= 1:
                    self.logger.info("Max connections reached!")
                    gateway_url, shard_count, _, connections_reset_after = await self.client.get_gateway()
                    await sleep(connections_reset_after / 1000)
                    gateway_url, shard_count, \
                        self.client.remaining_connections, connections_reset_after = await self.client.get_gateway()
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
                await self.client.gateway_handler.on_receive(message.json(loads=loads), self)
            elif message.type in [WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED]:
                self.logger.warning(
                    f"WebSocket is closing! Details: {message.json()}. Close code: {self.ws.close_code}")
            else:
                self.logger.warning("Unknown message type: " + str(type(message)))

    async def send(self, data: dict):
        async with self.ws_ratelimiting_lock:
            current_time = time()
            if current_time >= self.gateway_send_reset:
                self.gateway_send_reset = current_time + self.gateway_send_per
                self.gateway_send_left = self.gateway_send_limit
            if self.gateway_send_left == 0:
                sleep_for = self.gateway_send_reset - current_time
                self.logger.debug(f"Gateway ratelimited! Sleeping for {sleep_for}s")
                await sleep(self.gateway_send_reset - current_time)
            self.logger.debug("Data sent: " + str(data))
            await self.ws.send_json(data, dumps=dumps)

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
                self.failed_heartbeats += 1
                self.logger.info(
                    "WebSocket did not respond to a heartbeat! Failed attempts: " + str(self.failed_heartbeats))
                if self.failed_heartbeats > 2:
                    self.logger.warning("Gateway stopped responding, reconnecting!")
                    await self.connect(self.gateway_url)
                    return
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
        self.failed_heartbeats = 0

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
