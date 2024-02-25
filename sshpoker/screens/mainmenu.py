from typing import Optional

import pyfiglet
from rich.console import Console

from sshpoker.screens import getstats, getwallet, jointable
from sshpoker.screens import quit as quit_screen
from sshpoker.types import Client, ScreenBase


class Screen(ScreenBase):
    COMMANDS = [
        ("Check your [green]wallet[/green]", getwallet.Screen),
        ("Get your [yellow]statistics[/yellow]", getstats.Screen),
        ("Join a table", jointable.Screen),
        ("Create a new table", None),
        ("Message another user", None),
        (None, None),
        (None, None),
        (None, None),
        ("[red]Quit[/red]", quit_screen.Screen),
    ]

    def __init__(self):
        super().__init__(expects_input=True)

    async def display_screen(self, client: Client, console: Console, db_path: str):
        console.print(
            "\n[bold][green]"
            + pyfiglet.figlet_format("Main Menu", font="js_block_letters")
            + "[/green][/bold]"
        )
        for i, (cmd_name, command_class) in enumerate(self.COMMANDS):
            if command_class:
                console.print(f" ⦿ [{i+1}] [bold][white]{cmd_name}[/white][/bold]")
        console.print("\nSelection? ", end="")

    async def handle_input(
        self, client: Client, input_bytes: bytes, console: Console, db_path: str
    ) -> Optional[ScreenBase]:
        try:
            choice = int(input_bytes.decode("utf-8").strip())
            if choice > len(self.COMMANDS):
                raise Exception(f"{len(self.COMMANDS)} {choice}")
            return self.COMMANDS[choice - 1][1]()
        except Exception as e:
            print(e)
            console.print("\n[bold][red]Bad choice![/red] Try again...[/bold]\n")
        return self
