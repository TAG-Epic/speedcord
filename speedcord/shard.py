"""
Created by Epic at 9/5/20
"""
from .exceptions import GatewayUnavailable, GatewayNotAuthenticated, InvalidToken, InvalidShardCount, \
    InvalidGatewayVersion, IntentNotWhitelisted, InvalidIntentNumber
from .http import Route

from asyncio import Event, Lock, AbstractEventLoop, sleep
from asyncio.exceptions import TimeoutError
from aiohttp.client_exceptions import ClientConnectorError
from aiohttp import WSMessage, WSMsgType
from logging import getLogger
from sys import platform
from ujson import loads, dumps
from time import time


class DefaultShard:
    def __init__(self, shard_id, client, loop: AbstractEventLoop):
        """
        Handles all Discord Shard related events. For more information on what sharding is and how it works:
        https://discord.com/developers/docs/topics/gateway#sharding.
        This simply represents a Discord Shard. The actual handling of events happens via the client's handlers.
        :param shard_id: The id for the shard.
        :param client: A speedcord.Client object which will manage the shards.
        :param loop: an AbstractEventLoop which is used to create callbacks.
        """
        self.id = shard_id
        self.client = client
        self.loop = loop

        self.ws = None
        self.gateway_url = None
        self.logger = getLogger(f"speedcord.shard.{self.id}")
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

        self.is_ready = Event(loop=self.loop)

        # Default events
        self.client.opcode_dispatcher.register(10, self.handle_hello)
        self.client.opcode_dispatcher.register(11, self.handle_heartbeat_ack)
        self.client.opcode_dispatcher.register(9, self.handle_invalid_session)

        self.client.event_dispatcher.register("READY", self.handle_ready)

    async def connect(self, gateway_url=None):
        """
        Connects to the gateway. Usually done by the client.
        :param gateway_url: The gateway url.
        """
        await self.close()
        if gateway_url is None:
            r = Route("GET", "/gateway")
            resp = await self.client.http.request(r)
            data = await resp.json()
            gateway_url = data["url"]
        self.gateway_url = gateway_url
        try:
            self.ws = await self.client.http.create_ws(gateway_url, compression=0)
        except ClientConnectorError:
            await self.client.close()
            raise GatewayUnavailable() from None
        except TimeoutError:
            self.logger.debug("Gateway server is down, finding a new server.")
            await self.client.close()
            await self.connect()
            return
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
        self.connected.clear()
        self.is_ready.clear()

    async def read_loop(self):
        """
        Receives data from a gateway and sends it to a handler.
        """
        message: WSMessage  # Fix typehinting
        async for message in self.ws:
            if message.type == WSMsgType.TEXT:
                await self.client.gateway_handler.on_receive(message.json(loads=loads), self)
            elif message.type in [WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED]:
                self.logger.warning(
                    f"WebSocket is closing! Details: {message.json()}. Close code: {self.ws.close_code}")
            else:
                self.logger.warning("Unknown message type: " + str(type(message)))
        await self.on_disconnect(self.ws.close_code)

    async def send(self, data: dict):
        """
        Attempts to send a message via the gateway. Checks for the gateway ratelimit before doing so.
        """
        async with self.gateway_send_lock:
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

    async def on_disconnect(self, close_code: int):
        if close_code == 4000:
            # Unknown error
            self.logger.info("Gateway closed due to an unknown error.")
            await self.connect(self.gateway_url)
        elif close_code == 4001:
            # Unknown opcode
            self.logger.warning("An invalid opcode was sent to the gateway. Reconnecting!")
            await self.connect(self.gateway_url)
        elif close_code == 4002:
            self.logger.warning("An payload that couldn't be decoded by the gateway was sent to discord. Reconnecting!")
            await self.connect(self.gateway_url)
        elif close_code == 4003:
            await self.client.fatal(GatewayNotAuthenticated())
        elif close_code == 4004:
            await self.client.fatal(InvalidToken())
        elif close_code == 4005:
            self.logger.error("Already authenticated to the gateway. Reconnecting!")
            await self.connect(self.gateway_url)
        elif close_code == 4007:
            self.logger.warning("Invalid seq number, reconnecting with a new session!")
            self.session_id = None
            self.last_event_id = None
            await self.connect(self.gateway_url)
        elif close_code == 4008:
            self.logger.warning(
                "Library is sending too many payloads to the gateway! Please create a issue on the github repo")
            await self.connect(self.gateway_url)
        elif close_code == 4009:
            self.logger.info("A session timed out! Reconnecting with a new session.")
            self.session_id = None
            self.last_event_id = None
            await self.connect(self.gateway_url)
        elif close_code == 4010:
            if self.client.shard_count is not None:
                await self.client.fatal(InvalidShardCount())
                return
            self.logger.info("Forced to scale up guild count, expect downtime.")
            await self.client.close()
            for shard in self.client.shards:
                await shard.close()
            self.client.connected.clear()
            self.client.shards = []
            await self.client.connect()
            self.logger.info("Shard scale done.")
        elif close_code == 4012:
            await self.client.fatal(InvalidGatewayVersion())
        elif close_code == 4013:
            await self.client.fatal(InvalidIntentNumber())
        elif close_code == 4014:
            await self.client.fatal(IntentNotWhitelisted())
        else:
            self.logger.warning(f"Unknown close code received. Close code: {close_code}.")

    async def identify(self):
        """
        Sends an identify message to the gateway, which is the initial handshake.
        https://discord.com/developers/docs/topics/gateway#identify
        """
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
        """
        Sends a resume message to the gateway, which resumes any events stopped in
        case of some sort of a disconnect.
        https://discord.com/developers/docs/topics/gateway#resume
        """
        await self.send({
            "op": 6,
            "d": {
                "token": self.client.token,
                "session_id": self.session_id,
                "seq": self.last_event_id
            }
        })

    async def heartbeat_loop(self):
        """
        Sends a heartbeat_loop message to the gateway - used to keep the connection alive.
        https://discord.com/developers/docs/topics/gateway#heartbeat
        """
        await self.is_ready.wait()
        sess_id = self.session_id
        while self.connected.is_set() and self.session_id == sess_id:
            if not self.received_heartbeat_ack:
                self.failed_heartbeats += 1
                self.logger.info(
                    "WebSocket did not respond to a heartbeat! Failed attempts: " + str(self.failed_heartbeats))
                if self.failed_heartbeats > 2:
                    self.logger.warning("Gateway stopped responding, reconnecting!")
                    await self.close()
                    await self.connect()  # Don't cache gateway url here as the server is shutting down.
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
        self.is_ready.set()

    async def handle_invalid_session(self, data, shard):
        if shard.id != self.id:
            return
        if not data.get("d", False):
            # Session is no longer valid, create a new session
            self.session_id = None
            self.last_event_id = None
        await self.close()
        await self.connect(self.gateway_url)
