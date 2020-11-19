"""
Created by Epic at 9/1/20

Simple library to interact with the discord API
"""
from .client import Client
from .exceptions import HTTPException, Forbidden, NotFound, Unauthorized, LoginException, InvalidToken, \
    ConnectionsExceeded, GatewayException, GatewayClosed, GatewayUnavailable
from .values import version as __version__

__all__ = ("__version__", "Client", "HTTPException", "Forbidden", "NotFound",
           "Unauthorized", "LoginException", "InvalidToken",
           "ConnectionsExceeded", "GatewayException", "GatewayClosed",
           "GatewayUnavailable"
           )
