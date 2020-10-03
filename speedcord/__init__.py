"""
Created by Epic at 9/1/20

Simple library to interact with the discord API
"""
from .client import Client
from .values import version as __version__

__all__ = ("Client", "__version__")
