import os
from threading import Lock
from enum import Enum
import json

from apscheduler.schedulers.background import BackgroundScheduler

from hubstation import log
from hubstation.config.config import Config, PT_TAG, PT_TRANSFER_INTERVAL
from hubstation.constants import DownloaderType
from hubstation.helper.submodule_helper import SubmoduleHelper
from hubstation.helper.thread_helper import ThreadHelper
from hubstation.utils.commons import singleton
from hubstation.utils.exception_utils import ExceptionUtils
from hubstation.utils.string_utils import StringUtils
from hubstation.utils.torrent import Torrent

lock = Lock()
client_lock = Lock()


@singleton
class Downloader:
    # 客户端实例
    clients = {}

    _downloader_schema = []
    _download_order = None
    _download_settings = {}
    _downloader_confs = {}
    _monitor_downloader_ids = []
    # 下载器ID-名称枚举类
    _DownloaderEnum = None
    _scheduler = None

    def __init__(self):
        self._downloader_schema = SubmoduleHelper.import_submodules(
            'app.downloader.client',
            filter_func=lambda _, obj: hasattr(obj, 'client_id')
        )
        log.debug(f"【Downloader】加载下载器类型：{self._downloader_schema}")
        self.init_config()

    def init_config(self):
        # 清空已存在下载器实例
        self.clients = {}
        # 下载器配置，生成实例
        self._downloader_confs = {}
        self._monitor_downloader_ids = []
        for downloader_conf in self.dbhelper.get_downloaders():
            if not downloader_conf:
                continue
            did = downloader_conf.ID
            name = downloader_conf.NAME
            enabled = downloader_conf.ENABLED
            # 下载器监控配置
            transfer = downloader_conf.TRANSFER
            only_nastool = downloader_conf.ONLY_NASTOOL
            match_path = downloader_conf.MATCH_PATH
            rmt_mode = downloader_conf.RMT_MODE
            # rmt_mode_name = ModuleConf.RMT_MODES.get(rmt_mode).value if rmt_mode else ""
            # 输出日志
            if transfer:
                log_content = ""
                if only_nastool:
                    log_content += "启用标签隔离，"
                if match_path:
                    log_content += "启用目录隔离，"
                # log.info(f"【Downloader】读取到监控下载器：{name}{log_content}转移方式：{rmt_mode_name}")
                if enabled:
                    self._monitor_downloader_ids.append(did)
                else:
                    log.info(f"【Downloader】下载器：{name} 不进行监控：下载器未启用")
            # 下载器登录配置
            config = json.loads(downloader_conf.CONFIG)
            dtype = downloader_conf.TYPE
            self._downloader_confs[str(did)] = {
                "id": did,
                "name": name,
                "type": dtype,
                "enabled": enabled,
                "transfer": transfer,
                "only_nastool": only_nastool,
                "match_path": match_path,
                "rmt_mode": rmt_mode,
                # "rmt_mode_name": rmt_mode_name,
                "config": config,
                "download_dir": json.loads(downloader_conf.DOWNLOAD_DIR)
            }
        # 下载器ID-名称枚举类生成
        self._DownloaderEnum = Enum('DownloaderIdName',
                                    {did: conf.get("name") for did, conf in self._downloader_confs.items()})
        pt = Config().get_config('pt')
        if pt:
            self._download_order = pt.get("download_order")
        # 下载设置
        self._download_settings = {
            "-1": {
                "id": -1,
                "name": "预设",
                "category": '',
                "tags": PT_TAG,
                "is_paused": 0,
                "upload_limit": 0,
                "download_limit": 0,
                "ratio_limit": 0,
                "seeding_time_limit": 0,
                "downloader": "",
                "downloader_name": "",
                "downloader_type": ""
            }
        }
        download_settings = self.dbhelper.get_download_setting()
        for download_setting in download_settings:
            downloader_id = download_setting.DOWNLOADER
            download_conf = self._downloader_confs.get(str(downloader_id))
            if download_conf:
                downloader_name = download_conf.get("name")
                downloader_type = download_conf.get("type")
            else:
                downloader_name = ""
                downloader_type = ""
                downloader_id = ""
            self._download_settings[str(download_setting.ID)] = {
                "id": download_setting.ID,
                "name": download_setting.NAME,
                "category": download_setting.CATEGORY,
                "tags": download_setting.TAGS,
                "is_paused": download_setting.IS_PAUSED,
                "upload_limit": download_setting.UPLOAD_LIMIT,
                "download_limit": download_setting.DOWNLOAD_LIMIT,
                "ratio_limit": download_setting.RATIO_LIMIT / 100,
                "seeding_time_limit": download_setting.SEEDING_TIME_LIMIT,
                "downloader": downloader_id,
                "downloader_name": downloader_name,
                "downloader_type": downloader_type
            }
        # 启动下载器监控服务
        self.start_service()

    def __build_class(self, ctype, conf=None):
        for downloader_schema in self._downloader_schema:
            try:
                if downloader_schema.match(ctype):
                    return downloader_schema(conf)
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
        return None

    def start_service(self):
        """
        转移任务调度
        """
        # 移出现有任务
        self.stop_service()
        # 启动转移任务
        if not self._monitor_downloader_ids:
            return
        self._scheduler = BackgroundScheduler(timezone=Config().get_timezone())
        for downloader_id in self._monitor_downloader_ids:
            self._scheduler.add_job(func=self.transfer,
                                    args=[downloader_id],
                                    trigger='interval',
                                    seconds=PT_TRANSFER_INTERVAL)
        self._scheduler.print_jobs()
        self._scheduler.start()
        log.info("下载文件转移服务启动，目的目录：媒体库")

    def download(self,
                 media_info,
                 is_paused=None,
                 tag=None,
                 download_dir=None,
                 download_setting=None,
                 downloader_id=None,
                 upload_limit=None,
                 download_limit=None,
                 torrent_file=None,
                 in_from=None,
                 user_name=None,
                 proxy=None):
        """
        添加下载任务，根据当前使用的下载器分别调用不同的客户端处理
        :param media_info: 需下载的媒体信息，含URL地址
        :param is_paused: 是否暂停下载
        :param tag: 种子标签
        :param download_dir: 指定下载目录
        :param download_setting: 下载设置id，为None则使用-1默认设置，为"-2"则不使用下载设置
        :param downloader_id: 指定下载器ID下载
        :param upload_limit: 上传速度限制
        :param download_limit: 下载速度限制
        :param torrent_file: 种子文件路径
        :param in_from: 来源
        :param user_name: 用户名
        :param proxy: 是否使用代理，指定该选项为 True/False 会覆盖 site_info 的设置
        :return: 下载器类型, 种子ID，错误信息
        """

        def __download_fail(msg):
            """
            触发下载失败事件和发送消息
            """
            # self.eventmanager.send_event(EventType.DownloadFail, {
            #     "media_info": media_info.to_dict(),
            #     "reason": msg
            # })
            # if in_from:
            #     self.message.send_download_fail_message(media_info, f"添加下载任务失败：{msg}")

        # 触发下载事件
        # self.eventmanager.send_event(EventType.DownloadAdd, {
        #     "media_info": media_info.to_dict(),
        #     "is_paused": is_paused,
        #     "tag": tag,
        #     "download_dir": download_dir,
        #     "download_setting": download_setting,
        #     "downloader_id": downloader_id,
        #     "torrent_file": torrent_file
        # })

        # 标题
        title = media_info.org_string
        # 详情页面
        page_url = media_info.page_url
        # 默认值
        site_info, dl_files_folder, dl_files, retmsg = {}, "", [], ""

        if torrent_file:
            # 有种子文件时解析种子信息
            url = os.path.basename(torrent_file)
            content, dl_files_folder, dl_files, retmsg = Torrent().read_torrent_content(torrent_file)
        else:
            # 没有种子文件解析链接
            url = media_info.enclosure
            if not url:
                __download_fail("下载链接为空")
                return None, None, "下载链接为空"
            # 获取种子内容，磁力链不解析
            if url.startswith("magnet:"):
                content = url
            else:
                # 获取Cookie和ua等
                site_info = self.sites.get_sites(siteurl=url)
                # 下载种子文件，并读取信息
                _, content, dl_files_folder, dl_files, retmsg = Torrent().get_torrent_info(
                    url=url,
                    cookie=site_info.get("cookie"),
                    ua=site_info.get("ua"),
                    referer=page_url if site_info.get("referer") else None,
                    proxy=proxy if proxy is not None else site_info.get("proxy")
                )

        # 解析完成
        if retmsg:
            log.warn("【Downloader】%s" % retmsg)

        if not content:
            __download_fail(retmsg)
            return None, None, retmsg

        # 下载设置
        if not download_setting and media_info.site:
            # 站点的下载设置
            download_setting = self.sites.get_site_download_setting(media_info.site)
        if download_setting == "-2":
            # 不使用下载设置
            download_attr = {}
        elif download_setting:
            # 传入的下载设置
            download_attr = self.get_download_setting(download_setting) \
                            or self.get_download_setting(self.default_download_setting_id)
        else:
            # 默认下载设置
            download_attr = self.get_download_setting(self.default_download_setting_id)

        # 下载设置名称
        download_setting_name = download_attr.get('name')

        # 下载器实例
        if not downloader_id:
            downloader_id = download_attr.get("downloader")
        downloader_conf = self.get_downloader_conf(downloader_id)
        downloader = self.__get_client(downloader_id)

        if not downloader or not downloader_conf:
            __download_fail("请检查下载设置所选下载器是否有效且启用")
            return None, None, f"下载设置 {download_setting_name} 所选下载器失效"
        downloader_name = downloader_conf.get("name")

        # 开始添加下载
        try:
            # 下载设置中的分类
            category = download_attr.get("category")
            # 合并TAG
            tags = download_attr.get("tags")
            if tags:
                tags = str(tags).split(";")
                if tag:
                    if isinstance(tag, list):
                        tags.extend(tag)
                    else:
                        tags.append(tag)
            else:
                if tag:
                    if isinstance(tag, list):
                        tags = tag
                    else:
                        tags = [tag]

            # 暂停
            if is_paused is None:
                is_paused = StringUtils.to_bool(download_attr.get("is_paused"))
            else:
                is_paused = True if is_paused else False
            # 上传限速
            if not upload_limit:
                upload_limit = download_attr.get("upload_limit")
            # 下载限速
            if not download_limit:
                download_limit = download_attr.get("download_limit")
            # 分享率
            ratio_limit = download_attr.get("ratio_limit")
            # 做种时间
            seeding_time_limit = download_attr.get("seeding_time_limit")
            # 下载目录设置
            if not download_dir:
                download_info = self.__get_download_dir_info(media_info, downloader_conf.get("download_dir"))
                download_dir = download_info.get('path')
                # 从下载目录中获取分类标签
                if not category:
                    category = download_info.get('category')
            # 添加下载
            print_url = content if isinstance(content, str) else url
            if is_paused:
                log.info(f"【Downloader】下载器 {downloader_name} 添加任务并暂停：%s，目录：%s，Url：%s" % (
                    title, download_dir, print_url))
            else:
                log.info(f"【Downloader】下载器 {downloader_name} 添加任务：%s，目录：%s，Url：%s" % (
                    title, download_dir, print_url))
            # 下载ID
            download_id = None
            downloader_type = downloader.get_type()
            if downloader_type == DownloaderType.TR:
                ret = downloader.add_torrent(content,
                                             is_paused=is_paused,
                                             download_dir=download_dir,
                                             cookie=site_info.get("cookie"))
                if ret:
                    download_id = ret.hashString
                    downloader.change_torrent(tid=download_id,
                                              tag=tags,
                                              upload_limit=upload_limit,
                                              download_limit=download_limit,
                                              ratio_limit=ratio_limit,
                                              seeding_time_limit=seeding_time_limit)

            elif downloader_type == DownloaderType.QB:
                # 加标签以获取添加下载后的编号
                torrent_tag = "NT" + StringUtils.generate_random_str(5)
                if tags:
                    tags += [torrent_tag]
                else:
                    tags = [torrent_tag]
                # 布局默认原始
                ret = downloader.add_torrent(content,
                                             is_paused=is_paused,
                                             download_dir=download_dir,
                                             tag=tags,
                                             category=category,
                                             content_layout="Original",
                                             upload_limit=upload_limit,
                                             download_limit=download_limit,
                                             ratio_limit=ratio_limit,
                                             seeding_time_limit=seeding_time_limit,
                                             cookie=site_info.get("cookie"))
                if ret:
                    download_id = downloader.get_torrent_id_by_tag(torrent_tag)
            else:
                # 其它下载器，添加下载后需返回下载ID或添加状态
                ret = downloader.add_torrent(content,
                                             is_paused=is_paused,
                                             tag=tags,
                                             download_dir=download_dir,
                                             category=category)
                download_id = ret
            # 添加下载成功
            if ret:
                # 计算数据文件保存的路径
                save_dir = subtitle_dir = None
                visit_dir = self.get_download_visit_dir(download_dir)
                if visit_dir:
                    if dl_files_folder:
                        # 种子文件带目录
                        save_dir = os.path.join(visit_dir, dl_files_folder)
                        subtitle_dir = save_dir
                    elif dl_files:
                        # 种子文件为单独文件
                        save_dir = os.path.join(visit_dir, dl_files[0])
                        subtitle_dir = visit_dir
                    else:
                        save_dir = None
                        subtitle_dir = visit_dir
                # 登记下载历史，记录下载目录
                self.dbhelper.insert_download_history(media_info=media_info,
                                                      downloader=downloader_id,
                                                      download_id=download_id,
                                                      save_dir=save_dir)
                # 下载站点字幕文件
                if page_url \
                    and subtitle_dir \
                    and site_info \
                    and site_info.get("subtitle"):
                    ThreadHelper().start_thread(
                        self.sitesubtitle.download,
                        (
                            media_info,
                            site_info.get("id"),
                            site_info.get("cookie"),
                            site_info.get("ua"),
                            subtitle_dir
                        )
                    )
                # 发送下载消息
                if in_from:
                    media_info.user_name = user_name
                    self.message.send_download_message(in_from=in_from,
                                                       can_item=media_info,
                                                       download_setting_name=download_setting_name,
                                                       downloader_name=downloader_name)
                return downloader_id, download_id, ""
            else:
                __download_fail("请检查下载任务是否已存在")
                return downloader_id, None, f"下载器 {downloader_name} 添加下载任务失败，请检查下载任务是否已存在"
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            __download_fail(str(e))
            log.error(f"【Downloader】下载器 {downloader_name} 添加任务出错：%s" % str(e))
            return None, None, str(e)
