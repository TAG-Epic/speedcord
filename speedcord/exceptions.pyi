from aiohttp import ClientResponse


class HTTPException(Exception):
    request: ClientResponse
    data: str

    def __init__(self, request: ClientResponse, data: str):
        ...


class Forbidden(HTTPException):
    ...


class NotFound(HTTPException):
    request: ClientResponse

    def __init__(self, request: ClientResponse):
        ...


class Unauthorized(HTTPException):
    request: ClientResponse

    def __init__(self, request: ClientResponse):
        ...


class LoginException(Exception):
    ...


class InvalidToken(LoginException):
    def __init__(self):
        ...


class ShardingNotSupported(LoginException):
    def __init__(self):
        ...


class ConnectionsExceeded(LoginException):
    def __init__(self):
        ...


class GatewayException(Exception):
    ...


class GatewayClosed(GatewayException):
    def __init__(self):
        ...


class GatewayUnavailable(GatewayException):
    def __init__(self):
        ...


class GatewayClosedUnexpected(GatewayException):
    ...


class GatewayNotAuthenticated(GatewayClosedUnexpected):
    def __init__(self):
        ...


class InvalidShardCount(GatewayClosedUnexpected):
    def __init__(self):
        ...

class InvalidGatewayVersion(GatewayClosedUnexpected):
    def __init__(self):
        ...

class IntentException(GatewayException):
    ...

class InvalidIntentNumber(IntentException):
    def __init__(self):
        ...

class IntentNotWhitelisted(IntentException):
    def __init__(self):
        ...
