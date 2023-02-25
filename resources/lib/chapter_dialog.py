# Gnu General Public License - see LICENSE.TXT

import os
import threading
import json
import datetime

import xbmcgui
import xbmc
import xbmcaddon
import xbmcvfs

from .kodi_utils import HomeWindow
from .downloadutils import DownloadUtils
from .simple_logging import SimpleLogging

log = SimpleLogging(__name__)


def get_chapter_items():
    download_utils = DownloadUtils()
    home_screen = HomeWindow()

    item_id = home_screen.get_property("currently_playing_id")
    log.debug("ChapterDialogMonitor: currently_playing_id : {0}", item_id)
    if not item_id:
        return []

    url = "{server}/emby/Users/{userid}/Items/" + item_id + "?format=json"
    response_data = download_utils.download_url(url)
    json_data = json.loads(response_data)
    log.debug("ChapterDialogMonitor: item_info : {0}", json_data)
    if json_data is None:
        return []

    item_chapters = json_data.get("Chapters")
    if item_chapters is None or len(item_chapters) == 0:
        return []

    server = download_utils.get_server()

    chapters = []
    for chap in item_chapters:

        name = chap.get("Name", None)
        chap_type = chap.get("MarkerType", None)
        chap_resume = chap.get("StartPositionTicks", -1)
        chap_img_tag = chap.get("ImageTag", None)
        chap_index = chap.get("ChapterIndex", -1)

        if name and chap_type and chap_resume != -1:
            chap_display_name = name + " (" + chap_type + ")"
            li = xbmcgui.ListItem(chap_display_name, offscreen=True)

            resume_point = int((chap_resume / 1000) / 10000)
            li.setProperty("resume", str(resume_point))

            chap_time = str(datetime.timedelta(seconds=resume_point))
            li.setLabel2(chap_time)

            if chap_img_tag and chap_index != -1:
                img_url = "%s/emby/Items/%s/Images/Chapter/%s?maxWidth=380&tag=%s"
                img_url = img_url % (server, item_id, chap_index, chap_img_tag)
                log.debug("ChapterDialogMonitor: chap_img_url : {0}", img_url)
                art = {}
                art["thumb"] = img_url
                li.setArt(art)

            chapters.append(li)

    return chapters


def get_current_chapter(chapters):
    player = xbmc.Player()
    if player.isPlaying():
        current_position = player.getTime()
        index = 0
        for x in range(1, len(chapters)):
            chap = chapters[x]
            resume = int(chap.getProperty("resume"))
            log.debug("ChapterDialogMonitor: get_current_chapter : {0} - {1}", resume, current_position)
            if current_position < resume:
                break
            index += 1
    return index


class ChapterDialogMonitor(threading.Thread):

    stop_thread = False

    def run(self):
        log.debug("ChapterDialogMonitor Thread Started")

        home_screen = HomeWindow()
        kodi_monitor = xbmc.Monitor()
        while not kodi_monitor.abortRequested() and not self.stop_thread:

            if xbmc.getCondVisibility("Window.IsActive(videoosd)"):  # videoosd | fullscreenvideo

                item_id = home_screen.get_property("currently_playing_id")
                if xbmc.getCondVisibility("Window.IsVisible(VideoBookmarks)") and item_id:
                    xbmc.executebuiltin("Dialog.Close(VideoBookmarks,true)")

                    try:
                        plugin_path = xbmcvfs.translatePath(os.path.join(xbmcaddon.Addon().getAddonInfo('path')))
                        action_menu = ChapterDialog("ChapterDialog.xml", plugin_path, "default", "720p")
                        action_menu.doModal()
                    except Exception as e:
                        raise e

                kodi_monitor.waitForAbort(0.1)
            else:
                kodi_monitor.waitForAbort(2)

        log.debug("ChapterDialogMonitor Thread Exited")

    def stop_monitor(self):
        log.debug("ContextMonitor Stop Called")
        self.stop_thread = True


class ChapterDialog(xbmcgui.WindowXMLDialog):

    chapter_list = None

    def __init__(self, *args, **kwargs):
        log.debug("ChapterDialog: __init__")
        xbmcgui.WindowXML.__init__(self, *args, **kwargs)

    def onInit(self):
        log.debug("ChapterDialog: onInit")
        self.action_exitkeys_id = [10, 13]

        chapter_items = get_chapter_items()
        selected_chap = get_current_chapter(chapter_items)

        self.chapter_list = self.getControl(1234)
        self.chapter_list.addItems(chapter_items)
        self.chapter_list.selectItem(selected_chap)
        self.setFocus(self.chapter_list)

    def onFocus(self, control_id):
        pass

    def onAction(self, action):
        if action.getId() == 10:  # ACTION_PREVIOUS_MENU
            self.close()
        elif action.getId() == 92:  # ACTION_NAV_BACK
            self.close()

    def onClick(self, control_id):
        if control_id == 1234:
            selected = self.chapter_list.getSelectedItem()
            log.debug("ChapterDialog: Selected Item: {0}", selected)

            if selected:
                chap_name = selected.getLabel()
                resume = selected.getProperty("resume")
                log.debug("ChapterDialog: Chapter Selected : {0} - {1}", chap_name, resume)

                seek_to = int(resume)
                player = xbmc.Player()
                if player.isPlaying():
                    player.seekTime(seek_to)

            self.close()
