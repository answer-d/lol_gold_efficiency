from logging import getLogger
from functools import wraps
import inspect

# logger = getLogger("default")
logger = getLogger("debug")


def logging(func):
    """メソッドに対して指定するデコレータ。対象メソッドの開始と終了をロギングする
    ログレベルは「DEBUG」"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug("{} start. args={}, kwargs={}".format(func.__qualname__, args, kwargs))
        # logger.debug("## {}".format(inspect.getfullargspec(func)))

        rtn = func(*args, **kwargs)

        logger.debug("{} end. return={}".format(func.__qualname__, rtn))
        return rtn
    return wrapper
