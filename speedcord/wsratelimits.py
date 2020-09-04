"""
Created by Epic at 9/4/20
"""
from asyncio import Lock, sleep
import logging

logger = logging.getLogger("speedcord.wsratelimits")
lock = Lock()


async def send_ws(ws, data):
    await lock.acquire()
    logger.debug("Data sent: " + str(data))
    await ws.send_json(data)
    await sleep(.5)  # We can do 120 events/60s, TODO: rewrite this to allow 120/60 instead of 1/.5?
    lock.release()
