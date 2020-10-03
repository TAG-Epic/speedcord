from typing import Callable, Dict, Any
from asyncio import AbstractEventLoop
from logging import Logger

from .shard import DefaultShard


class OpcodeDispatcher:
    logger: Logger
    loop: AbstractEventLoop

    event_handlers: Dict[int, Callable[[dict, DefaultShard], Any]]

    def __init__(self, loop: AbstractEventLoop):
        ...

    def dispatch(self, opcode: int, *args: Any, **kwargs: Any):
        ...

    def register(self, opcode: int, func: Callable[[dict, DefaultShard], Any]):
        ...


class EventDispatcher:
    logger: Logger
    loop: AbstractEventLoop

    event_handlers: Dict[str, Callable[[dict, DefaultShard], Any]]

    def __init__(self, loop: AbstractEventLoop):
        ...

    def dispatch(self, event_name: str, *args: Any, **kwargs: Any):
        ...

    def register(self, event_name: str, func: Callable[[dict, DefaultShard], Any]):
        ...
