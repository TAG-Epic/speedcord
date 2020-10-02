from speedcord import Client
from logging import Logger

from .shard import DefaultShard


class DefaultGatewayHandler:
    client: Client
    logger: Logger

    def __init__(self, client: Client):
        ...

    async def on_receive(self, data: dict, shard: DefaultShard):
        ...
