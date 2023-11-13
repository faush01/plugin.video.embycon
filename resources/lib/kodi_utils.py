from typing import Union

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

import sys
import json

from .simple_logging import SimpleLogging

log = SimpleLogging(__name__)


class HomeWindow:
    """
        xbmcgui.Window(10000) with add-on id prefixed to keys
    """

    def __init__(self):
        self.id_string: str = 'plugin.video.embycon-%s'
        self.window = xbmcgui.Window(10000)

    def get_property(self, key: str) -> str:
        k: str = self.id_string % key
        v: str = self.window.getProperty(k)
        # log.debug('HomeWindow: getProperty |{0}| -> |{1}|', key, value)
        return v

    def set_property(self, key: str, value: Union[str, None]) -> None:
        if value is None:
            value = ""
        key = self.id_string % key
        # log.debug('HomeWindow: setProperty |{0}| -> |{1}|', key, value)
        self.window.setProperty(key, value)

    def clear_property(self, key: str) -> None:
        key = self.id_string % key
        # log.debug('HomeWindow: clearProperty |{0}|', key)
        self.window.clearProperty(key)


def add_menu_directory_item(label, path, folder=True, art=None):
    li = xbmcgui.ListItem(label, path=path)
    if art is None:
        art = {}
        addon = xbmcaddon.Addon()
        art["thumb"] = addon.getAddonInfo('icon')
    li.setArt(art)

    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=path, listitem=li, isFolder=folder)


def get_kodi_version():

    json_data = xbmc.executeJSONRPC(
        '{ "jsonrpc": "2.0", "method": "Application.GetProperties", "params": {"properties": ["version", "name"]}, "id": 1 }')

    result = json.loads(json_data)

    try:
        result = result.get("result")
        version_data = result.get("version")
        version = float(str(version_data.get("major")) + "." + str(version_data.get("minor")))
        log.debug("Version: {0} - {1}", version, version_data)
    except:
        version = 0.0
        log.error("Version Error : RAW Version Data: {0}", result)

    return version
