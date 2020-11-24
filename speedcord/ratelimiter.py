"""
Created by Epic at 11/24/20
"""
from asyncio import Lock, sleep
from time import time
from logging import getLogger

logger = getLogger("speedcord.ratelimiter")


class TimesPer:
    def __init__(self, times, per):
        self.times = times
        self.per = per
        self.lock = Lock()
        self.left = self.times
        self.reset = time() + per

    async def trigger(self):
        async with self.lock:
            current_time = time()
            if current_time >= self.reset:
                self.reset = current_time + self.per
                self.left = self.times
            if self.left == 0:
                sleep_for = self.reset - current_time
                logger.debug(f"Gateway ratelimited! Sleeping for {sleep_for}s")
                await sleep(self.reset - current_time)
