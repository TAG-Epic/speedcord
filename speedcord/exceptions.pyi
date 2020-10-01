from aiohttp import ClientResponse


class HTTPException(Exception):
    request: ClientResponse
    data: str

    def __init__(self, request: ClientResponse, data: str) -> None:
        ...


class Forbidden(HTTPException):
    ...


class NotFound(HTTPException):
    request: ClientResponse

    def __init__(self, request: ClientResponse) -> None:
        ...


class Unauthorized(HTTPException):
    request: ClientResponse

    def __init__(self, request: ClientResponse) -> None:
        ...


class LoginException(Exception):
    ...


class InvalidToken(LoginException):
    def __init__(self) -> None:
        ...


class ShardingNotSupported(LoginException):
    def __init__(self) -> None:
        ...


class ConnectionsExceeded(LoginException):
    def __init__(self) -> None:
        ...


class GatewayException(Exception):
    ...


class GatewayClosed(GatewayException):
    def __init__(self) -> None:
        ...
