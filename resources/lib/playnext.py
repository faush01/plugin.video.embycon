# Gnu General Public License - see LICENSE.TXT

import os
import threading

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

from .simple_logging import SimpleLogging
from .play_utils import send_event_notification
from .action_menu import ActionAutoClose
log = SimpleLogging(__name__)


class PlayNextService(threading.Thread):

    stop_thread = False
    monitor = None

    def __init__(self, play_monitor):
        super(PlayNextService, self).__init__()
        self.monitor = play_monitor

    def run(self):

        from .play_utils import get_playing_data
        settings = xbmcaddon.Addon()
        play_next_trigger_time = int(settings.getSetting('play_next_trigger_time'))

        play_next_dialog = None
        play_next_triggered = False
        is_playing = False

        while not xbmc.Monitor().abortRequested() and not self.stop_thread:

            player = xbmc.Player()
            if player.isPlaying():

                if not is_playing:
                    settings = xbmcaddon.Addon()
                    play_next_trigger_time = int(settings.getSetting('play_next_trigger_time'))
                    log.debug("New play_next_trigger_time value: {0}", play_next_trigger_time)

                duration = player.getTotalTime()
                position = player.getTime()
                trigger_time = play_next_trigger_time  # 300
                time_to_end = (duration - position)

                if not play_next_triggered and (trigger_time > time_to_end) and play_next_dialog is None:
                    play_next_triggered = True
                    log.debug("play_next_triggered hit at {0} seconds from end", time_to_end)

                    play_data = get_playing_data(self.monitor.played_information)
                    log.debug("play_next_triggered play_data : {0}", play_data)

                    next_episode = play_data.get("next_episode")
                    item_type = play_data.get("item_type")

                    if next_episode is not None and item_type == "Episode":

                        settings = xbmcaddon.Addon()
                        plugin_path = settings.getAddonInfo('path')
                        plugin_path_real = xbmcvfs.translatePath(os.path.join(plugin_path))

                        play_next_dialog = PlayNextDialog("PlayNextDialog.xml", plugin_path_real, "default", "720p")
                        play_next_dialog.set_episode_info(next_episode)
                        if play_next_dialog is not None:
                            play_next_dialog.show()

                is_playing = True

            else:
                play_next_triggered = False
                if play_next_dialog is not None:
                    play_next_dialog.stop_auto_close()
                    play_next_dialog.close()
                    del play_next_dialog
                    play_next_dialog = None

                is_playing = False

            if xbmc.Monitor().waitForAbort(1):
                break

    def stop_servcie(self):
        log.debug("PlayNextService Stop Called")
        self.stop_thread = True


class PlayNextDialog(xbmcgui.WindowXMLDialog):

    action_exitkeys_id = None
    episode_info = None
    play_called = False
    auto_close_thread = None

    def __init__(self, *args, **kwargs):
        log.debug("PlayNextDialog: __init__")
        xbmcgui.WindowXML.__init__(self, *args, **kwargs)
        self.auto_close_thread = ActionAutoClose(self)
        self.auto_close_thread.set_timeout(30)
        self.auto_close_thread.start()

    def onInit(self):
        log.debug("PlayNextDialog: onInit")
        self.action_exitkeys_id = [10, 13]

        log.debug("PlayNextDialog: episode_info : {0}", self.episode_info)

        series_name = self.episode_info.get("SeriesName")
        season_name = self.episode_info.get("SeasonName", "n/a")
        next_epp_name = self.episode_info.get("Name", "n/a")

        epp_index = self.episode_info.get("IndexNumber", -1)
        season_index = self.episode_info.get("ParentIndexNumber", -1)
        epp_season_number = "s%02d-e%02d" % (season_index, epp_index)

        rating = self.episode_info.get("CommunityRating")
        if rating:
            next_epp_name += " (%s)" % (rating,)

        overview = self.episode_info.get("Overview")

        overview_label = self.getControl(3018)
        overview_label.setText(overview)

        series_label = self.getControl(3011)
        series_label.setLabel(series_name)

        season_label = self.getControl(3016)
        season_label.setLabel(season_name)

        epp_season_num = self.getControl(3017)
        epp_season_num.setLabel(epp_season_number)

        series_label = self.getControl(3012)
        series_label.setLabel(next_epp_name)

        epp_image = self.getControl(3015)
        epp_image.setImage(self.episode_info["art"]["thumb"])

        runtime_ticks = self.episode_info.get("RunTimeTicks", 0)
        duration = (runtime_ticks / 10000000.0) / 60.0 # convert ticks to minutes
        duration = int(round(duration, 0))
        duration_string = "%s m" % (duration,)
        duration_label = self.getControl(3019)
        duration_label.setLabel(duration_string)

        self.auto_close_thread.set_callback(self)

    def update_progress(self, percentage):
        count_down = self.getControl(3030)
        count_down.setPercent(percentage)

    def onFocus(self, control_id):
        pass

    def doAction(self, action_id):
        pass

    def onMessage(self, message):
        log.debug("PlayNextDialog: onMessage: {0}", message)

    def onAction(self, action):

        if action.getId() == 10:  # ACTION_PREVIOUS_MENU
            self.auto_close_thread.stop()
            self.close()
        elif action.getId() == 92:  # ACTION_NAV_BACK
            self.auto_close_thread.stop()
            self.close()
        else:
            self.auto_close_thread.set_last()
            log.debug("PlayNextDialog: onAction: {0}", action.getId())

    def onClick(self, control_id):
        if control_id == 3013:
            log.debug("PlayNextDialog: Play Next Episode")
            self.play_called
            self.auto_close_thread.stop()
            self.close()
            next_item_id = self.episode_info.get("Id")
            log.debug("Playing Next Episode: {0}", next_item_id)
            play_info = {}
            play_info["item_id"] = next_item_id
            play_info["auto_resume"] = "-1"
            play_info["force_transcode"] = False
            send_event_notification("embycon_play_action", play_info)

        self.auto_close_thread.set_last()

    def set_episode_info(self, info):
        self.episode_info = info

    def get_play_called(self):
        return self.play_called

    def stop_auto_close(self):
        self.auto_close_thread.stop()
