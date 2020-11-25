"""
Created by Epic at 9/5/20
"""
from .exceptions import GatewayUnavailable, GatewayNotAuthenticated, InvalidToken, \
    InvalidGatewayVersion, IntentNotWhitelisted, InvalidIntentNumber
from .http import Route
from .ratelimiter import TimesPer

from asyncio import Event, AbstractEventLoop, sleep
from asyncio.exceptions import TimeoutError
from aiohttp.client_exceptions import ClientConnectorError
from aiohttp import WSMessage, WSMsgType
from logging import getLogger
from sys import platform
from ujson import loads, dumps


class DefaultShard:
    def __init__(self, shard_id, client, loop: AbstractEventLoop):
        """
        Handles all Discord Shard related events. For more information on what sharding is and how it works:
        https://discord.com/developers/docs/topics/gateway#sharding.
        This simply represents a Discord Shard. The actual handling of events happens via the client's handlers.
        :param shard_id: The id for the shard.
        :param client: A speedcord.Client object which will manage the shards.
        :param loop: an AbstractEventLoop which is used to create callbacks.
        """
        self.id = shard_id
        self.client = client
        self.loop = loop

        self.ws = None
        self.gateway_url = None
        self.logger = getLogger(f"speedcord.shard.{self.id}")
        self.connected = Event(loop=self.loop)  # Some bots might wanna know which shards is online at all times

        self.received_heartbeat_ack = True
        self.heartbeat_interval = None
        self.heartbeat_count = None
        self.failed_heartbeats = 0
        self.session_id = None
        self.last_event_id = None  # This gets modified by gateway.py
        self.is_closing = False
        self.is_initial_connect = True
        self.active = True

        self.send_ratelimiter = TimesPer(120, 60)

        self.is_ready = Event(loop=self.loop)
        self.active = False  # Will only handle core events

        # Default events
        self.client.opcode_dispatcher.register(10, self.handle_hello)
        self.client.opcode_dispatcher.register(11, self.handle_heartbeat_ack)
        self.client.opcode_dispatcher.register(9, self.handle_invalid_session)

        self.client.event_dispatcher.register("READY", self.handle_ready)

    async def connect(self, gateway_url=None):
        """
        Connects to the gateway. Usually done by the client.
        :param gateway_url: The gateway url.
        """
        await self.close()
        if gateway_url is None:
            r = Route("GET", "/gateway")
            resp = await self.client.http.request(r)
            data = await resp.json()
            gateway_url = data["url"]
        self.gateway_url = gateway_url
        try:
            self.ws = await self.client.http.create_ws(gateway_url, compression=0)
        except ClientConnectorError:
            await self.client.close()
            raise GatewayUnavailable() from None
        except TimeoutError:
            self.logger.debug("Gateway server is down, finding a new server.")
            await self.client.close()
            await self.connect()
            return
        self.loop.create_task(self.read_loop())
        self.connected.set()
        if not self.is_initial_connect:
            if self.session_id is None:
                async with self.client.connection_lock:
                    self.client.remaining_connections -= 1
                    if self.client.remaining_connections <= 1:
                        self.logger.info("Max connections reached!")
                        gateway_url, shard_count, connections_left, \
                        connections_reset_after, max_concurrency = await self.client.get_gateway()
                        await sleep(connections_reset_after / 1000)
                        gateway_url, shard_count, connections_left, \
                        connections_reset_after, max_concurrency = await self.client.get_gateway()
                        self.client.remaining_connections = connections_left
                    await self.identify()
                    return
            else:
                await self.resume()
        await self.identify()

    async def close(self):
        if self.ws is not None and not self.ws.closed:
            self.is_closing = True
            await self.ws.close()
            self.is_closing = False
        self.connected.clear()
        self.is_ready.clear()

    async def read_loop(self):
        """
        Receives data from a gateway and sends it to a handler.
        """
        message: WSMessage  # Fix typehinting
        async for message in self.ws:
            if message.type == WSMsgType.TEXT:
                data = message.json(loads=loads)
                if "s" in data.keys() and data["s"] is not None:
                    self.last_event_id = data["s"]
                self.logger.debug(f"Data received ({('inactive', 'active')[self.active]} mode): " + str(data))
                if self.active:
                    self.client.opcode_dispatcher.dispatch(data["op"], data, self)
                else:
                    self.loop.create_task(self.handle_dispatch(data))
            elif message.type in [WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED]:
                self.logger.warning(
                    f"WebSocket is closing! Details: {message.json()}. Close code: {self.ws.close_code}")
            else:
                self.logger.warning("Unknown message type: " + str(type(message)))
        await self.on_disconnect(self.ws.close_code)

    async def send(self, data: dict):
        """
        Attempts to send a message via the gateway. Checks for the gateway ratelimit before doing so.
        """
        self.logger.debug("Sending data...")
        await self.send_ratelimiter.trigger()
        self.logger.debug("Data sent: " + str(data))
        await self.ws.send_json(data, dumps=dumps)

    async def rescale_shards(self):
        if self.client.shard_ids is not None:
            return
        self.logger.info("Rescaling shards. Shard will be down until all shards are up.")
        new_shards = []
        await self.client.spawn_shards(new_shards, activate_automatically=False)
        for shard in self.client.shards:
            await shard.close()
        for shard in new_shards:
            shard.active = True
        self.client.shards = new_shards

    async def on_disconnect(self, close_code: int):
        # close_code: (action, action_data, save_session, save_gateway_url)
        handlers = {
            4000: ("INFO", "Gateway closed due to an unknown error. ", True, True),
            4001: ("WARN", "An invalid opcode was sent to the gateway. ", True, True),
            4002: ("WARN", "An payload that couldn't be decoded by the gateway was sent to discord. ", True, True),
            4003: ("FATAL", GatewayNotAuthenticated, False, False),
            4004: ("FATAL", InvalidToken, False, False),
            4005: ("WARN", "Already authenticated to the gateway. ", True, True),
            4007: ("WARN", "Invalid seq number. ", False, True),
            4008: ("WARN", "We are sending too many payloads to the gateway! Please create a issue on the github. ",
                   False, False),
            4009: ("WARN", "A session timed out! Reconnecting with a new session. ", False, True),
            4010: ("FUNC", self.rescale_shards, True, True),
            4012: ("FATAL", InvalidGatewayVersion, False, False),
            4013: ("FATAL", InvalidIntentNumber, False, False),
            4014: ("FATAL", IntentNotWhitelisted, False, False),
            None: ("WARN", f"Unknown close code received. Close code: {close_code}. ", True, True)
        }
        if self.is_closing:
            return

        handler = handlers.get(close_code, handlers[None])
        action, action_data, save_session, save_gateway_url = handler
        if action == "FATAL":
            await self.client.fatal(action_data())
            return
        elif action in ["INFO", "WARN"]:
            log_string = action_data
            log_string += "Reconnecting "
            if not save_session and save_gateway_url:
                self.session_id = None
                self.last_event_id = None
                log_string += "with a new session"
            elif not save_session and not save_gateway_url:
                self.session_id = None
                self.last_event_id = None
                self.gateway_url = None
                log_string += "with a new session and gateway endpoint"
            elif save_session and not save_gateway_url:
                log_string += "with a new gateway endpoint"
            log_string += "."

            if action == "INFO":
                self.logger.info(log_string)
            else:
                self.logger.warning(log_string)
            await self.connect(self.gateway_url)
        elif action == "FUNC":
            self.logger.debug(close_code)
            await action_data()

    async def identify(self):
        """
        Sends an identify message to the gateway, which is the initial handshake.
        https://discord.com/developers/docs/topics/gateway#identify
        """
        self.logger.debug("Identifying..")
        await self.send({
            "op": 2,
            "d": {
                "token": self.client.token,
                "properties": {
                    "$os": platform,
                    "$browser": "SpeedCord",
                    "$device": "SpeedCord"
                },
                "intents": self.client.intents,
                "shard": (self.id, self.client.current_shard_count)
            }
        })

    async def resume(self):
        """
        Sends a resume message to the gateway, which resumes any events stopped in
        case of some sort of a disconnect.
        https://discord.com/developers/docs/topics/gateway#resume
        """
        await self.send({
            "op": 6,
            "d": {
                "token": self.client.token,
                "session_id": self.session_id,
                "seq": self.last_event_id
            }
        })

    async def heartbeat_loop(self):
        """
        Sends a heartbeat_loop message to the gateway - used to keep the connection alive.
        https://discord.com/developers/docs/topics/gateway#heartbeat
        """
        await self.is_ready.wait()
        sess_id = self.session_id
        while self.connected.is_set() and self.session_id == sess_id:
            if not self.received_heartbeat_ack:
                self.failed_heartbeats += 1
                self.logger.info(
                    "WebSocket did not respond to a heartbeat! Failed attempts: " + str(self.failed_heartbeats))
                if self.failed_heartbeats > 2:
                    self.logger.warning("Gateway stopped responding, reconnecting!")
                    await self.close()
                    await self.connect()  # Don't cache gateway url here as the server is shutting down.
                    return
            self.received_heartbeat_ack = False
            await self.send({
                "op": 1,
                "d": self.heartbeat_count
            })
            if self.heartbeat_count is not None:
                self.heartbeat_count += 1
            else:
                self.heartbeat_count = 0
            await sleep(self.heartbeat_interval)

    async def handle_dispatch(self, data):
        handlers = {
            9: self.handle_invalid_session,
            10: self.handle_hello,
            11: self.handle_heartbeat_ack
        }
        if "t" not in data.keys():
            return
        if data["t"] is None:
            event_handler = handlers.get(data["op"])
            if event_handler is None:
                return
            await event_handler(data, self)
        else:
            event_handler = getattr(self, "handle_" + data["t"].lower(), None)
            if event_handler is None:
                return
            await event_handler(data["d"], self)

    async def handle_hello(self, data, shard):
        if shard.id != self.id:
            return
        self.received_heartbeat_ack = True
        self.heartbeat_interval = data["d"]["heartbeat_interval"] / 1000
        self.loop.create_task(self.heartbeat_loop())
        self.logger.debug("Started heartbeat loop")

    async def handle_heartbeat_ack(self, data, shard):
        if shard.id != self.id:
            return
        self.received_heartbeat_ack = True
        self.failed_heartbeats = 0
        self.logger.debug("Received heartbeat successfully!")

    async def handle_ready(self, data, shard):
        if shard.id != self.id:
            return
        self.session_id = data["session_id"]
        self.is_ready.set()

    async def handle_invalid_session(self, data, shard):
        if shard.id != self.id:
            return
        if not data.get("d", False):
            # Session is no longer valid, create a new session
            self.session_id = None
            self.last_event_id = None
        await self.close()
        await self.connect(self.gateway_url)
