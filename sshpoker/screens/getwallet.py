from typing import Optional

import pyfiglet
from rich.console import Console

from sshpoker.db import SSHPokerDB
from sshpoker.types import Client, ScreenBase


class Screen(ScreenBase):
    async def display_screen(self, client: Client, console: Console, db_path: str):
        currency = await SSHPokerDB(db_path).get_user_currency(client.pubkey_b64)
        console.print(
            "[bold][yellow]"
            + pyfiglet.figlet_format("Wallet", font="js_block_letters")
            + "[/yellow][/bold]\n"
            + f"💰 [bold][green]{currency}[/bold][/green]"
        )

    async def handle_input(
        self, client: Client, input_bytes: bytes, console: Console, db_path: str
    ) -> Optional[ScreenBase]:
        return None
