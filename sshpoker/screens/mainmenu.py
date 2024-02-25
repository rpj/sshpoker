import pyfiglet
from rich.console import Console

from sshpoker.types import Client, ScreenBase


class Screen(ScreenBase):
    COMMANDS = [
        "Change user name",
        "Enter room",
        "Create new room",
        "Get statistics",
        "Message user",
    ]

    def display_screen(self, client: Client, console: Console):
        console.print(
            "\n[bold][green]"
            + pyfiglet.figlet_format("Main Menu", font="js_block_letters")
            + "[/green][/bold]"
        )
        for i, cmd in enumerate(self.COMMANDS):
            console.print(f" ⦿ {i+1}) [bold][white]{cmd}[/white][/bold]")
        console.print("\nSelection? ", end="")

    def handle_input(
        self, client: Client, input_bytes: bytes, console: Console
    ) -> ScreenBase:
        try:
            choice = int(input_bytes.decode("utf-8").strip())
        except:
            console.print("\n[bold][red]Bad choice![/red] Try again...[/bold]\n")
        return self
