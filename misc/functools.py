from functools import update_wrapper

from toolz.functoolz import compose


class decorable:
    def __init__(self, function):
        self._function = function
        update_wrapper(self, function)

    def __call__(self, *args, **kwargs):
        return self._function(*args, **kwargs)

    def before(self, *fs):
        return self.__class__(compose(self._function, *reversed(fs)))

    def after(self, *fs):
        return self.__class__(compose(*reversed(fs), self._function))
