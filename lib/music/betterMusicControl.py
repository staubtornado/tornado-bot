from json import loads
from selectors import DefaultSelector, EVENT_READ, EVENT_WRITE
from socket import socket, AF_INET, SOCK_STREAM
from types import SimpleNamespace
from typing import Union, Any

from discord import Bot

from data.config.settings import SETTINGS


class BetterMusicControl:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.sel = DefaultSelector()

        self.listener = bot.loop.create_task(self._listener())

    def valid_request(self, ):

    def accept_wrapper(self, sock: Union[Any, socket]):
        conn, addr = sock.accept()  # Should be ready to read
        print(f"Accepted connection from {addr}")
        conn.setblocking(False)
        data = SimpleNamespace(addr=addr, inb=b"", outb=b"")
        self.sel.register(conn, EVENT_READ | EVENT_WRITE, data=data)

    def service_connection(self, con_key, con_mask):
        sock = con_key.fileobj
        data = con_key.data
        if con_mask & EVENT_READ:
            recv_data = sock.recv(1024)  # Should be ready to read
            if recv_data:
                data.outb += recv_data
            else:
                print(f"Closing connection to {data.addr}")
                self.sel.unregister(sock)
                sock.close()
        if con_mask & EVENT_WRITE:
            if data.outb:
                message: dict = dict(loads(data.outb.decode("utf-8")))
                print(f"[SYSTEM] Received {message.get('message')} from {data.addr}")


                voice_states: dict[int] = self.bot.get_cog("Music").voice_states
                if any([True for vs in voice_states if voice_states[vs].id == message.get("session_id")]):
                    actions: dict[str] = {"TOGGLE": lambda : }



                print(f"Echoing {data.outb!r} to {data.addr}")
                sent = sock.send(data.outb)  # Should be ready to write
                data.outb = data.outb[sent:]

    async def _listener(self):
        host, port = SETTINGS["ExternalIP"], SETTINGS["Port"]
        l_sock = socket(AF_INET, SOCK_STREAM)
        l_sock.bind((host, port))
        l_sock.listen()
        print(f"Listening on {(host, port)}")
        l_sock.setblocking(False)
        self.sel.register(l_sock, EVENT_READ, data=None)

        try:
            while True:
                events = self.sel.select(timeout=None)
                for key, mask in events:
                    if key.data is None:
                        self.accept_wrapper(key.fileobj)
                    else:
                        self.service_connection(key, mask)
        except KeyboardInterrupt:
            print("Caught keyboard interrupt, exiting")
        finally:
            self.sel.close()
