"""Constants"""
from enum import Enum

DEFAULT_ENCODING = 'utf-8'


class DownloaderType(Enum):
    QB = 'Qbittorrent'
    TR = 'Transmission'
    UT = 'uTorrent'
    PAN115 = '115网盘'
    ARIA2 = 'Aria2'
    PIKPAK = 'PikPak'


class MediaType(Enum):
    TV = '电视剧'
    MOVIE = '电影'
    ANIME = '动漫'
    UNKNOWN = '未知'


class RmtMode(Enum):
    LINK = "硬链接"
    SOFTLINK = "软链接"
    COPY = "复制"
    MOVE = "移动"
    RCLONECOPY = "Rclone复制"
    RCLONE = "Rclone移动"
    MINIOCOPY = "Minio复制"
    MINIO = "Minio移动"


class SearchType(Enum):
    WX = "微信"
    WEB = "WEB"
    DB = "豆瓣"
    RSS = "电影/电视剧订阅"
    USERRSS = "自定义订阅"
    OT = "手动下载"
    TG = "Telegram"
    API = "第三方API请求"
    SLACK = "Slack"
    SYNOLOGY = "Synology Chat"
    PLUGIN = "插件"


# 处理进度Key字典
class ProgressKey(Enum):
    # 搜索
    Search = "search"
    # 转移
    FileTransfer = "filetransfer"
    # 媒体库同步
    MediaSync = "mediasync"
    # 站点Cookie获取
    SiteCookie = "sitecookie"
