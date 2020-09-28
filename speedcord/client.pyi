from typing import List, Optional, Union
from asyncio import AbstractEventLoop
from logging import Logger
from asyncio import Event, Lock

from .shard import DefaultShard
from .http import HttpClient
from .dispatcher import EventDispatcher, OpcodeDispatcher
from .gateway import DefaultGatewayHandler


class Client:
    ...
    intents: int
    token: str
    shard_count: int
    shard_ids: List[int]

    shards: List[DefaultShard]
    loop: AbstractEventLoop
    logger: Logger
    http: HttpClient
    opcode_dispatcher: OpcodeDispatcher
    event_dispatcher: EventDispatcher
    gateway_handler: DefaultGatewayHandler
    connected: Event
    exit_event: Event
    remaining_connections: Optional[int]
    connection_lock: Lock

    def __init__(self, intents: int, token: Optional[str] = None, *, shard_count: Optional[int] = None, shard_ids: Optional[List[int]] = None):
        ...
    def run(self):
        ...
    async def get_gateway(self) -> (str, int, int, int):
        ...

    async def connect(self):
        ...
    async def start(self):
        ...
    async def close(self):
        ...

    def listen(self, event: Union[str, int]):
        ...

    async def handle_dispatch(self, data: dict, shard: DefaultShard):
        ...
