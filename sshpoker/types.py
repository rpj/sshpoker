import socket
import threading
from abc import ABC
from dataclasses import dataclass
from typing import Optional, Tuple

import paramiko
from rich.console import Console

RetAddr = Tuple[str, int]
ClientTuple = Tuple[socket.socket, RetAddr]


class ClientQuitRequest(Exception):
    pass


@dataclass
class Client:
    addr: ClientTuple
    client_thread: Optional[threading.Thread] = None
    main_thread: Optional[threading.Thread] = None
    channel: Optional[paramiko.Channel] = None
    pubkey_b64: Optional[str] = None
    username: Optional[str] = None


class ScreenBase(ABC):
    expects_input: bool

    def __init__(self, *, expects_input: bool = False):
        self.expects_input = expects_input

    async def display_screen(
        self, client: Client, console: Console, db_path: str
    ) -> None:
        pass

    async def handle_input(
        self, client: Client, input_bytes: bytes, console: Console, db_path: str
    ) -> Optional["ScreenBase"]:
        """
        Returning None will return the user to the main menu.
        Otherwise, the ScreenBase returned will be transitioned to next.
        """
        pass
