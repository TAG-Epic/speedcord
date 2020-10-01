from speedcord import Client
from asyncio import AbstractEventLoop, Lock, Event
from logging import Logger

from aiohttp import ClientWebSocketResponse


class DefaultShard:
    id: int
    client: Client
    loop: AbstractEventLoop
    ws: ClientWebSocketResponse
    gateway_url: str
    ws_ratelimiting_lock: Lock
    logger: Logger
    connected: Event
    received_heartbeat_ack: bool
    heartbeat_interval: int
    heartbeat_count: int
    failed_heartbeats: int
    session_id: str
    last_event_id: int

    def __init__(self, shard_id: int, client: Client, loop: AbstractEventLoop) -> None:
        ...

    async def connect(self, gateway_url: str) -> None:
        ...

    async def close(self) -> None:
        ...

    async def read_loop(self) -> None:
        ...

    async def send(self, data: dict) -> None:
        ...

    async def identify(self) -> None:
        ...

    async def resume(self) -> None:
        ...

    async def heartbeat_loop(self) -> None:
        ...

    async def handle_hello(self, data: dict, shard: int) -> None:
        ...

    async def handle_heartbeat_ack(self, data: dict, shard: 'DefaultShard') -> None:
        ...

    async def handle_ready(self, data: dict, shard: 'DefaultShard') -> None:
        ...

    async def handle_invalid_session(self, data: dict, shard: 'DefaultShard') -> None:
        ...
