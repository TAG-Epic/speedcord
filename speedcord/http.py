"""
Created by Epic at 9/1/20
Inspiration taken from discord.py
"""

import asyncio
import logging
from sys import version_info as python_version
from urllib.parse import quote as uriquote

from aiohttp import (ClientSession, ClientWebSocketResponse,
                     __version__ as aiohttp_version
                     )

from .exceptions import Forbidden, HTTPException, NotFound, Unauthorized
from .values import version as speedcord_version

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
    """
    Used by HttpClient to handle rate limits. Locked when a Bucket's rate limit has been hit, which prevents
    additional requests from being executed.

    Parameters
    ----------
    lock: asyncio.Lock
        An asyncio.Lock object. Usually something like ``asyncio.Lock(
        loop=some_loop)``.
    """

    def __init__(self, lock: asyncio.Lock):
        self.lock = lock
        self.unlock = True

    def __enter__(self):
        return self

    def defer(self):
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

    def __init__(self, token, *, baseuri="https://discord.com/api/v7",
                 loop=asyncio.get_event_loop()):
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
            "Authorization"        : f"Bot {self.token}",
            "User-Agent"           : f"DiscordBot ("
                                     f"https://github.com/TAG-Epic/speedcord "
                                     f"{speedcord_version}) "
                                     f"Python/{python_version[0]}."
                                     f"{python_version[1]} "
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
            Whether to enable compression. Refer to https://discord.com/developers/docs/topics/gateway for more information.
        """
        options = {
            "max_msg_size": 0,
            "timeout"     : 60,
            "autoclose"   : False,
            "headers"     : {
                "User-Agent": self.default_headers["User-Agent"]
            },
            "compress"    : compression
        }
        return await self.session.ws_connect(url, **options)

    async def request(self, route: Route, **kwargs):
        """
        Sends a request to the Discord API. Handles rate limits by utilizing LockManager and the `Discord API Bucket
        system`_.

        .. _Discord API Bucket system: https://discord.com/developers/docs/topics/gateway#encoding-and-compression

        When the client wants to send a new request, this method attempts to acquire a ratelimit lock. When it
        eventually does, it sends a request and checks to see if the ratelimit has been exceeded. If so,
        that Bucket's LockManager is locked so other requests cannot acquire a lock.
        The Discord Bucket system returns a `delta` value which specifies how long it will take before another
        request can be sent and the LockManager for that Bucket can be unlocked.

        Parameters
        ----------
        route: Route
            The Discord API route to send a request to.
        **kwargs: Dict[str, Any]
            The parameters to send with the request.
        """
        bucket = route.bucket

        for i in range(self.retry_attempts):
            if not self.global_lock.is_set():
                self.logger.debug("Sleeping for Global Rate Limit")
                await self.global_lock.wait()

            ratelimit_lock: asyncio.Lock = self.ratelimit_locks.get(bucket,
                                                                    asyncio.Lock(
                                                                        loop=self.loop))
            await ratelimit_lock.acquire()
            with LockManager(ratelimit_lock) as lockmanager:
                # Merge default headers with the users headers,
                # could probably use a if to check if is headers set?
                # Not sure which is optimal for speed
                kwargs["headers"] = {
                    **self.default_headers, **kwargs.get("headers", {})
                }

                # Format the reason
                try:
                    reason = kwargs.pop("reason")
                except KeyError:
                    pass
                else:
                    if reason:
                        kwargs["headers"]["X-Audit-Log-Reason"] = uriquote(
                            reason, safe="/ ")
                r = await self.session.request(route.method,
                                               self.baseuri + route.path,
                                               **kwargs)

                # check if we have rate limit header information
                remaining = r.headers.get('X-Ratelimit-Remaining')
                if remaining == '0' and r.status != 429:
                    # we've depleted our current bucket
                    delta = float(r.headers.get("X-Ratelimit-Reset-After"))
                    self.logger.debug(
                        f"Ratelimit exceeded. Bucket: {bucket}. Retry after: "
                        f"{delta}")
                    lockmanager.defer()
                    self.loop.call_later(delta, ratelimit_lock.release)

                status_code = r.status

                if status_code == 404:
                    raise NotFound(r)
                elif status_code == 401:
                    raise Unauthorized(r)
                elif status_code == 403:
                    raise Forbidden(r, await r.text())
                elif status_code == 429:
                    if not r.headers.get("Via"):
                        # Cloudflare banned?
                        raise HTTPException(r, await r.text())

                    data = await r.json()
                    retry_after = data["retry_after"] / 1000
                    is_global = data.get("global", False)
                    if is_global:
                        self.logger.warning(
                            f"Global ratelimit hit! Retrying in "
                            f"{retry_after}s")
                    else:
                        self.logger.warning(
                            f"A ratelimit was hit (429)! Bucket: {bucket}. "
                            f"Retrying in {retry_after}s")

                    await asyncio.sleep(retry_after)
                    continue

                return r

    async def close(self):
        await self.session.close()
