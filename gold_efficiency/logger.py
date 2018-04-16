from logging import getLogger
from functools import wraps
import inspect

# logger = getLogger("default")
logger = getLogger("debug")


def logging(func, self_cut=False):
    """メソッドに対して指定するデコレータ。対象メソッドの開始と終了をロギングする
    ログレベルは「DEBUG」"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug("{} start. args={}, kwargs={}".format(func.__qualname__, args, kwargs))
        logger.debug(inspect.getfullargspec(func))

        rtn = func(*args[1:], **kwargs) if self_cut else func(*args, **kwargs)

        logger.debug("{} end. return={}".format(func.__qualname__, rtn))
        return rtn
    return wrapper


def logging_class(klass):
    """クラスに対して指定するデコレータ。クラス内の全メソッドの開始と終了をロギングする"""
    if inspect.isclass(klass):
        logger.debug("process {}".format(klass.__name__))
        for m in klass.__dict__:
            func = getattr(klass, m)
            logger.debug("{}.{} = {}".format(klass.__name__, m, func))
            if callable(func) and not inspect.isclass(func) and inspect.isroutine(func):
                logger.debug("-> decorate {}".format(func.__qualname__))
                if inspect.getfullargspec(func).args[0] != 'self':
                    setattr(klass, m, logging(func, True))
                else:
                    setattr(klass, m, logging(func, False))
        return klass
    else:
        logger.error("{} is not class".format(klass))
