# Gnu General Public License - see LICENSE.TXT

import sys
import functools
import time
from typing import Callable, TypeVar
from .simple_logging import SimpleLogging

log = SimpleLogging(__name__)

enabled = False

F = TypeVar("F", bound=Callable[..., object])


def set_timing_enabled(val: bool) -> None:
    global enabled
    enabled = val


def timer(func: F) -> F:
    @functools.wraps(func)
    def wrapper(*args: object, **kwargs: object) -> object:
        started = time.time()
        value = func(*args, **kwargs)
        ended = time.time()
        if enabled:
            data = ""
            if func.__name__ == "download_url" and len(args) > 1:
                data = args[1]
            elif func.__name__ == "main_entry_point" and len(sys.argv) > 2:
                data = sys.argv[2]
            log.info("timing_data|{0}|{1}|{2}|{3}", func.__name__, started, ended, data)
        return value

    return wrapper  # type: ignore[return-value]
