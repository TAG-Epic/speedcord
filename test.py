"""
Created by Epic at 11/14/20
"""


def test_require_shard_count_shard_ids():
    from speedcord import Client
    try:
        Client(0, shard_ids=[0, 2, 4])
    except TypeError:
        pass
    else:
        raise Exception("Did not verify if shard_count was passed.")
