"""
Created by Epic at 9/1/20
"""
import asyncio
import logging
from aiohttp import ClientWebSocketResponse, WSMessage, WSMsgType

from . import exceptions, packets, wsratelimits
from .http import HttpClient, Route
from .dispatcher import DefaultDispatcher
from .gateway import DefaultGatewayHandler

__all__ = ("Client",)


class Client:
    def __init__(self, intents: int, token=None):
        self.intents = int(intents)
        self.token = token

        self.loop = asyncio.get_event_loop()
        self.logger = logging.getLogger("speedcord")
        self.ws: ClientWebSocketResponse = None
        self.http: HttpClient = None
        self.dispatcher = DefaultDispatcher(self.loop)
        self.gateway_handler = DefaultGatewayHandler(self)
        self.connected = asyncio.Event()

        self.error_exit_event = asyncio.Event(loop=self.loop)

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

        gateway_url = await self.get_gateway_url()

        self.ws = await self.http.create_ws(gateway_url, compression=0)
        self.connected.set()

        # Connect to the WS
        await self.send(packets.identify(self.token, intents=self.intents, mobile_status=True))

    async def start(self):
        if self.token is None:
            raise exceptions.InvalidToken
        self.http = HttpClient(self.token, loop=self.loop)

        await self.connect()

        self.loop.create_task(self.read_loop())

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

    async def send(self, data: dict):
        if self.ws.closed:
            raise exceptions.GatewayClosed
        await wsratelimits.send_ws(self.ws, data)

    async def close(self):
        await self.http.close()
        if self.ws is not None and not self.ws.closed:
            await self.ws.close()
