"""
Created by Epic at 9/1/20
"""

from asyncio import AbstractEventLoop
from inspect import iscoroutine
import logging


class DefaultDispatcher:
    def __init__(self, loop: AbstractEventLoop):
        self.logger = logging.getLogger("speedcord.dispatcher")
        self.loop = loop

        # A dict of the opcode int and a list of coroutines to execute once a event is sent
        self.event_handlers = {}

    def dispatch(self, opcode, *args, **kwargs):
        self.logger.debug("Dispatching event with opcode: " + str(opcode))
        for event in self.event_handlers.get(opcode, []):
            self.loop.create_task(event(*args, **kwargs))

    def register(self, opcode, func):
        if not iscoroutine(func):
            raise TypeError("func has to be a coroutine!")
        event_handlers = self.event_handlers.get(opcode, [])
        event_handlers.append(func)
        self.event_handlers[opcode] = event_handlers

