from logging import getLogger
from functools import wraps
import inspect

# logger = getLogger("default")
logger = getLogger("debug")


def logging(func):
    """メソッドに対して指定するデコレータ。対象メソッドの開始と終了をロギングする
    ログレベルは「DEBUG」"""
    @wraps(func)
    def wrapper(obj, *args, **kwargs):
        logger.debug("{} start. obj={}, args={}, kwargs={}".format(func.__qualname__, obj, args, kwargs))
        logger.debug("argspec : {}".format(inspect.getfullargspec(func).args))

        if inspect.ismodule(func):
            logger.debug("this is module")
        if inspect.ismethod(func):
            logger.debug("this is method")
        if inspect.isfunction(func):
            logger.debug("this is function")
        if inspect.isgeneratorfunction(func):
            logger.debug("this is generated function")

        logger.debug(func.__class__.__name__)

        logger.debug("call function : {}({}, {})".format(func.__qualname__, args, kwargs))
        rtn = func(obj, *args, **kwargs)
        logger.debug("{} end. return={}".format(func.__qualname__, rtn))
        return rtn
    return wrapper


@logging
def logging_class(klass):
    """クラスに対して指定するデコレータ。クラス内の全メソッドの開始と終了をロギングする"""
    if inspect.isclass(klass):
        logger.debug("class={}".format(klass))
        for m in klass.__dict__:
            fn = getattr(klass, m)
            logger.debug("elem:{} -> attr:{}".format(m, fn))
            if callable(fn):
                logger.debug("{} is callable! execute setattr({}, {}, {})".format(m, klass, m, logging(fn)))
                setattr(klass, m, logging(fn))
        return klass
    else:
        logger.error("{} is not class".format(klass))
