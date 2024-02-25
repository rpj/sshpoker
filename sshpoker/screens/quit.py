from typing import Optional

import pyfiglet
from rich.console import Console

from sshpoker.db import SSHPokerDB
from sshpoker.types import Client, ClientQuitRequest, ScreenBase


class Screen(ScreenBase):
    async def display_screen(self, client: Client, console: Console, db_path: str):
        console.print(
            "[white][bold]"
            + pyfiglet.figlet_format("Goodbye!", font="colossal")
            + "[/bold][/white]"
        )
        console.print(
            "[white]"
            + pyfiglet.figlet_format("Thanks for playing", font="rectangles")
            + "[/white]"
        )
        raise ClientQuitRequest()

    async def handle_input(
        self, client: Client, input_bytes: bytes, console: Console, db_path: str
    ) -> Optional[ScreenBase]:
        return None
