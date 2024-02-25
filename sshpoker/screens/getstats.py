from typing import Optional

import pyfiglet
from rich.console import Console

from sshpoker.db import SSHPokerDB
from sshpoker.types import Client, ScreenBase


class Screen(ScreenBase):
    async def display_screen(self, client: Client, console: Console, db_path: str):
        (_pk1, first_seen, _pk2, winnings, games, wins, losses) = await SSHPokerDB(
            db_path
        ).get_user(client.pubkey_b64, with_stats=True)
        console.print(
            "[bold][yellow]"
            + pyfiglet.figlet_format("Statistics", font="js_block_letters")
            + "[/yellow][/bold]\n"
            + "\n".join(
                [
                    f"Joined:               {first_seen}",
                    f"Total winnings:       {winnings}",
                    f"Games played (W/L):   {games} ({wins} / {losses})",
                ]
            )
        )

    async def handle_input(
        self, client: Client, input_bytes: bytes, console: Console, db_path: str
    ) -> Optional[ScreenBase]:
        return None
