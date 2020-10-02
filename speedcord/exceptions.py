"""
Created by Epic at 9/1/20

Includes classes for exception handling
"""


class HTTPException(Exception):
    """HTTP request denied exception"""
    def __init__(self, request, data):
        self.request = request
        self.data = data
        super().__init__(data)


class Forbidden(HTTPException):
    """Exception for forbiddden case"""
    pass


class NotFound(HTTPException):
    """Resource not found exception"""
    def __init__(self, request):
        self.request = request
        Exception.__init__(self, "The selected resource was not found")


class Unauthorized(HTTPException):
    """Unauthorized access exception"""
    def __init__(self, request):
        self.request = request
        Exception.__init__(self, "You are not authorized to view this resource")


class LoginException(Exception):
    """Exception during user login"""
    pass


class InvalidToken(LoginException):
    """Invalid token exception"""
    def __init__(self):
        super().__init__("Invalid token provided.")


class ShardingNotSupported(LoginException):
    """Sharding not supported exception"""
    def __init__(self):
        super().__init__("SpeedCord does not support sharding at this time.")


class ConnectionsExceeded(LoginException):
    """Connection limit exceeded exception"""
    def __init__(self):
        super().__init__("You have exceeded your gateway connection limits")


class GatewayException(Exception):
    """Gateway exception"""
    pass


class GatewayClosed(GatewayException):
    """Closed gateway exception"""
    def __init__(self):
        super().__init__("You can't do this as the gateway is closed.")
