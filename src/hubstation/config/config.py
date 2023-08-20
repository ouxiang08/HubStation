from enum import Enum

from dynaconf import Dynaconf
import os
import shutil
import sys
from threading import Lock
import ruamel.yaml

# 种子名/文件名要素分隔字符
SPLIT_CHARS = r"\.|\s+|\(|\)|\[|]|-|\+|【|】|/|～|;|&|\||#|_|「|」|~"
# 默认User-Agent
DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"
# 收藏了的媒体的目录名，名字可以改，在Emby中点击红星则会自动将电影转移到此分类下，需要在Emby Webhook中配置用户行为通知
RMT_FAVTYPE = '精选'
# TMDB域名地址
TMDB_API_DOMAINS = ['api.themoviedb.org', 'api.tmdb.org', 'tmdb.nastool.cn', 'tmdb.nastool.workers.dev']
TMDB_IMAGE_DOMAIN = 'image.tmdb.org'
# 添加下载时增加的标签，开始只监控NAStool添加的下载时有效
PT_TAG = "HS"

settings = Dynaconf(
    settings_files=['settings.yml'],
)


class OsType(Enum):
    WINDOWS = "Windows"
    LINUX = "Linux"
    SYNOLOGY = "Synology"
    MACOS = "MacOS"
    DOCKER = "Docker"


# WebDriver路径
WEBDRIVER_PATH = {
    "Docker": "/usr/lib/chromium/chromedriver",
    "Synology": "/var/packages/NASTool/target/bin/chromedriver"
}

# Xvfb虚拟显示路程
XVFB_PATH = [
    "/usr/bin/Xvfb",
    "/usr/local/bin/Xvfb"
]

# 线程锁
lock = Lock()

# 全局实例
_CONFIG = None


def singleconfig(cls):
    def _singleconfig(*args, **kwargs):
        global _CONFIG
        if not _CONFIG:
            with lock:
                _CONFIG = cls(*args, **kwargs)
        return _CONFIG

    return _singleconfig


@singleconfig
class Config(object):
    _config = {}
    _config_path = None
    _user = None

    def __init__(self):
        self._config_path = os.environ.get('NASTOOL_CONFIG')
        if not os.environ.get('TZ'):
            os.environ['TZ'] = 'Asia/Shanghai'
        self.init_syspath()
        self.init_config()

    def init_config(self):
        try:
            if not self._config_path:
                print("【Config】NASTOOL_CONFIG 环境变量未设置，程序无法工作，正在退出...")
                quit()
            if not os.path.exists(self._config_path):
                os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
                cfg_tp_path = os.path.join(self.get_inner_config_path(), "config.yaml")
                cfg_tp_path = cfg_tp_path.replace("\\", "/")
                shutil.copy(cfg_tp_path, self._config_path)
                print("【Config】config.yaml 配置文件不存在，已将配置文件模板复制到配置目录...")
            with open(self._config_path, mode='r', encoding='utf-8') as cf:
                try:
                    # 读取配置
                    print("正在加载配置：%s" % self._config_path)
                    self._config = ruamel.yaml.YAML().load(cf)
                except Exception as e:
                    print("【Config】配置文件 config.yaml 格式出现严重错误！请检查：%s" % str(e))
                    self._config = {}
        except Exception as err:
            print("【Config】加载 config.yaml 配置出错：%s" % str(err))
            return False

    def init_syspath(self):
        with open(os.path.join(self.get_root_path(),
                               "third_party.txt"), "r") as f:
            for third_party_lib in f.readlines():
                module_path = os.path.join(self.get_root_path(),
                                           "third_party",
                                           third_party_lib.strip()).replace("\\", "/")
                if module_path not in sys.path:
                    sys.path.append(module_path)

    @property
    def current_user(self):
        return self._user

    @current_user.setter
    def current_user(self, user):
        self._user = user

    def get_proxies(self):
        return self.get_config('app').get("proxies")

    def get_ua(self):
        return self.get_config('app').get("user_agent") or DEFAULT_UA

    def get_config(self, node=None):
        if not node:
            return self._config
        return self._config.get(node, {})

    def save_config(self, new_cfg):
        self._config = new_cfg
        with open(self._config_path, mode='w', encoding='utf-8') as sf:
            yaml = ruamel.yaml.YAML()
            return yaml.dump(new_cfg, sf)

    def get_config_path(self):
        return os.path.dirname(self._config_path)

    def get_temp_path(self):
        return os.path.join(self.get_config_path(), "temp")

    @staticmethod
    def get_root_path():
        return os.path.dirname(os.path.realpath(__file__))

    def get_inner_config_path(self):
        return os.path.join(self.get_root_path(), "config")

    def get_script_path(self):
        return os.path.join(self.get_root_path(), "scripts", "sqls")

    def get_user_plugin_path(self):
        return os.path.join(self.get_config_path(), "plugins")

    def get_domain(self):
        domain = (self.get_config('app') or {}).get('domain')
        if domain and not domain.startswith('http'):
            domain = "http://" + domain
        if domain and str(domain).endswith("/"):
            domain = domain[:-1]
        return domain

    @staticmethod
    def get_timezone():
        return os.environ.get('TZ')

    @staticmethod
    def update_favtype(favtype):
        global RMT_FAVTYPE
        if favtype:
            RMT_FAVTYPE = favtype

    def get_tmdbapi_url(self):
        return f"https://{self.get_config('app').get('tmdb_domain') or TMDB_API_DOMAINS[0]}/3"

    def get_tmdbimage_url(self, path, prefix="w500"):
        if not path:
            return ""
        tmdb_image_url = self.get_config("app").get("tmdb_image_url")
        if tmdb_image_url:
            return tmdb_image_url + f"/t/p/{prefix}{path}"
        return f"https://{TMDB_IMAGE_DOMAIN}/t/p/{prefix}{path}"

    @property
    def category_path(self):
        category = self.get_config('media').get("category")
        if category:
            return os.path.join(Config().get_config_path(), f"{category}.yaml")
        return None
