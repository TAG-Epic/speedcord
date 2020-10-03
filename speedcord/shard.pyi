from typing import Optional
from speedcord import Client
from asyncio import AbstractEventLoop, Lock, Event
from logging import Logger

from aiohttp import ClientWebSocketResponse


class DefaultShard:
    id: int
    client: Client
    loop: AbstractEventLoop
    ws: Optional[ClientWebSocketResponse]
    gateway_url: Optional[str]
    logger: Logger
    connected: Event

    received_heartbeat_ack: bool
    heartbeat_interval: Optional[int]
    heartbeat_count: Optional[int]
    failed_heartbeats: int
    session_id: Optional[str]
    last_event_id: Optional[int]

    gateway_send_lock: Lock
    gateway_send_limit: int
    gateway_send_per: int
    gateway_send_left: int
    gateway_send_reset: float

    def __init__(self, shard_id: int, client: Client, loop: AbstractEventLoop):
        ...

    async def connect(self, gateway_url: str):
        ...

    async def close(self):
        ...

    async def read_loop(self):
        ...

    async def send(self, data: dict):
        ...

    async def identify(self):
        ...

    async def resume(self):
        ...

    async def heartbeat_loop(self):
        ...

    async def handle_hello(self, data: dict, shard: 'DefaultShard'):
        ...

    async def handle_heartbeat_ack(self, data: dict, shard: 'DefaultShard'):
        ...

    async def handle_ready(self, data: dict, shard: 'DefaultShard'):
        ...

    async def handle_invalid_session(self, data: dict, shard: 'DefaultShard'):
        ...
