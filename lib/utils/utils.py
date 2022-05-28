from datetime import timedelta, datetime
from time import strftime, gmtime
from traceback import format_tb
from typing import Union

from discord import Permissions
from millify import millify


def ordinal(n: Union[int, float]) -> str:
    if isinstance(n, float):
        n = int(n)
    return "%d%s" % (n, "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10::4])


def shortened(n: Union[int, float], precision: int = 2) -> str:
    return millify(n, precision=precision)


def extract_int(string: str) -> list[int]:
    return [int(s) for s in string.split() if s.isdigit()]


def time_to_string(seconds: int) -> str:
    if seconds < 3600:
        output = strftime('%M:%S', gmtime(seconds))
    elif 86400 > seconds >= 3600:
        output = strftime('%H:%M:%S', gmtime(seconds))
    else:
        output = timedelta(seconds=seconds)
    return output


def get_permissions(permissions: Permissions) -> list[str]:
    rtrn = []

    for method_name in dir(permissions):  # Iterate through all attributes of the permission object
        if not method_name.startswith("is") and not method_name.startswith("_"):  # If the attribute is a permission...
            if getattr(permissions, method_name) is True:  # ... and that attribute is true...
                rtrn.append(method_name)  # ... append it to the list that is returned
    return rtrn


def save_traceback(exception):
    with open(f"./data/tracebacks/{datetime.now().strftime('%d_%m_%Y__%H_%M_%S_%f')}.txt", "w") as file:
        try:
            tb = exception.original.__traceback__
        except AttributeError:
            tb = exception.__traceback__
        file.write("".join(format_tb(tb)))
