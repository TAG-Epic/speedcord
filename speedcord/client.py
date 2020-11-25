"""
Created by Epic at 9/1/20
"""
from asyncio import Event, get_event_loop, Lock, sleep
from logging import getLogger
from time import time

from .exceptions import Unauthorized, ConnectionsExceeded, InvalidToken
from .http import HttpClient, Route
from .dispatcher import OpcodeDispatcher, EventDispatcher
from .shard import DefaultShard
from .ratelimiter import TimesPer

__all__ = ("Client",)


class Client:
    def __init__(self, intents, token=None, *, shard_count=None, shard_ids=None):
        """
        The client to interact with the discord API
        :param intents: the intents to use
        :param token: the discord bot token to use
        :param shard_count: how many shards to use
        :param shard_ids: A list of shard ids to spawn. Shard_count must be set for this to work
        """
        # Configurable stuff
        self.intents = int(intents)
        self.token = token
        self.shard_count = shard_count
        self.shard_ids = shard_ids

        # Things used by the lib, usually doesn't need to get changed but can if you want to.
        self.shards = []
        self.loop = get_event_loop()
        self.logger = getLogger("speedcord")
        self.http = None
        self.opcode_dispatcher = OpcodeDispatcher(self.loop)
        self.event_dispatcher = EventDispatcher(self.loop)
        self.connected = Event()
        self.exit_event = Event(loop=self.loop)
        self.remaining_connections = None
        self.connection_lock = Lock(loop=self.loop)
        self.fatal_exception = None
        self.connect_ratelimiter = None
        self.current_shard_count = None

        # Default event handlers
        self.opcode_dispatcher.register(0, self.handle_dispatch)

        # Check types
        if shard_count is None and shard_ids is not None:
            raise TypeError("You have to set shard_count if you use shard_ids")

    def run(self):
        """
        Starts the client
        """
        try:
            self.loop.run_until_complete(self.start())
        except KeyboardInterrupt:
            self.loop.run_until_complete(self.close())
        if self.fatal_exception is not None:
            raise self.fatal_exception from None

    async def get_gateway(self):
        """
        Get details about the gateway
        :return: wss url to connect to
        :return: how many shards to use
        :return: how many gateway connections left
        :return: how many ms until the gateway connection limit resets
        """
        route = Route("GET", "/gateway/bot")
        try:
            r = await self.http.request(route)
        except Unauthorized:
            await self.close()
            raise
        data = await r.json()

        shards = data["shards"]
        remaining_connections = data["session_start_limit"]["remaining"]
        connections_reset_after = data["session_start_limit"]["reset_after"]
        max_concurrency = data["session_start_limit"]["max_concurrency"]
        gateway_url = data["url"]

        if remaining_connections == 0:
            raise ConnectionsExceeded
        self.remaining_connections = remaining_connections
        self.logger.debug(f"{remaining_connections} gateway connections left!")
        return gateway_url, shards, remaining_connections, connections_reset_after, max_concurrency

    async def connect(self):
        """
        Connects to discord and spawns shards. Start has to be called first!
        """
        if self.token is None:
            raise InvalidToken
        if self.http is None:
            self.http = HttpClient(self.token, loop=self.loop)
        await self.spawn_shards(self.shards, shard_ids=self.shard_ids)
        self.connected.set()
        self.logger.info("All shards connected!")

    async def start(self):
        """
        Sets up the http client and connects to discord and spawns shards.
        """
        if self.token is None:
            raise InvalidToken
        self.http = HttpClient(self.token, loop=self.loop)

        await self.connect()

        await self.exit_event.wait()
        await self.close()

    async def close(self):
        """
        Closes the http client and disconnects all shards
        """
        self.connected.clear()
        self.exit_event.set()
        await self.http.close()
        for shard in self.shards:
            await shard.close()

    async def fatal(self, exception):
        """
        Raises a fatal exception to the bot.
        Please do not use this for non-fatal exceptions.
        """
        self.fatal_exception = exception
        await self.close()

    async def spawn_shards(self, shard_list, *, activate_automatically=True, shard_ids=None):
        try:
            gateway_url, shard_count, connections_left,\
                connections_reset_after, max_concurrency = await self.get_gateway()
        except Unauthorized as e:
            await self.fatal(e)
            return
        if self.connect_ratelimiter is None:
            self.connect_ratelimiter = TimesPer(max_concurrency, 5)
        self.current_shard_count = self.shard_count or shard_count
        if shard_ids is None:
            shard_ids = range(shard_count)
        async with self.connection_lock:
            for shard_id in shard_ids:
                connections_left -= 1
                if connections_left <= 1:
                    sleep_time = (connections_reset_after / 1000) - time()
                    if sleep_time > 0:
                        self.logger.warning("You have used up all your gateway IDENTIFYs. Sleeping until it resets.")
                        await sleep(connections_reset_after - time())
                    try:
                        gateway_url, shard_count, connections_left,\
                            connections_reset_after, max_concurrency = await self.get_gateway()
                    except Unauthorized as e:
                        await self.fatal(e)
                        return
                await self.connect_ratelimiter.trigger()
                self.logger.info(f"Launching shard {shard_id}")
                shard = DefaultShard(shard_id, self, loop=self.loop)
                if not activate_automatically:
                    shard.active = False
                else:
                    shard.active = True
                await shard.connect(gateway_url)
                shard_list.append(shard)
            self.remaining_connections = connections_left

    def listen(self, event):
        """
        Listen to a event or a opcode.
        :param event: a opcode or event name to listen to
        """

        def get_func(func):
            if isinstance(event, int):
                self.opcode_dispatcher.register(event, func)
            elif isinstance(event, str):
                self.event_dispatcher.register(event, func)
            else:
                raise TypeError("Invalid event type!")

        return get_func

    # Handle events
    async def handle_dispatch(self, data, shard):
        """
        Dispatches a event to the event handler
        :param data: the data to dispatch
        :param shard: What shard was the event received on
        """
        self.event_dispatcher.dispatch(data["t"], data["d"], shard)
