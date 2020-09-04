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
    def __init__(self, method: str, route: str, **parameters):
        self.method = method
        self.path = route.format(**parameters)

        # Used for bucket cooldowns
        self.channel_id = parameters.get("channel_id")
        self.guild_id = parameters.get("guild_id")

    @property
    def bucket(self):
        return f"{self.channel_id}:{self.guild_id}:{self.path}"


class LockManager:
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
    def __init__(self, token, *, baseuri="https://discord.com/api/v7", loop=asyncio.get_event_loop()):
        self.baseuri = baseuri
        self.token = token
        self.loop = loop
        self.session = ClientSession(loop=loop)
        self.logger = logging.getLogger("speedcord.http")

        self.ratelimit_locks = {}
        self.global_lock = asyncio.Event(loop=self.loop)

        # Clear the global lock on start
        self.global_lock.set()

        self.default_headers = {
            "X-RateLimit-Precision": "millisecond",
            "Authorization": f"Bot {self.token}",
            "User-Agent": f"DiscordBot (https://github.com/TAG-Epic/speedcord {speedcord_version}) Python/{python_version[0]}.{python_version[1]} aiohttp/{aiohttp_version}"
        }

        self.retry_attempts = 3

    async def create_ws(self, url, *, compression) -> ClientWebSocketResponse:
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
        bucket = route.bucket

        for i in range(self.retry_attempts):
            if not self.global_lock.is_set():
                self.logger.debug("Sleeping for Global Rate Limit")
                await self.global_lock.wait()

            ratelimit_lock: asyncio.Lock = self.ratelimit_locks.get(bucket, asyncio.Lock(loop=self.loop))
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

                # check if we have rate limit header information
                remaining = r.headers.get('X-Ratelimit-Remaining')
                if remaining == '0' and r.status != 429:
                    # we've depleted our current bucket
                    delta = float(r.headers.get("X-Ratelimit-Reset-After"))
                    self.logger.debug(f"Ratelimit exceeded. Bucket: {bucket}. Retry after: {delta}")
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
                        self.logger.warning(f"Global ratelimit hit! Retrying in {retry_after}s")
                    else:
                        self.logger.warning(
                            f"A ratelimit was hit! This should not happen! Bucket: {bucket}. Retrying in {retry_after}s")

                    await asyncio.sleep(retry_after)
                    continue

                return r

    async def close(self):
        await self.session.close()
