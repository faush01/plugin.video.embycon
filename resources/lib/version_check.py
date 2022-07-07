# Gnu General Public License - see LICENSE.TXT

import xbmc
import xbmcgui

import threading
import json

from .downloadutils import DownloadUtils
from .simple_logging import SimpleLogging
from .clientinfo import ClientInformation

log = SimpleLogging(__name__)


class VersionCheck(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        try:
            self.do_check()
        except:
            pass

    def do_check(self):
        log.debug("VersionCheck Running")

        # get server info
        # /emby/system/info/public
        download_utils = DownloadUtils()

        url = "{server}/emby/system/info/public?format=json"
        json_data = download_utils.download_url(url,authenticate=False)
        server_info = json.loads(json_data)
        log.debug("VersionCheck : Server Info : {0}", server_info)

        if server_info is not None:
            sid_data = server_info.get("Id", "")
            sv_data = server_info.get("Version", "")

            client = ClientInformation()
            cv_data = client.get_version()
            cid_data = client.get_device_id()

            kv_data = xbmc.getInfoLabel('System.BuildVersion').split(" ")[0]

            version_check_data = {
                "cid": cid_data,
                "cv": cv_data,
                "sid": sid_data,
                "sv": sv_data,
                "kv": kv_data
            }
            log.debug("VersionCheck : version_check_data : {0}", version_check_data)

            check_url = "https://prod-31.centralus.logic.azure.com:443/workflows/3bd53db4c2b64c40a8286c5e2e129b26/triggers/manual/paths/invoke?api-version=2016-10-01&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=XcMLM6TT_NYvqeIERGoCm9Tuk59sFtNGIXuG_-E3tq8"
            version_result = download_utils.download_url(url=check_url, method="POST", authenticate=False, post_body=version_check_data)
            version_check_info = json.loads(version_result)
            log.debug("VersionCheck : version_check_info : {0}", version_check_info)

            if version_check_info is not None and version_check_info.get("message", None):
                xbmcgui.Dialog().notification("Version Check",
                                              version_check_info.get("message", ""),
                                              icon="special://home/addons/plugin.video.embycon/icon.png")

        log.debug("VersionCheck Exited")
