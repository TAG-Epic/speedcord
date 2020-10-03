from typing import Optional, Type, Dict, Any
from types import TracebackType
from asyncio import AbstractEventLoop, Lock, Event
from logging import Logger

from aiohttp import ClientWebSocketResponse, ClientResponse, ClientSession


class Route:
    method: str
    path: str
    channel_id: Optional[int]
    guild_id: Optional[int]

    def __init__(self, method: str, route: str, **parameters: Any):
        ...

    @property
    def bucket(self) -> str:
        ...


class LockManager:
    lock: Lock
    unlock: bool

    def __init__(self, lock: Lock):
        ...

    def __enter__(self) -> 'LockManager':
        ...

    def defer(self):
        ...

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException],
                 exc_tb: Optional[TracebackType]):
        ...


class HttpClient:
    baseuri: str
    token: str
    loop: AbstractEventLoop
    session: ClientSession
    logger: Logger
    ratelimit_locks: Dict[str, Lock]
    global_lock: Event
    default_headers: Dict[str, str]
    retry_attempts: int

    def __init__(self, token: str, *, baseuri: str = None, loop: AbstractEventLoop = None):
        ...

    async def create_ws(self, url: str, *, compression: int) -> ClientWebSocketResponse:
        ...

    async def request(self, route: Route, **kwargs: Any) -> ClientResponse:
        ...

    async def close(self):
        ...
