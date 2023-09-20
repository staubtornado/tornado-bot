from asyncio import AbstractEventLoop, get_event_loop
from datetime import datetime
from sys import stdout, stderr
from traceback import format_exception

from discord import ApplicationCommandInvokeError


def log(message: str, *, error: bool = False) -> None:
    """
    Logs a message to the console.
    :param message: The message to log.
    :param error: Whether the message is an error message.

    :return: None
    """
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}", file=stdout if not error else stderr)


def _write_file(path: str, content: str) -> None:
    with open(path, "w") as file:
        file.write(content)


async def save_traceback(_exception:  ApplicationCommandInvokeError | Exception) -> None:
    """
    Saves a traceback to a file without blocking the event loop.
    :param _exception: The exception to save the traceback of.

    :return: None
    """
    exception = _exception.original if isinstance(_exception, ApplicationCommandInvokeError) else _exception
    loop: AbstractEventLoop = get_event_loop()

    tb = ''.join(format_exception(type(exception), exception, exception.__traceback__))
    await loop.run_in_executor(None, _write_file, f"./logs/{datetime.now().strftime('%Y-%m-%d--%H-%M-%S')}.txt", tb)
