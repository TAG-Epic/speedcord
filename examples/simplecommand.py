"""
Created by Epic at 9/5/20
"""

import speedcord
from speedcord.http import Route
from os import environ as env
from logging import basicConfig, DEBUG

client = speedcord.Client(intents=512, shard_count=5)
basicConfig(level=DEBUG)  # Comment this out if you don't want to see what's going on behind the scenes


@client.listen("MESSAGE_CREATE")
async def on_message(data, shard):
    message = data
    if message["content"].lower() == "!test":
        channel = message["channel_id"]
        route = Route("POST", f"/channels/{channel}/messages", channel_id=channel)
        await client.http.request(route, json={"content": "Hello world!"})

client.token = env["TOKEN"]
client.run()
