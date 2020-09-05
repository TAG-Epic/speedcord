"""
Created by Epic at 9/5/20
"""

import speedcord
from speedcord.http import Route

client = speedcord.Client(intents=512)


async def on_message(data, shard):
    message = data
    if message["content"].lower() == "!test":
        channel = message["channel_id"]
        route = Route("POST", f"/channels/{channel}/messages", channel_id=channel)
        await client.http.request(route, json={"content": "Hello world!"})


client.event_dispatcher.register("MESSAGE_CREATE", on_message)

client.token = "token"
client.run()
