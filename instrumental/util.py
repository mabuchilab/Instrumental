from past.builtins import unicode
from future.builtins import bytes
from future.utils import PY2

from functools import wraps
import pickle


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
