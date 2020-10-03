"""
Created by Epic at 9/1/20
"""

from asyncio import AbstractEventLoop
import logging

__all__ = ("OpcodeDispatcher", "EventDispatcher")


class OpcodeDispatcher:
    def __init__(self, loop: AbstractEventLoop):
        """
        Receives events identified by their opcode, and handles them by running them through the event loop.
        :param loop: an AbstractEventLoop which is used to create callbacks.
        """
        self.logger = logging.getLogger("speedcord.dispatcher")
        self.loop = loop

        # A dict of the opcode int and a list of coroutines to execute once a event is sent
        self.event_handlers = {}

    def dispatch(self, opcode, *args, **kwargs):
        """
        Dispatches an event to listeners registered to this opcode.
        :param opcode: The opcode of the event sent by Discord API.
        """
        self.logger.debug("Dispatching event with opcode: " + str(opcode))
        for event in self.event_handlers.get(opcode, []):
            self.loop.create_task(event(*args, **kwargs))

    def register(self, opcode, func):
        """
        Register a handler for a specific opcode. This handler will be called whenever a matching opcode is dispatched.
        :param opcode: : The opcode from discord to listen to.
        :param func: The function that will be called when the event is dispatched.
        """
        event_handlers = self.event_handlers.get(opcode, [])
        event_handlers.append(func)
        self.event_handlers[opcode] = event_handlers


class EventDispatcher:
    def __init__(self, loop: AbstractEventLoop):
        """
        Receives events identified by their name and handles them by running them
        through the event loop.
        :param loop: an AbstractEventLoop which is used to create callbacks.
        """
        self.logger = logging.getLogger("speedcord.dispatcher")
        self.loop = loop

        # A dict of the event name and a list of coroutines to execute once a event is sent
        self.event_handlers = {}

    def dispatch(self, event_name, *args, **kwargs):
        """
        Dispatches an event to listeners registered to this event_name.
        :param event_name: The name of the event sent by Discord API.
        """
        self.logger.debug("Dispatching event with name: " + str(event_name))
        for event in self.event_handlers.get(event_name, []):
            self.loop.create_task(event(*args, **kwargs))

    def register(self, event_name, func):
        """
        Register a handler for a specific event. This handler will be called whenever an
        event matching the registered event_name is dispatched.
        :param event_name: The event name from discord to listen to.
        :param func: The function that will be called when the event is dispatched.
        """
        event_name = event_name.upper()
        event_handlers = self.event_handlers.get(event_name, [])
        event_handlers.append(func)
        self.event_handlers[event_name] = event_handlers
