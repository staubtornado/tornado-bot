from typing import Union

from millify import millify


def ordinal(n: Union[int, float]) -> str:
    if isinstance(n, float):
        n = int(n)
    return "%d%s" % (n, "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10::4])


def shortened(n: Union[int, float], precision: int = 2) -> str:
    return millify(n, precision=precision)
