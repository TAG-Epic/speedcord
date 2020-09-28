import unittest
from speedcord import Client
from os import environ as env


class Tests(unittest.TestCase):
    def test_start_no_shardcount_no_id(self):
        bot = Client(0, token=env["BOT_TOKEN"])

        @bot.listen("READY")
        async def on_ready(data, shard):
            bot.exit_event.set()

        bot.start()

    def test_start_shardcount_no_id(self):
        bot = Client(0, token=env["BOT_TOKEN"], shard_count=5)

        @bot.listen("READY")
        async def on_ready(data, shard):
            bot.exit_event.set()

        bot.start()

    def test_start_shardcount_id(self):
        bot = Client(0, token=env["BOT_TOKEN"], shard_count=5, shard_ids=[0, 2, 4])

        @bot.listen("READY")
        async def on_ready(data, shard):
            bot.exit_event.set()

        bot.start()


if __name__ == '__main__':
    unittest.main()
