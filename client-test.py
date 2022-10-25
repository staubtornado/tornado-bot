from asyncio import open_connection, new_event_loop

HOST: str = "127.0.0.1"
PORT: int = 65432


async def run_client() -> None:
    reader, writer = await open_connection(HOST, PORT)

    request: dict = {
        "uID": "272446903940153345",
        "sessionID": "C694DCE0=EA",
        "message": "TOGGLE"
    }

    writer.write(bytes(str(request), "utf-8"))
    await writer.drain()

    data: bytes = await reader.read(1024)
    if not data:
        print("Socket closed.")

    print(f"Received: {data.decode()!r}")

if __name__ == "__main__":
    loop = new_event_loop()
    loop.run_until_complete(run_client())
