"""
Created by Epic at 9/1/20
"""


class HTTPException(Exception):
    def __init__(self, request, data):
        self.request = request
        self.data = data
        super().__init__(data)


class Forbidden(HTTPException):
    pass


class NotFound(HTTPException):
    def __init__(self, request):
        self.request = request
        Exception.__init__(self, "The selected resource was not found")


class Unauthorized(HTTPException):
    def __init__(self, request):
        self.request = request
        Exception.__init__(self, "You are not authorized to view this resource")


class LoginException(Exception):
    pass


class InvalidToken(LoginException):
    def __init__(self):
        super().__init__("Invalid token provided.")


class ShardingNotSupported(LoginException):
    def __init__(self):
        super().__init__("SpeedCord does not support sharding at this time.")


class ConnectionsExceeded(LoginException):
    def __init__(self):
        super().__init__("You have exceeded your gateway connection limits")


class GatewayException(Exception):
    pass


class GatewayClosed(GatewayException):
    def __init__(self):
        super().__init__("You can't do this as the gateway is closed.")


class GatewayUnavailable(GatewayException):
    def __init__(self):
        super().__init__("Can't reach the discord gateway. Have you tried checking your internet?")


class GatewayClosedUnexpected(GatewayException):
    pass


class GatewayNotAuthenticated(GatewayClosedUnexpected):
    def __init__(self):
        super().__init__("We sent a payload to the discord gateway before authenticating.")


class InvalidShardCount(GatewayException):
    def __init__(self):
        super().__init__("Invalid shard count sent to discord. Please modify your shard_count.")


class InvalidGatewayVersion(GatewayException):
    def __init__(self):
        super().__init__("Invalid gateway version provided!")


class IntentException(GatewayException):
    pass


class InvalidIntentNumber(IntentException):
    def __init__(self):
        super().__init__("The intent number you provided is not valid.")


class IntentNotWhitelisted(IntentException):
    def __init__(self):
        super().__init__("You tried to launch with intents you are not whitelisted for.")
