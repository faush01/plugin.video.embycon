# Gnu General Public License - see LICENSE.TXT

from uuid import uuid4 as uuid4
import xbmcaddon
import xbmcvfs

from .kodi_utils import HomeWindow
from .simple_logging import SimpleLogging

log = SimpleLogging(__name__)


class ClientInformation:

    @staticmethod
    def get_device_id():

        window = HomeWindow()
        client_id = window.get_property("client_id")

        if client_id:
            return client_id

        emby_guid_path = xbmcvfs.translatePath("special://temp/embycon_guid")
        log.debug("emby_guid_path: {0}", emby_guid_path)
        guid = xbmcvfs.File(emby_guid_path)
        client_id = guid.read()
        guid.close()

        if not client_id:
            client_id = uuid4().hex
            log.debug("Generating a new guid: {0}", client_id)
            guid = xbmcvfs.File(emby_guid_path, 'w')
            guid.write(client_id)
            guid.close()
            log.debug("emby_client_id (NEW): {0}", client_id)
        else:
            log.debug("emby_client_id: {0}", client_id)

        window.set_property("client_id", client_id)
        return client_id

    @staticmethod
    def get_version():
        addon = xbmcaddon.Addon()
        version = addon.getAddonInfo("version")
        return version

    @staticmethod
    def get_client():
        return 'Kodi EmbyCon'
