import threading
import xbmc
import traceback

from .simple_logging import SimpleLogging
from resources.lib.functions import show_menu

log = SimpleLogging(__name__)


class ContextMonitor(threading.Thread):

    stop_thread = False

    def run(self):

        item_id = None
        log.debug("ContextMonitor Thread Started")

        kodi_monitor = xbmc.Monitor()
        while not kodi_monitor.abortRequested() and not self.stop_thread:

            if xbmc.getCondVisibility("Window.IsActive(fullscreenvideo) | Window.IsActive(visualisation)"):
                kodi_monitor.waitForAbort(1)
            else:
                if xbmc.getCondVisibility("Window.IsVisible(contextmenu)"):
                    if item_id:
                        xbmc.executebuiltin("Dialog.Close(contextmenu,true)")
                        params = {}
                        params["item_id"] = item_id
                        try:
                            show_menu(params)
                        except Exception as err:
                            tb = traceback.format_exc()
                            log.error("Context Menu Error : {0}\n{1}", err, tb)

                container_id = xbmc.getInfoLabel("System.CurrentControlID")
                item_id = xbmc.getInfoLabel("Container(" + str(container_id) + ").ListItem.Property(id)")

                kodi_monitor.waitForAbort(0.2)

        '''
        context_up = False
        is_embycon_item = False
        
        while not xbmc.Monitor().abortRequested() and not self.stop_thread:

            if xbmc.getCondVisibility("Window.IsActive(fullscreenvideo) | Window.IsActive(visualisation)"):
                xbmc.sleep(1000)
            else:
                if xbmc.getCondVisibility("Window.IsVisible(contextmenu)"):
                    context_up = True
                    if is_embycon_item:
                        xbmc.executebuiltin("Dialog.Close(contextmenu,true)")
                else:
                    if context_up:  # context now down, do something
                        context_up = False
                        container_id = xbmc.getInfoLabel("System.CurrentControlID")
                        log.debug("ContextMonitor Container ID: {0}", container_id)
                        item_id = xbmc.getInfoLabel("Container(" + str(container_id) + ").ListItem.Property(id)")
                        log.debug("ContextMonitor Item ID: {0}", item_id)
                        if item_id:
                            params = {}
                            params["item_id"] = item_id
                            show_menu(params)

                container_id = xbmc.getInfoLabel("System.CurrentControlID")
                condition = ("String.StartsWith(Container(" + str(container_id) +
                             ").ListItem.Path,plugin://plugin.video.embycon) + !String.IsEmpty(Container(" +
                             str(container_id) + ").ListItem.Property(id))")
                is_embycon_item = xbmc.getCondVisibility(condition)

                xbmc.sleep(200)
                
        '''

        log.debug("ContextMonitor Thread Exited")

    def stop_monitor(self):
        log.debug("ContextMonitor Stop Called")
        self.stop_thread = True
