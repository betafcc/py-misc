import inspect
from functools import wraps, update_wrapper

from toolz.functoolz import compose


class profunction:
    def __init__(self, function=lambda arg: arg):
        self._function = function
        update_wrapper(self, function)

    def __call__(self, *args, **kwargs):
        return self._function(*args, **kwargs)

    def before(self, *fs):
        return self.__class__(compose(self._function, *reversed(fs)))

    def after(self, *fs):
        return self.__class__(compose(*reversed(fs), self._function))


def before(*process_arguments):
    def _before(f):
        return profunction(f).before(*process_arguments)._function

    return _before


def after(*process_result):
    def _after(f):
        return profunction(f).after(*process_result)._function

    return _after


def kwargs(f):
    parameters = inspect.signature(f).parameters.values()

    @wraps(f)
    def _kwargs(**user_kwargs):
        _ = ((p.name, user_kwargs.get(p.name, p.default)) for p in parameters)
        return f(**dict((k, v) for k, v in _ if v is not inspect._empty))

    return _kwargs
