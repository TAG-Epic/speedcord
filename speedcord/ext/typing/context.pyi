from speedcord import Client
from typing import Dict, Any, Optional, List, Union

class BaseContext:
    client: Client
    data: Dict[str, Any]
    def __init__(self, client: Client, data: Dict[str, Any]):
        ...

class MessageContext:
    id: int
    channel_id: int
    guild_id: Optional[int]
    author: Dict[str, Any]  # TODO: Type this
    member: Optional[Dict[str, Any]]  # TODO: Type this
    content: str
    timestamp: int
    edited_timestamp: Optional[int]
    tts: bool
    mention_everyone: bool
    mentions: None  # TODO: Type this
    mention_roles: List[int]
    mention_channels: None  # TODO: Type this
    attachments: List[Any]  # TODO: Type this
    embeds: List[Dict[str, Any]]
    reactions: List[Any]  # TODO: Type this
    nonce: Optional[Union[int, str]]
    pinned: bool
    webhook_id: Optional[int]
    type: int
    activity: Optional[Any]  # TODO: Type this
    application: Optional[Any]  # TODO: Type this
    message_reference: Optional[Any]  # TODO: Type this
    flags: Optional[int]

