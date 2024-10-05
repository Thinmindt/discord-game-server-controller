from dataclasses import dataclass


@dataclass
class ServerInfo:
    version: str
    servername: str
    description: str
