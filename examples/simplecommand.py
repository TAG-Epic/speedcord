"""
Created by Epic at 9/5/20

Instructions on using this example:
    - Create a discord server, app and bot (you can just follow the discord api instructions).
        - Full instructions can be found here - https://discordpy.readthedocs.io/en/latest/discord.html
    - Make sure the bot has message read and write permissions.
    - Copy the token from the bot and set it as an environment variable and invite it to a server
        - Also explained in the article above
    - Run this script.
    - Write !test in the chat.
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
