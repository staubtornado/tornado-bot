from datetime import datetime
from io import BytesIO
from math import floor, ceil
from time import strftime, gmtime
from traceback import format_tb
from typing import Union, Optional
from urllib.parse import ParseResult, urlparse

from aiofiles import open as aio_open
from discord import Permissions, File, ApplicationCommandInvokeError
from matplotlib import pyplot as plt, use
from matplotlib.axes import Axes
from matplotlib.figure import Figure
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


async def save_traceback(
        exception: Union[ApplicationCommandInvokeError, Exception],
        additional_info: str = None
) -> None:
    if isinstance(exception, ApplicationCommandInvokeError):
        exception = exception.original
    async with aio_open(f"./data/tracebacks/{datetime.now().strftime('%d_%m_%Y__%H_%M_%S_%f')}.txt", "w") as f:
        await f.write("".join(format_tb(exception.__traceback__)))
        await f.write(f"Exception: {exception}\n")
        if additional_info is not None:
            await f.write(f"Additional info: {additional_info}")


def create_graph(
        coordinates: list[tuple[int, int]],
        title: Optional[str] = None,
        x_label: Optional[str] = None,
        y_label: Optional[str] = None
) -> File:
    use("Agg")

    fig: Figure
    ax: Axes
    fig, ax = plt.subplots()

    ax.plot(*zip(*coordinates))

    if title is not None:
        ax.set_title(title)
    if x_label is not None:
        ax.set_xlabel(x_label)
    if y_label is not None:
        ax.set_ylabel(y_label)

    plt.tight_layout()
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)
    ax.set_facecolor((88 / 255, 101 / 255, 242 / 255))
    ax.spines["bottom"].set_color("#969890")
    ax.spines["top"].set_color("#969890")
    ax.spines["right"].set_color("#969890")
    ax.spines["left"].set_color("#969890")
    ax.tick_params(axis="x", colors="#969890")
    ax.tick_params(axis="y", colors="#969890")
    ax.xaxis.label.set_color("#969890")
    ax.yaxis.label.set_color("#969890")
    ax.title.set_color("#969890")

    imgdata = BytesIO()
    fig.savefig(imgdata, format="png")
    imgdata.seek(0)
    plt.close(fig)
    return File(imgdata, filename="graph.png")


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
