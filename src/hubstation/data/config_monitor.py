import json
import os
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from werkzeug.security import generate_password_hash

from hubstation import log
from hubstation.config.config import Config
from hubstation.utils.cache_manager import ConfigLoadCache, CategoryLoadCache
from hubstation.utils.commons import INSTANCES


class ConfigMonitor(FileSystemEventHandler):
    """
    配置文件变化响应
    """

    def __init__(self):
        FileSystemEventHandler.__init__(self)

    def on_modified(self, event):
        if event.is_directory:
            return
        src_path = event.src_path
        file_name = os.path.basename(src_path)
        file_head, file_ext = os.path.splitext(os.path.basename(file_name))
        if file_ext != ".yaml":
            return
        # 配置文件10秒内只能加载一次
        if file_name == "config.yaml" and not ConfigLoadCache.get(src_path):
            ConfigLoadCache.set(src_path, True)
            CategoryLoadCache.set("ConfigLoadBlock", True, ConfigLoadCache.ttl)
            log.warn(f"【System】进程 {os.getpid()} 检测到系统配置文件已修改，正在重新加载...")
            time.sleep(1)
            # 重新加载配置
            Config().init_config()
            # 重载singleton服务
            for instance in INSTANCES.values():
                if hasattr(instance, "init_config"):
                    instance.init_config()
        # 正在使用的二级分类策略文件3秒内只能加载一次，配置文件加载时，二级分类策略文件不加载
        elif file_name == os.path.basename(Config().category_path) \
                and not CategoryLoadCache.get(src_path) \
                and not CategoryLoadCache.get("ConfigLoadBlock"):
            CategoryLoadCache.set(src_path, True)
            log.warn(f"【System】进程 {os.getpid()} 检测到二级分类策略 {file_head} 配置文件已修改，正在重新加载...")
            time.sleep(1)
            # 重新加载二级分类策略
            # Category().init_config()


def start_config_monitor():
    """
    启动服务
    """
    global _observer
    # 配置文件监听
    _observer.schedule(ConfigMonitor(), path=Config().get_config_path(), recursive=False)
    _observer.daemon = True
    _observer.start()
