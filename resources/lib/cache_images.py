# coding=utf-8
# Gnu General Public License - see LICENSE.TXT

import urllib.request
import urllib.parse
import urllib.error
import http.client
import base64
import sys
import threading
import time

import xbmcgui
import xbmcplugin
import xbmc
import xbmcaddon

from .downloadutils import DownloadUtils
from .simple_logging import SimpleLogging
from .jsonrpc import JsonRpc
from .translation import string_load
from .datamanager import DataManager
from .utils import get_art, double_urlencode
from .kodi_utils import HomeWindow

downloadUtils = DownloadUtils()
log = SimpleLogging(__name__)


class CacheArtwork(threading.Thread):

    stop_all_activity = False

    def __init__(self):
        log.debug("CacheArtwork init")
        self.stop_all_activity = False
        super(CacheArtwork, self).__init__()

    def stop_activity(self):
        self.stop_all_activity = True

    def run(self):
        log.debug("CacheArtwork background thread started")
        last_update = 0
        home_window = HomeWindow()
        settings = xbmcaddon.Addon()
        latest_content_hash = "never"
        check_interval = int(settings.getSetting('cacheImagesOnScreenSaver_interval'))
        check_interval = check_interval * 60
        monitor = xbmc.Monitor()
        monitor.waitForAbort(5)

        while not self.stop_all_activity and not monitor.abortRequested() and xbmc.getCondVisibility("System.ScreenSaverActive"):
            content_hash = home_window.get_property("embycon_widget_reload")
            if (check_interval != 0 and (time.time() - last_update) > check_interval) or (latest_content_hash != content_hash):
                log.debug("CacheArtwork background thread - triggered")
                if monitor.waitForAbort(10):
                    break
                if self.stop_all_activity or monitor.abortRequested():
                    break
                self.cache_artwork_background()
                last_update = time.time()
                latest_content_hash = content_hash

            monitor.waitForAbort(5)

        log.debug("CacheArtwork background thread exited : stop_all_activity : {0}", self.stop_all_activity)

    @staticmethod
    def delete_cached_images(item_id):
        log.debug("cache_delete_for_links")

        progress = xbmcgui.DialogProgress()
        progress.create(string_load(30281))
        progress.update(30, string_load(30347))

        item_image_url_part = "emby/Items/%s/Images/" % item_id
        item_image_url_part = item_image_url_part.replace("/", "%2f")
        # log.debug("texture ids: {0}", item_image_url_part)

        # is the web server enabled
        web_query = {"setting": "services.webserver"}
        result = JsonRpc('Settings.GetSettingValue').execute(web_query)
        xbmc_webserver_enabled = result['result']['value']
        if not xbmc_webserver_enabled:
            xbmcgui.Dialog().ok(string_load(30294), string_load(30295))
            return

        params = {"properties": ["url"]}
        json_result = JsonRpc('Textures.GetTextures').execute(params)
        textures = json_result.get("result", {}).get("textures", [])
        # log.debug("texture ids: {0}", textures)

        progress.update(70, string_load(30346))

        delete_count = 0
        for texture in textures:
            texture_id = texture["textureid"]
            texture_url = texture["url"]
            if item_image_url_part in texture_url:
                delete_count += 1
                log.debug("removing texture id: {0}", texture_id)
                params = {"textureid": int(texture_id)}
                JsonRpc('Textures.RemoveTexture').execute(params)

        del textures

        progress.update(100, string_load(30125))
        progress.close()

        xbmcgui.Dialog().ok(string_load(30281), string_load(30344) % delete_count)

    def remove_unused_artwork(self, p_dialog):
        delete_canceled = False

        params = {"properties": ["url"]}
        json_result = JsonRpc('Textures.GetTextures').execute(params)
        textures = json_result.get("result", {}).get("textures", [])
        total_textures = len(textures)

        emby_texture_urls = self.get_emby_artwork(p_dialog, limit=False)

        # log.debug("kodi textures: {0}", textures)
        # log.debug("emby texture urls: {0}", emby_texture_urls)

        total_removed = 0
        unused_texture_ids = set()
        index = 0

        if emby_texture_urls is not None:
            for texture in textures:
                url = texture.get("url")
                url = urllib.parse.unquote(url)
                url = url.replace("image://", "")
                url = url[0:-1]
                if url.find("/emby/") > -1 and url not in emby_texture_urls or url.find("localhost:24276") > -1:
                    log.debug("adding unused texture url: {0}", url)
                    unused_texture_ids.add(texture["textureid"])

            log.debug("unused texture ids: {0}", unused_texture_ids)


            total_removed = len(unused_texture_ids)
            for texture_id in unused_texture_ids:
                params = {"textureid": int(texture_id)}
                JsonRpc('Textures.RemoveTexture').execute(params)
                percentage = int((float(index) / float(total_removed)) * 100)
                message = "%s of %s" % (index, total_removed)
                p_dialog.update(percentage, message)
                index += 1
                if isinstance(p_dialog, xbmcgui.DialogProgress) and p_dialog.iscanceled():
                    delete_canceled = True
                    break
                if self.stop_all_activity:
                    break

        del textures
        del emby_texture_urls
        del unused_texture_ids

        result_report = []
        result_report.append(string_load(30385) + str(total_textures))
        result_report.append(string_load(30386) + str(total_removed))
        result_report.append(string_load(30387) + str(index))

        if delete_canceled:
            xbmc.sleep(2000)

        return result_report

    def cache_artwork_interactive(self):
        log.debug("cache_artwork_interactive")

        xbmcplugin.endOfDirectory(int(sys.argv[1]), cacheToDisc=False)

        # is the web server enabled
        web_query = {"setting": "services.webserver"}
        result = JsonRpc('Settings.GetSettingValue').execute(web_query)
        xbmc_webserver_enabled = result['result']['value']
        if not xbmc_webserver_enabled:
            xbmcgui.Dialog().ok(string_load(30294), string_load(30295))
            xbmc.executebuiltin('ActivateWindow(servicesettings)')
            return

        result_report = []

        # ask questions
        question_delete_unused = xbmcgui.Dialog().yesno(string_load(30296), string_load(30297))
        question_cache_images = xbmcgui.Dialog().yesno(string_load(30299), string_load(30300))

        # now do work - delete unused
        if question_delete_unused:
            delete_pdialog = xbmcgui.DialogProgress()
            delete_pdialog.create(string_load(30298), "")
            remove_result = self.remove_unused_artwork(delete_pdialog)
            if remove_result:
                result_report.extend(remove_result)
            delete_pdialog.close()
            del delete_pdialog

        # now do work - cache images
        if question_cache_images:
            cache_pdialog = xbmcgui.DialogProgress()
            cache_pdialog.create(string_load(30301), "")
            cache_report = self.cache_artwork(cache_pdialog)
            cache_pdialog.close()
            del cache_pdialog
            if cache_report:
                result_report.extend(cache_report)

        if len(result_report) > 0:
            msg = "\r\n".join(result_report)
            xbmcgui.Dialog().textviewer(string_load(30125), msg, usemono=True)

    def cache_artwork_background(self):
        log.debug("cache_artwork_background")
        dp = xbmcgui.DialogProgressBG()
        dp.create(string_load(30301), "")
        result_text = None
        try:
            #self.remove_unused_artwork(dp)
            result_text = self.cache_artwork(dp)
        except Exception as err:
            log.error("Cache Images Failed : {0}", err)
        dp.close()
        del dp
        if result_text is not None:
            log.debug("Cache Images reuslt : {0}", " - ".join(result_text))

    def get_emby_artwork(self, progress, limit=False):
        log.debug("get_emby_artwork")

        url = ""
        url += "{server}/emby/Users/{userid}/Items"
        url += "?Recursive=true"
        url += "&EnableUserData=False"
        url += "&Fields=BasicSyncInfo"
        url += "&IncludeItemTypes=Movie,Series,Season,Episode,BoxSet"
        url += "&ImageTypeLimit=1"
        url += "&format=json"

        settings = xbmcaddon.Addon()
        max_image_width = int(settings.getSetting('max_image_width'))

        data_manager = DataManager()
        results = data_manager.get_content(url)
        if results is None:
            results = []

        if isinstance(results, dict):
            results = results.get("Items")

        # log.debug("Cache Emby Images Items: {0}", results)

        server = downloadUtils.get_server()
        log.debug("Emby Item Count Count: {0}", len(results))

        if self.stop_all_activity:
            return None

        progress.update(0, string_load(30359))

        texture_urls = set()

        image_types = {"thumb", "poster", "banner", "clearlogo", "tvshow.poster", "tvshow.banner", "tvshow.landscape"}
        for item in results:
            art = get_art(item, server, max_image_width)
            for art_type in art:
                if not limit:
                    texture_urls.add(art[art_type])
                elif art_type in image_types:
                    texture_urls.add(art[art_type])

        return texture_urls

    def cache_artwork(self, progress):
        log.debug("cache_artwork")

        # is the web server enabled
        web_query = {"setting": "services.webserver"}
        result = JsonRpc('Settings.GetSettingValue').execute(web_query)
        xbmc_webserver_enabled = result['result']['value']
        if not xbmc_webserver_enabled:
            log.error("Kodi web server not enabled, can not cache images")
            return

        # get the port
        web_port = {"setting": "services.webserverport"}
        result = JsonRpc('Settings.GetSettingValue').execute(web_port)
        xbmc_port = result['result']['value']
        log.debug("xbmc_port: {0}", xbmc_port)

        # get the user
        web_user = {"setting": "services.webserverusername"}
        result = JsonRpc('Settings.GetSettingValue').execute(web_user)
        xbmc_username = result['result']['value']
        log.debug("xbmc_username: {0}", xbmc_username)

        # get the password
        web_pass = {"setting": "services.webserverpassword"}
        result = JsonRpc('Settings.GetSettingValue').execute(web_pass)
        xbmc_password = result['result']['value']

        progress.update(0, string_load(30356))

        params = {"properties": ["url"]}
        json_result = JsonRpc('Textures.GetTextures').execute(params)
        textures = json_result.get("result", {}).get("textures", [])
        log.debug("Textures.GetTextures Count: {0}", len(textures))

        if self.stop_all_activity:
            return

        progress.update(0, string_load(30357))

        texture_urls = set()
        for texture in textures:
            url = texture.get("url")
            url = urllib.parse.unquote(url)
            url = url.replace("image://", "")
            url = url[0:-1]
            texture_urls.add(url)

        del textures
        del json_result

        log.debug("texture_urls Count: {0}", len(texture_urls))

        if self.stop_all_activity:
            return

        progress.update(0, string_load(30358))

        emby_texture_urls = self.get_emby_artwork(progress, limit=True)
        if emby_texture_urls is None:
            return

        missing_texture_urls = set()
        # image_types = ["thumb", "poster", "banner", "clearlogo", "tvshow.poster", "tvshow.banner", "tvshow.landscape"]
        for image_url in emby_texture_urls:
            if image_url not in texture_urls and not image_url.endswith("&Tag=") and len(image_url) > 0:
                missing_texture_urls.add(image_url)

            if self.stop_all_activity:
                return

        # log.debug("texture_urls: {0}", texture_urls)
        # log.debug("missing_texture_urls: {0}", missing_texture_urls)
        # log.debug("Number of existing textures: {0}", len(texture_urls))
        # log.debug("Number of missing textures: {0}", len(missing_texture_urls))

        kodi_http_server = "localhost:" + str(xbmc_port)
        log.debug("Local Kodi Web Server :  {0}", kodi_http_server)
        headers = {}
        if xbmc_password:
            auth = "%s:%s" % (xbmc_username, xbmc_password)
            headers = {'Authorization': 'Basic %s' % base64.b64encode(auth.encode("utf-8")).decode("utf-8")}
        log.debug("Local Kodi Web Server Headers :  {0}", headers)

        total = len(missing_texture_urls)
        index = 1

        count_done = 0
        for get_url in missing_texture_urls:
            log.debug("texture_url: {0}", get_url)
            url = double_urlencode(get_url)
            kodi_texture_url = ("/image/image://%s" % url)
            log.debug("kodi_texture_url: {0}", kodi_texture_url)

            percentage = int((float(index) / float(total)) * 100)
            message = "%s of %s" % (index, total)
            progress.update(percentage, message)

            conn = http.client.HTTPConnection(kodi_http_server, timeout=20)
            conn.request(method="GET", url=kodi_texture_url, headers=headers)
            data = conn.getresponse()
            if data.status == 200:
                count_done += 1
            log.debug("Get Image Result: {0}", data.status)

            index += 1
            if isinstance(progress, xbmcgui.DialogProgress) and progress.iscanceled():
                break

            if self.stop_all_activity:
                break

        result_report = []
        result_report.append(string_load(30302) + str(len(texture_urls)))
        result_report.append(string_load(30303) + str(len(missing_texture_urls)))
        result_report.append(string_load(30304) + str(count_done))
        return result_report
