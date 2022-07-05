# Gnu General Public License - see LICENSE.TXT

import xbmc
import xbmcgui
import xbmcaddon

import time
import threading

from .simple_logging import SimpleLogging

log = SimpleLogging(__name__)


class SkipIntroMonitor(threading.Thread):

    intro_start_ticks = 0
    intro_end_ticks = 0
    auto_skip = False
    original_play_path = None

    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        log.debug("SkipIntroMonitor Running")

        settings = xbmcaddon.Addon()
        addon_path = settings.getAddonInfo('path')
        skip_intro_dialog = None

        intro_start_sec = ((self.intro_start_ticks / 1000) / 10000)
        intro_end_sec = ((self.intro_end_ticks / 1000) / 10000)

        player = xbmc.Player()
        monitor = xbmc.Monitor()
        while not monitor.abortRequested():

            play_time = player.getTime()
            play_path = player.getPlayingFile()

            if play_path != self.original_play_path:
                log.debug("SkipIntroMonitor original file no longer playing: {0} {1}", play_path, self.original_play_path)
                break

            if skip_intro_dialog is None and (intro_start_sec < play_time < intro_end_sec):
                log.debug("SkipIntroMonitor doing skip intro action: {0} {1} {2}", intro_start_sec, play_time, intro_end_sec)
                if self.auto_skip:
                    log.debug("SkipIntroMonitor auto skip")
                    player.seekTime(intro_end_sec)
                else:
                    log.debug("SkipIntroMonitor show dialog")
                    skip_intro_dialog = SkipIntroDialog("SkipIntroDialog.xml", addon_path, "default", "720p")
                    skip_intro_dialog.show()

            # player skipped past intro end so exit the monitor
            if play_time > intro_end_sec:
                log.debug("SkipIntroMonitor player position past intro end time: {0} {1}", play_time, intro_end_sec)
                if skip_intro_dialog is not None:
                    skip_intro_dialog.close()
                break

            # dialog has been actioned so do the thing
            if skip_intro_dialog is not None and not skip_intro_dialog.dialog_open:
                log.debug("SkipIntroMonitor skip intro dialog result: {0}", skip_intro_dialog.confirm)
                if skip_intro_dialog.confirm:
                    player.seekTime(intro_end_sec)
                break

            monitor.waitForAbort(1.0)

        log.debug("SkipIntroMonitor Exited")

    def set_times(self, start, end):
        self.intro_start_ticks = start
        self.intro_end_ticks = end

    def set_auto_skip(self, auto_skip):
        self.auto_skip = auto_skip

    def set_play_path(self, path):
        self.original_play_path = path


class SkipIntroDialog(xbmcgui.WindowXMLDialog):

    dialog_open = False
    confirm = False
    action_exitkeys_id = None

    def __init__(self, *args, **kwargs):
        log.debug("SkipIntroPromptDialog: __init__")
        xbmcgui.WindowXML.__init__(self, *args, **kwargs)
        self.dialog_open = True

    def onInit(self):
        log.debug("SkipIntroPromptDialog: onInit")
        self.action_exitkeys_id = [10, 13]

    def onFocus(self, controlId):
        pass

    def doAction(self, actionID):
        pass

    def onMessage(self, message):
        log.debug("SkipIntroPromptDialog: onMessage: {0}", message)

    def onAction(self, action):

        if action.getId() == 10:  # ACTION_PREVIOUS_MENU
            self.dialog_open = False
            self.close()
        elif action.getId() == 92:  # ACTION_NAV_BACK
            self.dialog_open = False
            self.close()
        else:
            log.debug("SkipIntroPromptDialog: onAction: {0}", action.getId())

    def onClick(self, controlID):
        if controlID == 1:
            self.confirm = True
            self.dialog_open = False
            self.close()
