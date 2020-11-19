"""
Created by Epic at 9/1/20
"""
from asyncio import Event, get_event_loop, Lock
from logging import getLogger

from .exceptions import Unauthorized, ConnectionsExceeded, InvalidToken
from .http import HttpClient, Route
from .dispatcher import OpcodeDispatcher, EventDispatcher
from .gateway import DefaultGatewayHandler
from .shard import DefaultShard

__all__ = ("Client",)


class Client:
    def __init__(self, intents, token=None, *, shard_count=None, shard_ids=None):
        """
        The client used to interact with the discord API.

        Parameters
        ----------
        intents: int
            The intents to use.
        token: Optional[str]
            Discord bot token to use.
        shard_count: Optional[int]
            How many shards the client should use.
        shard_ids: Optional[List[int]]
            A list of shard IDs to spawn. ``shard_count`` must be set for this
            to work.

        Raises
        ------
        TypeError
            ``shard_ids`` was set without ``shard_count``.
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
        self.gateway_handler = DefaultGatewayHandler(self)
        self.connected = Event()
        self.exit_event = Event(loop=self.loop)
        self.remaining_connections = None
        self.connection_lock = Lock(loop=self.loop)
        self.fatal_exception = None

        # Default event handlers
        self.opcode_dispatcher.register(0, self.handle_dispatch)

        # Check types
        if shard_count is None and shard_ids is not None:
            raise TypeError("You have to set shard_count if you use shard_ids")

    def run(self):
        """
        Starts the client.
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

        Returns
        -------
        Tuple[str, int, int, int]
            A tuple consisting of the wss url to connect to, how many shards
            to use, how many gateway connections left, how many milliseconds
            until the gateway connection limit resets.

        Raises
        ------
        Unauthorized
            Authentication failed.
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
        gateway_url = data["url"]

        if remaining_connections == 0:
            raise ConnectionsExceeded
        self.remaining_connections = remaining_connections
        self.logger.debug(f"{remaining_connections} gateway connections left!")

        return gateway_url, shards, remaining_connections, connections_reset_after

    async def connect(self):
        """
        Connects to discord and spawns shards. :meth:`start()` has to be called first!

        Raises
        ------
        InvalidToken
            Provided token is invalid.
        """
        if self.token is None:
            raise InvalidToken

        try:
            gateway_url, shard_count, _, connections_reset_after = await self.get_gateway()
        except Unauthorized:
            self.exit_event.clear()
            raise InvalidToken

        if self.shard_count is None or self.shard_count < shard_count:
            self.shard_count = shard_count

        shard_ids = self.shard_ids or range(self.shard_count)
        for shard_id in shard_ids:
            self.logger.debug(f"Launching shard {shard_id}")
            shard = DefaultShard(shard_id, self, loop=self.loop)
            self.loop.create_task(shard.connect(gateway_url))
            self.shards.append(shard)
        self.connected.set()
        self.logger.info("All shards connected!")

    async def start(self):
        """
        Sets up the HTTP client, connects to Discord, and spawns shards.

        Raises
        ------
        InvalidToken
            Provided token is invalid.
        """
        if self.token is None:
            raise InvalidToken
        self.http = HttpClient(self.token, loop=self.loop)

        await self.connect()

        await self.exit_event.wait()
        await self.close()

    async def close(self):
        """
        Closes the HTTP client and disconnects all shards.
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

    def listen(self, event):
        """
        Listen to an event or opcode.

        Parameters
        ----------
        event: Union[int, str]
            An opcode or event name to listen to.

        Raises
        ------
        TypeError
            Invalid event type was passed.
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
        Dispatches a event to the event handler.

        Parameters
        ----------
        data: Dict[str, Any]
            The data to dispatch.
        shard: DefaultShard
            Shard the event was received on.
        """
        self.event_dispatcher.dispatch(data["t"], data["d"], shard)
