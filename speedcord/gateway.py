"""
Created by Epic at 9/2/20
"""
from logging import getLogger


class DefaultGatewayHandler:
    """
    A default handler for opcode events.

    Parameters
    ----------
    client: speedcord.Client
        A speedcord.Client object to connect the gateway handler to.
    """

    def __init__(self, client):
        self.client = client
        self.logger = getLogger("speedcord.gateway")

    async def on_receive(self, data, shard):
        """
        Function that's called whenever an event is called on a shard.

        Parameters
        ----------
        data: Dict[str, Any]
            Data sent by Discord gateway.
        shard: DefaultShard
            Shard to process the data on.
        """
        self.logger.debug("Data received: " + str(data))
        self.client.opcode_dispatcher.dispatch(data["op"], data, shard)
        if "s" in data.keys() and data["s"] is not None:
            shard.last_event_id = data["s"]
