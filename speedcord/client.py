"""
Created by Epic at 9/1/20
"""
import asyncio
import logging
from aiohttp import ClientWebSocketResponse, WSMessage, WSMsgType

from . import exceptions, packets, wsratelimits
from .http import HttpClient, Route
from .dispatcher import OpcodeDispatcher, EventDispatcher
from .gateway import DefaultGatewayHandler

__all__ = ("Client",)


class Client:
    def __init__(self, intents: int, token=None, *, use_mobile_status=False):
        # Configurable stuff
        self.intents = int(intents)
        self.token = token
        self.use_mobile_status = use_mobile_status

        # Things used by the lib, usually doesn't need to get changed but can if you want to.
        self.loop = asyncio.get_event_loop()
        self.logger = logging.getLogger("speedcord")
        self.ws: ClientWebSocketResponse = None
        self.http: HttpClient = None
        self.opcode_dispatcher = OpcodeDispatcher(self.loop)
        self.event_dispatcher = EventDispatcher(self.loop)
        self.gateway_handler = DefaultGatewayHandler(self)
        self.connected = asyncio.Event()
        self.heartbeat_interval = None
        self.heartbeat_count = None
        self.received_heartbeat_ack = True
        self.error_exit_event = asyncio.Event(loop=self.loop)
        self.session_id = None
        self.last_event_received = None

        # Default event handlers
        self.opcode_dispatcher.register(10, self.handle_hello)
        self.opcode_dispatcher.register(11, self.handle_heartbeat_ack)
        self.opcode_dispatcher.register(0, self.handle_dispatch)
        self.opcode_dispatcher.register(9, self.handle_invalid_session)

        self.event_dispatcher.register("READY", self.handle_ready)

    def run(self):
        try:
            self.loop.run_until_complete(self.start())
        except KeyboardInterrupt:
            self.loop.run_until_complete(self.close())

    async def get_gateway_url(self):
        route = Route("GET", "/gateway/bot")
        try:
            r = await self.http.request(route)
        except exceptions.Unauthorized:
            await self.close()
            raise
        data = await r.json()

        shards = data["shards"]
        remaining_connections = data["session_start_limit"]["remaining"]
        gateway_url = data["url"]

        if shards != 1:
            raise exceptions.ShardingNotSupported
        if remaining_connections == 0:
            raise exceptions.ConnectionsExceeded

        self.logger.debug(f"{remaining_connections} gateway connections left!")

        return gateway_url

    async def connect(self):
        if self.token is None:
            raise exceptions.InvalidToken
        if self.ws is not None:
            if not self.ws.closed:
                await self.ws.close()
            self.ws = None

        try:
            gateway_url = await self.get_gateway_url()
        except exceptions.Unauthorized:
            self.error_exit_event.clear()
            raise exceptions.InvalidToken

        self.ws = await self.http.create_ws(gateway_url, compression=0)
        self.connected.set()

        # Start receiving events
        self.loop.create_task(self.read_loop())
        # Connect to the WS
        if self.session_id is None:
            await self.send(packets.identify(self.token, intents=self.intents, mobile_status=self.use_mobile_status))
        else:
            await self.send(
                packets.resume(self.token, session_id=self.session_id, last_event_received=self.last_event_received))

    async def start(self):
        if self.token is None:
            raise exceptions.InvalidToken
        self.http = HttpClient(self.token, loop=self.loop)

        await self.connect()

        await self.error_exit_event.wait()
        await self.close()

    async def read_loop(self):
        message: WSMessage  # Autocompletion fix
        async for message in self.ws:
            if message.type == WSMsgType.CLOSE:
                self.logger.critical(message.json())
                self.logger.critical(self.ws.close_code)
                self.error_exit_event.set()
            elif message.type == WSMsgType.TEXT:
                await self.gateway_handler.on_receive(message.json())

    async def heartbeat_loop(self):
        while True:
            if self.ws is None or self.ws.closed:
                return
            if not self.received_heartbeat_ack:
                self.logger.error("Gateway stopped responding to heartbeats, reconnecting!")
                await self.connect()
                return
            self.received_heartbeat_ack = False
            await self.send({
                "op": 1,
                "d": self.heartbeat_count
            })
            if self.heartbeat_count is None:
                self.heartbeat_count = 1
            else:
                self.heartbeat_count += 1
            await asyncio.sleep(self.heartbeat_interval)

    async def send(self, data: dict):
        if self.ws.closed:
            raise exceptions.GatewayClosed
        await wsratelimits.send_ws(self.ws, data)

    async def close(self):
        await self.http.close()
        if self.ws is not None and not self.ws.closed:
            await self.ws.close()

    # Handle events
    async def handle_hello(self, data):
        self.received_heartbeat_ack = True
        self.heartbeat_interval = data["d"]["heartbeat_interval"] / 1000
        self.loop.create_task(self.heartbeat_loop())
        self.logger.debug("Started heartbeat loop")

    async def handle_heartbeat_ack(self, data):
        self.received_heartbeat_ack = True
        self.logger.debug("Received heartbeat ack!")

    async def handle_dispatch(self, data):
        self.event_dispatcher.dispatch(data["t"], data["d"])

    async def handle_ready(self, data):
        self.session_id = data["session_id"]

    async def handle_invalid_session(self, data):
        if not data:
            self.logger.debug("Invalid session, reconnecting!")
            self.session_id = None
        await self.connect()
