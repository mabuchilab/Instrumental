from past.builtins import unicode
from future.builtins import bytes
from future.utils import PY2

import time
from functools import wraps
import pickle

from .errors import TimeoutError


def save_result(filename):
    """Decorator to save return value(s)"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwds):
            retval = func(*args, **kwds)
            with open(filename, 'wb') as fh:
                pickle.dump(retval, fh)
            return retval
        return wrapper
    return decorator


def cached_as(filename):
    """Decorator to cache return value(s) in a pickle file

    If a file with the given filename exists, it is unpickled and that value is returned. Otherwise,
    the decorated function is called, and its return value is returned, after pickling and saving it
    for later use.
    """
    import os.path
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwds):
            if os.path.exists(filename):
                with open(filename, 'rb') as fh:
                    return pickle.load(fh)
            else:
                retval = func(*args, **kwds)
                with open(filename, 'wb') as fh:
                    pickle.dump(retval, fh)
                return retval
        return wrapper
    return decorator


def to_str(value, encoding='utf-8'):
    """Convert value to a str type

    Returns a bytes object in Python 2, and a unicode string in Python 3. Encodes or decodes the
    input value as necessary.
    """
    if isinstance(value, str):
        return value

    if PY2:
        return unicode(value).encode(encoding=encoding)
    else:
        return bytes(value).decode(encoding=encoding)


def call_with_timeout(func, timeout):
    """Call a function repeatedly until successful or timeout elapses

    timeout : float or None
        If None, only try to call `func` once. If negative, try until successful. If nonnegative,
        try for up to `timeout` seconds. If a non-None timeout is given, hides any exceptions that
        `func` causes. If timeout elapses, raises a TimeoutError.
    """
    if timeout is None:
        return func()

    cur_time = start_time = time.time()
    max_time = start_time + float(timeout)
    while cur_time <= max_time:
        try:
            return func()
        except:
            pass
        cur_time = time.time()

    raise TimeoutError


# From http://code.activestate.com/recipes/576563-cached-property/#c3
def cached_property(fun):
    """A memoize decorator for class properties."""
    @wraps(fun)
    def get(self):
        try:
            return self._cache[fun]
        except AttributeError:
            self._cache = {}
        except KeyError:
            pass
        ret = self._cache[fun] = fun(self)
        return ret
    return property(get)
