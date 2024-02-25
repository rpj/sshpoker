import socket
import threading
from abc import ABC
from dataclasses import dataclass
from typing import Optional, Tuple

import paramiko
from rich.console import Console

RetAddr = Tuple[str, int]
ClientTuple = Tuple[socket.socket, RetAddr]


@dataclass
class Client:
    addr: ClientTuple
    client_thread: Optional[threading.Thread] = None
    main_thread: Optional[threading.Thread] = None
    channel: Optional[paramiko.Channel] = None
    pubkey_b64: Optional[str] = None
    username: Optional[str] = None


class ScreenBase(ABC):
    def display_screen(self, client: Client, console: Console) -> None:
        pass

    def handle_input(
        self, client: Client, input_bytes: bytes, console: Console
    ) -> "ScreenBase":
        pass
