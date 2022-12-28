from datetime import datetime
from math import floor, ceil
from time import strftime, gmtime
from traceback import format_tb
from typing import Union, Any
from urllib.parse import ParseResult, urlparse

from aiofiles import open as aio_open
import matplotlib.pyplot as plt
from discord import Permissions, File
from matplotlib import use
from millify import millify


def ordinal(n: Union[int, float]) -> str:
    if isinstance(n, float):
        n = int(n)
    return "%d%s" % (n, "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10::4])


def shortened(n: Union[int, float], precision: int = 2) -> str:
    return millify(n, precision=precision, drop_nulls=True)


def truncate(string: str, limit: int, end: str = "...") -> str:
    return string[:limit] + end if len(string) > limit else string


def extract_int(string: str) -> list[int]:
    return [int(s) for s in string.split() if s.isdigit()]


def time_to_string(seconds: int) -> str:
    if seconds < 3600:
        return strftime('%M:%S', gmtime(seconds))
    elif 86400 > seconds >= 3600:
        return strftime('%H:%M:%S', gmtime(seconds))
    return strftime("%d:%H:%M:%S", gmtime(seconds))


def get_permissions(permissions: Permissions) -> list[str]:
    rtrn = []

    for method_name in dir(permissions):  # Iterate through all attributes of the permission object
        if not method_name.startswith("is") and not method_name.startswith("_"):  # If the attribute is a permission...
            if getattr(permissions, method_name) is True:  # ... and that attribute is true...
                rtrn.append(method_name)  # ... append it to the list that is returned
    return rtrn


def save_traceback(exception):
    with open(f"./data/tracebacks/{datetime.now().strftime('%d_%m_%Y__%H_%M_%S_%f')}.txt", "w") as f:
        f.write("".join(format_tb(exception.__traceback__)))


def create_graph(y: list[int], title: str = None) -> tuple[str, File]:
    use("Agg")

    with plt.rc_context({"axes.edgecolor": "#838383", "xtick.color": "#838383", "ytick.color": "#838383"}):
        plt.plot([i for i in range(len(y))], y)

    if title is not None:
        plt.title(title)

    path = f"./data/cache/{datetime.now().strftime('%d_%m_%Y__%H_%M_%S_%f')}.png"
    plt.savefig(path, format="png", transparent=True)
    plt.close()

    with open(path, "rb") as f:
        path = path.replace("./data/cache/", "")

        f: Any = f
        picture = File(f, filename=path)
    return f"attachment://{path}", picture


def url_is_valid(url: str) -> tuple[bool, ParseResult]:
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme), parsed


def progress_bar(amount: Union[int, float], total: Union[int, float],
                 content: tuple[str, str, str] = ("◻", "", "▪️"), length: int = 10) -> str:
    percent: float = float((amount / total) if amount <= total else 1)
    return floor(percent * length) * content[0] + content[1] + ceil((1 - percent) * length) * content[2]


def split_list(lst: list, size: int):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


def all_equal(iterator) -> bool:
    iterator = iter(iterator)
    try:
        first = next(iterator)
    except StopIteration:
        return True
    return all(first == x for x in iterator)


def binary_search(arr: list[int], s: int, r: int, x: int) -> int:
    if r >= s:
        mid = s + (r - s) // 2

        if arr[mid] == x:
            return mid
        if arr[mid] > x:
            return binary_search(arr, s, mid - 1, x)
        return binary_search(arr, mid + 1, r, x)
    return -1


def linear_search(arr: list[int], x: int) -> int:
    for i, e in enumerate(arr):
        if e == x:
            return i
    return -1


async def read_file(filepath: str) -> bytes:
    async with aio_open(filepath, "rb") as f:
        return await f.read()
