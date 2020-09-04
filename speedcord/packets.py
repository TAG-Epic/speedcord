"""
Created by Epic at 9/2/20
"""


def identify(token: str, intents: int, *, mobile_status=False):
    return {
        "op": 2,
        "d": {
            "token": token,
            "properties": {
                "$os": "linux",
                "$browser": ("SpeedCord", "Discord iOS")[mobile_status],  # TODO: Maybe make it more clear what it does?
                "$device": "SpeedCord"
            },
            "intents": intents
        }
    }
