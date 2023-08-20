import threading
import time
from collections import OrderedDict

# 线程锁
from hubstation.utils.exception_utils import ExceptionUtils

lock = threading.RLock()

# 全局实例
INSTANCES = OrderedDict()


# 单例模式注解
def singleton(cls):
    # 创建字典用来保存类的实例对象
    global INSTANCES

    def _singleton(*args, **kwargs):
        # 先判断这个类有没有对象
        if cls not in INSTANCES:
            with lock:
                if cls not in INSTANCES:
                    INSTANCES[cls] = cls(*args, **kwargs)
                    pass
        # 将实例对象返回
        return INSTANCES[cls]

    return _singleton


class DbPersist(object):
    """
    数据库持久化装饰器
    """

    def __init__(self, db):
        self.db = db

    def __call__(self, f):
        def persist(*args, **kwargs):
            try:
                ret = f(*args, **kwargs)
                self.db.commit()
                return True if ret is None else ret
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
                self.db.rollback()
                return False

        return persist
