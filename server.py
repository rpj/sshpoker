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

from sshpoker.types import ClientTuple, Client
from sshpoker.screens import mainmenu


console = Console()
host_key = paramiko.RSAKey(filename="hostkey")
clients: Dict[ClientTuple, Client] = {}
db_path = Path(__file__).parent / "database.sqlite3"
db = SSHPokerDB(db_path)

BANNER_FONT = "ansi_shadow"


def client_thread(client_tuple: ClientTuple, shutdown_event: threading.Event):
    client, addr = client_tuple
    ip, port = addr
    t = paramiko.Transport(client)
    t.set_gss_host(socket.getfqdn(""))
    t.load_server_moduli()
    t.add_server_key(host_key)
    server = Server()
    t.start_server(server=server)

    while not shutdown_event.is_set():
        shutdown_event.wait(0.1)

    client.close()
    t.close()


async def client_main_thread_async(client: Client):
    channel = client.channel
    channel.transport.set_keepalive(10)

    ip, port = channel.get_transport().getpeername()
    keydisp = client.pubkey_b64[-32:].replace("=", "")
    client_str = f"{keydisp} {client.username}@{ip}:{port}"

    db_user = await db.get_user(client.pubkey_b64)
    hello_str = "to SSH Poker"
    if db_user is None:
        print(f"New user:   {client_str}")
        await db.new_user(client.pubkey_b64, client.username)
    else:
        hello_str = "back"
    with console.capture() as cap:
        console.print(
            "\n[bold][cyan]"
            #+ pyfiglet.figlet_format("ssh", font=BANNER_FONT) + "\n"
            + pyfiglet.figlet_format("sshpoker", font=BANNER_FONT)
            + "[/cyan][/bold]"
            + f"Welcome {hello_str}, [bold][green]{client.username}[/green][/bold]!\n"
        )
    channel.send(bytes(cap.get(), "utf-8"))

    print(f"Connected:  {client_str}")
    cur_screen = mainmenu.Screen()
    while channel.active:
        try:
            with console.capture() as cap:
                cur_screen.display_screen(client, console)
            channel.send(bytes(cap.get(), "utf-8"))

            data = channel.recv(4096)
            if len(data) == 0:
                print(f"Disconnect: {client_str}")
                channel.close()
                return
            if cur_screen:
                with console.capture() as cap:
                    cur_screen = cur_screen.handle_input(client, data, console)
                channel.send(bytes(cap.get(), "utf-8"))
            else:
                print(f"Unhanled data from: {client_str}\n\t{data}")
        except socket.timeout:
            pass
        time.sleep(0.01)

def client_main_thread(client: Client):
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
        client.main_thread = threading.Thread(target=client_main_thread, args=(client,))
        client.main_thread.start()
        return True

async def main():
    await db.initialize()

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