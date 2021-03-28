"""
Created by Epic at 9/1/20
Inspiration taken from discord.py
"""

from aiohttp import ClientSession, __version__ as aiohttp_version, ClientWebSocketResponse
import asyncio
import logging
from sys import version_info as python_version
from urllib.parse import quote as uriquote

from .values import version as speedcord_version
from .exceptions import Forbidden, NotFound, HTTPException, Unauthorized

__all__ = ("Route", "HttpClient")


class Route:
    """
    Describes an API route. Used by HttpClient to send requests. For a list of routes and their parameters,
    refer to https://discord.com/developers/docs/reference.
    Parameters
    ----------
    method: str
        Standard HTTPS method.
    route: str
        Discord API route.
    parameters: Dict[str, Any]
        Parameters to send with the request.
    """
    def __init__(self, method, route, **parameters):
        self.method = method
        self.path = route.format(**parameters)

        # Used for bucket cooldowns
        self.channel_id = parameters.get("channel_id")
        self.guild_id = parameters.get("guild_id")

    @property
    def bucket(self):
        """
        The Route's bucket identifier.
        """
        return f"{self.channel_id}:{self.guild_id}:{self.path}"


class LockManager:
    def __init__(self, lock: asyncio.Lock):
        """
        Used by HttpClient to handle rate limits. Locked when a Bucket's rate limit has been
        hit, which prevents additional requests from being executed.
        :param lock: An asyncio.Lock object. Usually something like asyncio.Lock(loop=some_loop)
        """
        self.lock = lock
        self.unlock = True

    def __enter__(self):
        return self

    def defer(self):
        """
        Stops the lock from being automatically being unlocked when it ends
        """
        self.unlock = False

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.unlock:
            self.lock.release()


class HttpClient:
    """
    An HTTP client that handles Discord rate limits.

    Parameters
    ----------
    token: str
        A Discord bot token. To create a bot - https://discordpy.readthedocs.io/en/latest/discord.html
    **baseuri: str
        Discord's API URI.
    **loop: AbstractEventLoop
        An event loop to use for callbacks.
    """
    def __init__(self, token, *, baseuri="https://discord.com/api/v8", loop=asyncio.get_event_loop()):
        self.baseuri = baseuri
        self.token = token
        self.loop = loop
        self.session = ClientSession()
        self.logger = logging.getLogger("speedcord.http")

        self.ratelimit_locks = {}
        self.global_lock = asyncio.Event(loop=self.loop)

        # Clear the global lock on start
        self.global_lock.set()

        self.default_headers = {
            "X-RateLimit-Precision": "millisecond",
            "Authorization": f"Bot {self.token}",
            "User-Agent": f"DiscordBot (https://github.com/TAG-Epic/speedcord {speedcord_version}) "
                          f"Python/{python_version[0]}.{python_version[1]} "
                          f"aiohttp/{aiohttp_version}"
        }

        self.retry_attempts = 3

    async def create_ws(self, url, *, compression) -> ClientWebSocketResponse:
        """
        Opens a websocket to the specified url.

        Parameters
        ----------
        url: str
            The URL that the websocket will connect to.
        compression: int
            Whether to enable compression.
        """
        if self.session.closed:
            self.session = ClientSession()
        options = {
            "max_msg_size": 0,
            "timeout": 60,
            "autoclose": False,
            "headers": {
                "User-Agent": self.default_headers["User-Agent"]
            },
            "compress": compression
        }
        return await self.session.ws_connect(url, **options)

    async def request(self, route: Route, **kwargs):
        """
        Sends a request to the Discord API.

        Parameters
        ----------
        route: Route
            The Discord API route to send a request to.
        **kwargs: Dict[str, Any]
            The parameters being passed to asyncio.ClientSession.request
        """
        if self.session.closed:
            self.session = ClientSession()
        bucket = route.bucket

        for retry_count in range(self.retry_attempts):
            if not self.global_lock.is_set():
                self.logger.debug("Sleeping for global rate-limit")
                await self.global_lock.wait()

            ratelimit_lock: asyncio.Lock = self.ratelimit_locks.get(bucket, None)
            if ratelimit_lock is None:
                self.ratelimit_locks[bucket] = asyncio.Lock()
                continue

            await ratelimit_lock.acquire()
            with LockManager(ratelimit_lock) as lockmanager:
                # Merge default headers with the users headers, could probably use a if to check if is headers set?
                # Not sure which is optimal for speed
                kwargs["headers"] = {**self.default_headers, **kwargs.get("headers", {})}

                # Format the reason
                try:
                    reason = kwargs.pop("reason")
                except KeyError:
                    pass
                else:
                    if reason:
                        kwargs["headers"]["X-Audit-Log-Reason"] = uriquote(reason, safe="/ ")
                r = await self.session.request(route.method, self.baseuri + route.path, **kwargs)
                headers = r.headers

                if r.status == 429:
                    data = await r.json()
                    retry_after = data["retry_after"]
                    if "X-RateLimit-Global" in headers.keys():
                        # Global rate-limited
                        self.global_lock.set()
                        self.logger.warning(
                            "Global rate-limit reached! Please contact discord support to get this increased. "
                            "Trying again in %s Request attempt %s" % (retry_after, retry_count))
                        await asyncio.sleep(retry_after)
                        self.global_lock.clear()
                        self.logger.debug("Trying request again. Request attempt: %s" % retry_count)
                        continue
                    else:
                        self.logger.info("Ratelimit bucket hit! Bucket: %s. Retrying in %s. Request count %s" % (
                            bucket, retry_after, retry_count))
                        await asyncio.sleep(retry_after)
                        self.logger.debug("Trying request again. Request attempt: %s" % retry_count)
                        continue
                elif r.status == 401:
                    raise Unauthorized(r)
                elif r.status == 403:
                    raise Forbidden(r, await r.text())
                elif r.status == 404:
                    raise NotFound(r)
                elif r.status >= 300:
                    raise HTTPException(r, await r.text())

                # Check if we are just on the limit but not passed it
                remaining = r.headers.get('X-Ratelimit-Remaining')
                if remaining == "0":
                    retry_after = float(headers.get("X-RateLimit-Reset-After", "0"))
                    self.logger.info("Rate-limit exceeded! Bucket: %s Retry after: %s" % (bucket, retry_after))
                    lockmanager.defer()
                    self.loop.call_later(retry_after, ratelimit_lock.release)

                return r

    async def close(self):
        await self.session.close()
