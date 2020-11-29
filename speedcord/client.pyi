from typing import List, Optional, Union, Tuple, Callable, Any
from asyncio import AbstractEventLoop, Event, Lock
from logging import Logger

from .shard import DefaultShard
from .http import HttpClient
from .dispatcher import EventDispatcher, OpcodeDispatcher
from .ratelimiter import TimesPer


class Client:
    intents: int
    token: str
    shard_count: int
    shard_ids: List[int]

    shards: List[DefaultShard]
    loop: AbstractEventLoop
    logger: Logger
    http: Optional[HttpClient]
    opcode_dispatcher: OpcodeDispatcher
    event_dispatcher: EventDispatcher
    connected: Event
    exit_event: Event
    remaining_connections: Optional[int]
    connection_lock: Lock
    fatal_exception: Optional[Exception]
    connect_ratelimiter: Optional[TimesPer]
    current_shard_count: Optional[int]

    def __init__(self, intents: int, token: Optional[str] = None, *, shard_count: Optional[int] = None,
                 shard_ids: Optional[List[int]] = None):
        ...

    def run(self):
        ...

    async def get_gateway(self) -> Tuple[str, int, int, int, int]:
        ...

    async def connect(self):
        ...

    async def start(self):
        ...

    async def close(self):
        ...

    async def fatal(self, exception: Optional[Exception]):
        ...

    async def spawn_shards(self, shard_list: list, *, activate_automatically: bool = True, shard_ids: Optional[List] = None):
        ...

    def listen(self, event: Union[str, int]) -> Callable[[Callable[[dict, DefaultShard], Any]], Any]:
        ...

    async def handle_dispatch(self, data: dict, shard: DefaultShard):
        ...
