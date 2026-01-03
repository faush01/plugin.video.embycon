from __future__ import annotations
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

    window: xbmcgui.Window

    def __init__(self) -> None:
        self.id_string = "plugin.video.embycon-%s"
        self.window = xbmcgui.Window(10000)

    def get_property(self, key: str) -> str:
        key = self.id_string % key
        return self.window.getProperty(key)

    def set_property(self, key: str, value: str) -> None:
        key = self.id_string % key
        self.window.setProperty(key, value)

    def clear_property(self, key: str) -> None:
        key = self.id_string % key
        self.window.clearProperty(key)


def add_menu_directory_item(
    label: str, path: str, folder: bool = True, art: dict | None = None
) -> None:
    li: xbmcgui.ListItem = xbmcgui.ListItem(label, path=path)
    if art is None:
        art = {}
        addon = xbmcaddon.Addon()
        art["thumb"] = addon.getAddonInfo("icon")
    li.setArt(art)

    xbmcplugin.addDirectoryItem(
        handle=int(sys.argv[1]), url=path, listitem=li, isFolder=folder
    )


def get_kodi_version() -> float:
    json_data = xbmc.executeJSONRPC(
        '{ "jsonrpc": "2.0", "method": "Application.GetProperties", "params": {"properties": ["version", "name"]}, "id": 1 }'
    )

    result = json.loads(json_data)

    try:
        result = result.get("result")
        version_data = result.get("version")
        version = float(
            str(version_data.get("major")) + "." + str(version_data.get("minor"))
        )
        log.debug("Version: {0} - {1}", version, version_data)
    except Exception:
        version = 0.0
        log.error("Version Error : RAW Version Data: {0}", result)

    return version
