import os
import signal
import sys
import threading
import warnings
from hubstation import log
from hubstation.config.config import Config, APP_VERSION
from hubstation.data.config_monitor import start_config_monitor
from hubstation.db import init_db, update_db, init_data
from hubstation.helper.chrome_helper import init_chrome

warnings.filterwarnings('ignore')

# 运行环境判断
is_executable = getattr(sys, 'frozen', False)
is_windows_exe = is_executable and (os.name == "nt")
# if is_windows_exe:
#     # 托盘相关库
#     import threading
#     from package.trayicon import TrayIcon, NullWriter

if is_executable:
    # 可执行文件初始化环境变量
    config_path = os.path.join(os.path.dirname(sys.executable), "config").replace("\\", "/")
    os.environ["HUBSTATION_CONFIG"] = os.path.join(config_path, "config.yaml").replace("\\", "/")
    os.environ["HUBSTATION_LOG"] = os.path.join(config_path, "logs").replace("\\", "/")
    try:
        if not os.path.exists(config_path):
            os.makedirs(config_path)
    except Exception as err:
        print(str(err))


def sigal_handler(num, stack):
    """
    信号处理
    """
    log.warn('捕捉到退出信号：%s，开始退出...' % num)
    # 关闭配置文件监控
    log.info('关闭配置文件监控...')
    # stop_config_monitor()
    # 关闭服务
    log.info('关闭服务...')
    # WebAction.stop_service()
    # 退出主进程
    log.info('退出主进程...')
    # sys.exit(0) -> os._exit(0)
    # fix s6下python进程无法退出的问题
    os._exit(0)


def get_run_config(forcev4=False):
    """
    获取运行配置
    """
    _web_host = "::"
    _web_port = 3000
    _ssl_cert = None
    _ssl_key = None
    _debug = False

    app_conf = Config().get_config('app')
    if app_conf:
        if forcev4:
            _web_host = "0.0.0.0"
        elif app_conf.get("web_host"):
            _web_host = app_conf.get("web_host").replace('[', '').replace(']', '')
        _web_port = int(app_conf.get('web_port')) if str(app_conf.get('web_port', '')).isdigit() else 3000
        _ssl_cert = app_conf.get('ssl_cert')
        _ssl_key = app_conf.get('ssl_key')
        _ssl_key = app_conf.get('ssl_key')
        _debug = True if app_conf.get("debug") else False

    app_arg = dict(host=_web_host, port=_web_port, debug=_debug, threaded=True, use_reloader=False)
    if _ssl_cert:
        app_arg['ssl_context'] = (_ssl_cert, _ssl_key)
    return app_arg


# 退出事件
signal.signal(signal.SIGINT, sigal_handler)
signal.signal(signal.SIGTERM, sigal_handler)


def init_system():
    # 配置
    log.console('HubStation 当前版本号：%s' % APP_VERSION)
    # 数据库初始化
    init_db()
    # 数据库更新
    update_db()
    # 数据初始化
    init_data()


def start_service():
    log.console("开始启动服务...")
    # 启动服务
    # WebAction.start_service()
    # 监听配置文件变化
    start_config_monitor()


# 系统初始化
init_system()

# 启动服务
start_service()


# 本地运行
if __name__ == '__main__':
    # Windows启动托盘
    # if is_windows_exe:
    #     homepage = Config().get_config('app').get('domain')
    #     if not homepage:
    #         homepage = "http://localhost:%s" % str(Config().get_config('app').get('web_port'))
    #     log_path = os.environ.get("HUBSTATION_LOG")
    #
    #     sys.stdout = NullWriter()
    #     sys.stderr = NullWriter()
    #
    #
    #     def traystart():
    #         TrayIcon(homepage, log_path)
    #
    #
    #     if len(os.popen("tasklist| findstr %s" % os.path.basename(sys.executable), 'r').read().splitlines()) <= 2:
    #         p1 = threading.Thread(target=traystart, daemon=True)
    #         p1.start()

    # 初始化浏览器驱动
    init_chrome()

    # Flask启动
    # App.run(**get_run_config(is_windows_exe))
