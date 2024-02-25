import asyncio
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Dict, Optional

import paramiko
import pyfiglet
from rich import print
from rich.console import Console

from sshpoker.db import SSHPokerDB

from sshpoker.types import ClientTuple, Client, ClientQuitRequest
from sshpoker.screens import mainmenu
from sshpoker.const import MAX_CONNECTED_CLIENTS


console = Console()
host_key = paramiko.RSAKey(filename="hostkey")
clients: Dict[ClientTuple, Client] = {}
db_path = Path(__file__).parent / "database.sqlite3"
db = SSHPokerDB(db_path)

BANNER_FONT = "ansi_shadow"


def client_thread(client_tuple: ClientTuple, shutdown_event: threading.Event):
    client, _addr = client_tuple
    t = paramiko.Transport(client)
    t.set_gss_host(socket.getfqdn(""))
    t.load_server_moduli()
    t.add_server_key(host_key)
    server = Server()
    t.start_server(server=server)

    while not shutdown_event.is_set():
        shutdown_event.wait(1.0)

    client.close()
    t.close()


async def client_main_thread_async(client: Client):
    channel = client.channel
    channel.transport.set_keepalive(10)

    ip, port = channel.get_transport().getpeername()
    keydisp = client.pubkey_b64[-16:].replace("=", "")
    client_str = f"{keydisp} {client.username}@{ip}:{port}"

    async def disconnect(extra: str = ""):
        print(f"Disconnect: {client_str} {extra}")
        if not await db.log_user_out(client.pubkey_b64):
            print(f"LOGOUT FAILED! {client_str} {client.pubkey_b64}")
        channel.close()
        del clients[client.addr]

    def rich_send(fmted_str):
        with console.capture() as cap:
            console.print(fmted_str)
        try:
            channel.send(bytes(cap.get(), "utf-8"))
        except Exception as e:
            print(f"SEND FAILED! {client_str}")
            print(e)

    db_user = await db.get_user(client.pubkey_b64)
    hello_str = "to SSH Poker"
    if db_user is None:
        print(f"New user:   {client_str}")
        await db.new_user(client.pubkey_b64)
    else:
        hello_str = "back"

    banner = ("\n[bold][cyan]"
        + pyfiglet.figlet_format("sshpoker", font=BANNER_FONT)
        + "[/cyan][/bold]")
    
    cur_session = await db.log_user_in(client.pubkey_b64, ip, port)
    if cur_session:
        [(_pk, logged_in, ip, _port)] = cur_session
        rich_send(banner + "[bold][red]Already connected![/bold][/red]\n\n" +
                  f"This key has been logged in from {ip} since {logged_in}\n\n")
        await disconnect("already connected")
        return

    # wait to do this here because it's not much more expensive and we
    # get the full banner plus the already-connected check above, which
    # is helpful/important for security awareness
    if len(clients) > MAX_CONNECTED_CLIENTS:
        rich_send(banner + "The server is [red]full[/red] right now, sorry!\n" + "Please try again in awhile...\n\n")
        await disconnect("max clients")

    rich_send(banner
        + f"Welcome {hello_str}, [bold][green]{client.username}[/green][/bold]!\n"
        + f"{len(clients)} user{'s' if len(clients) > 1 else ''} online."
    )

    print(f"Connected:  {client_str}")
    cur_screen = mainmenu.Screen()
    last_screen = cur_screen
    while channel.active:
        try:
            client_quit_requested = False
            with console.capture() as cap:
                try:
                    await cur_screen.display_screen(client, console, db_path)
                except ClientQuitRequest:
                    client_quit_requested = True
                    
            channel.send(bytes(cap.get(), "utf-8"))

            if client_quit_requested:
                await disconnect("client requested")
                return

            if not cur_screen.expects_input:
                cur_screen = last_screen
                continue

            data = channel.recv(4096)
            if len(data) == 0:
                await disconnect("zero-byte read")
                return

            if cur_screen:
                if cur_screen.expects_input:
                    with console.capture() as cap:
                        next_screen = await cur_screen.handle_input(client, data, console, db_path)
                        if next_screen:
                            last_screen = cur_screen
                            cur_screen = next_screen
                    channel.send(bytes(cap.get(), "utf-8") + b"\n")
                else:
                    cur_screen = mainmenu.Screen()
            else:
                print(f"Unhandled data from: {client_str}\n\t{data}")
        except socket.timeout:
            pass
        time.sleep(0.01)

def client_main_bounce(client):
    asyncio.run(client_main_thread_async(client))

class Server(paramiko.ServerInterface):
    def __init__(self):
        self.username: Optional[str] = None
        self.key: Optional[paramiko.PKey] = None

    def check_channel_request(self, kind, chanid):
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED

    def check_auth_publickey(self, username: str, key: paramiko.PKey):
        self.key = key
        self.username = username
        return paramiko.AUTH_SUCCESSFUL

    def get_allowed_auths(self, username: str):
        return "publickey"

    def check_channel_shell_request(self, channel: paramiko.Channel):
        channel_peer = channel.getpeername()
        if not channel_peer in clients:
            print(f"ERROR: non-connected channel opened? {channel_peer} {channel}")
            channel.close()
            return
        client = clients[channel_peer]
        client.channel = channel
        client.pubkey_b64 = self.key.get_base64()
        client.username = self.username
        client.main_thread = threading.Thread(target=client_main_bounce, args=(client,))
        client.main_thread.start()
        return True

async def main():
    await db.initialize()
    await db._direct_exec("delete from session")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", 2222))

    sock.listen(100)
    shutdown_event = threading.Event()
    while True:
        try:
            client_tuple = sock.accept()
            c_thread = threading.Thread(
                target=client_thread, args=(client_tuple, shutdown_event)
            )
            c_thread.start()
            clients[client_tuple[1]] = Client(addr=client_tuple[1], client_thread=c_thread)
        except KeyboardInterrupt:
            print(f"Exiting, disconnecting {len(clients)} connected clients...")
            shutdown_event.set()
            for client in clients.values():
                client.client_thread.join()
                client.main_thread.join()
            print("... done!")
            sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())