"""
Created by Epic at 9/1/20
"""


class HTTPException(Exception):
    """
    Exception that's thrown when an HTTP request operation fails.
    """

    def __init__(self, request, data):
        self.request = request
        self.data = data
        super().__init__(data)


class Forbidden(HTTPException):
    """
    Exception that's thrown for when status code 403 occurs.

    Subclass of :exc:`HTTPException`
    """
    pass


class NotFound(HTTPException):
    """
    Exception that's thrown when status code 404 occurs.

    Subclass of :exc:`HTTPException`
    """

    def __init__(self, request):
        self.request = request
        Exception.__init__(self, "The selected resource was not found")


class Unauthorized(HTTPException):
    """
    Exception that's thrown when status code 401 occurs.

    Subclass of :exc:`HTTPException`
    """

    def __init__(self, request):
        self.request = request
        Exception.__init__(self, "You are not authorized to view this resource")


class LoginException(Exception):
    """
    Base exception thrown when an issue occurs during login attempts.
    """
    pass


class InvalidToken(LoginException):
    """
    Exception that's thrown when an attempt to login with invalid token is made.
    """

    def __init__(self):
        super().__init__("Invalid token provided.")


class ConnectionsExceeded(LoginException):
    """
    Exception that's thrown when all gateway IDENTIFYs are exhausted.
    """
    def __init__(self):
        super().__init__("You have exceeded your gateway connection limits")


class GatewayException(Exception):
    """
    Base exception that's thrown whenever a gateway error occurs.
    """
    pass


class GatewayClosed(GatewayException):
    """
    Exception that's thrown when the gateway is used while in a closed state.
    """
    def __init__(self):
        super().__init__("You can't do this as the gateway is closed.")


class GatewayUnavailable(GatewayException):
    """
    Exception that's thrown when the gateway is unreachable.
    """
    def __init__(self):
        super().__init__("Can't reach the discord gateway. Have you tried checking your internet?")


class GatewayClosedUnexpected(GatewayException):
    """
    The gateway closed unexpectedly.
    """
    pass


class GatewayNotAuthenticated(GatewayClosedUnexpected):
    """
    We sent a payload to the discord gateway before authenticating.
    """
    def __init__(self):
        super().__init__("We sent a payload to the discord gateway before authenticating.")


class InvalidShardCount(GatewayException):
    """
    Invalid shard count sent to discord. Please modify your shard_count.
    """
    def __init__(self):
        super().__init__("Invalid shard count sent to discord. Please modify your shard_count.")


class InvalidGatewayVersion(GatewayException):
    """
    Invalid gateway version provided! This is likely the library being very out of date.
    """
    def __init__(self):
        super().__init__("Invalid gateway version provided!")


class IntentException(GatewayException):
    """
    Base exceptions for all intent exceptions
    """
    pass


class InvalidIntentNumber(IntentException):
    """
    The intent value you provided is invalid.
    """
    def __init__(self):
        super().__init__("The intent number you provided is not valid. "
                         "You can use https://ziad87.me/intents/ to calculate intents")


class IntentNotWhitelisted(IntentException):
    """
    You are not whitelisted for some of the intents you provided.
    """
    def __init__(self):
        super().__init__("You tried to launch with intents you are not whitelisted for.")
