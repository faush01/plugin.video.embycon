import threading
import sys
import xbmc
import xbmcgui

from simple_logging import SimpleLogging
from resources.lib.functions import show_menu

log = SimpleLogging(__name__)


class ContextMonitor(threading.Thread):

    stop_monitor = False

    def run(self):
        monitor = xbmc.Monitor()
        container_id = None
        log.debug("ContextMonitor Thread Started")

        while not xbmc.abortRequested:

            if not xbmc.getCondVisibility("Window.IsVisible(contextmenu)"):
                container_id = xbmc.getInfoLabel("System.CurrentControlID")
                log.debug("ContextMonitor Container ID: {0}", container_id)

                if xbmc.getCondVisibility("String.StartsWith(Container(" + str(container_id) + ").ListItem.Path,plugin://plugin.video.embycon)"):
                    item_id = xbmc.getInfoLabel("Container(" + str(container_id) + ").ListItem.Property(id)")
                else:
                    item_id = None

            elif item_id:
                log.debug("ContextMonitor Item ID: {0}", item_id)
                xbmc.executebuiltin("Dialog.Close(contextmenu,true)")
                params = {}
                params["item_id"] = item_id
                show_menu(params)

            xbmc.sleep(50)

        log.debug("ContextMonitor Thread Exited")

    def stop_monitor(self):
        log.debug("ContextMonitor Stop Called")
        self.stop_monitor = True