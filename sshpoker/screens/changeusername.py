from rich.console import Console

from sshpoker.types import Client, ScreenBase


class Screen(ScreenBase):
    def display_screen(self, client: Client, console: Console):
        with console.capture() as cap:
            console.print()
