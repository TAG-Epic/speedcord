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
