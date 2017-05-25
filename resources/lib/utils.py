# Gnu General Public License - see LICENSE.TXT

import xbmc
import xbmcgui
import xbmcaddon

import json

from downloadutils import DownloadUtils
from simple_logging import SimpleLogging
from clientinfo import ClientInformation

#define our global download utils
downloadUtils = DownloadUtils()
log = SimpleLogging("EmbyCon." + __name__)

###########################################################################
class PlayUtils():
    def getPlayUrl(self, id, result):
        log.info("getPlayUrl")
        addonSettings = xbmcaddon.Addon(id='plugin.video.embycon')
        playback_type = addonSettings.getSetting("playback_type")
        playback_bitrate = addonSettings.getSetting("playback_bitrate")
        server = addonSettings.getSetting('ipaddress') + ":" + addonSettings.getSetting('port')
        smb_username = addonSettings.getSetting('smbusername')
        smb_password = addonSettings.getSetting('smbpassword')
        log.info("playback_type: " + playback_type)
        playurl = None

        # check if strm file, will contain contain playback url
        if result.get('MediaSources'):
            source = result['MediaSources'][0]
            if source.get('Container') == 'strm':
                playurl = source.get('Path')
                if playurl:
                    return playurl

        # do direct path playback
        if playback_type == "0":
            playurl = result.get("Path")

            # handle DVD structure
            if (result.get("VideoType") == "Dvd"):
                playurl = playurl + "/VIDEO_TS/VIDEO_TS.IFO"
            elif (result.get("VideoType") == "BluRay"):
                playurl = playurl + "/BDMV/index.bdmv"

            # add smb creds
            if smb_username == '':
                playurl = playurl.replace("\\\\", "smb://")
            else:
                playurl = playurl.replace("\\\\", "smb://" + smb_username + ':' + smb_password + '@')

            playurl = playurl.replace("\\", "/")

        # do direct http streaming playback
        elif playback_type == "1":
            playurl = "http://%s/emby/Videos/%s/stream?static=true" % (server, id)
            user_token = downloadUtils.authenticate()
            playurl = playurl + "&api_key=" + user_token

        # do transcode http streaming playback
        elif playback_type == "2":
            log.info("playback_bitrate: " + playback_bitrate)

            clientInfo = ClientInformation()
            deviceId = clientInfo.getDeviceId()
            bitrate = int(playback_bitrate) * 1000
            user_token = downloadUtils.authenticate()

            playurl = (
                "http://%s/emby/Videos/%s/master.m3u8?MediaSourceId=%s&VideoCodec=h264&AudioCodec=ac3&MaxAudioChannels=6&deviceId=%s&VideoBitrate=%s"
                % (server, id, id, deviceId, bitrate))

            playurl = playurl + "&api_key=" + user_token

        log.info("Playback URL: " + playurl)
        return playurl.encode('utf-8')


def getKodiVersion():
    version = 0.0
    jsonData = xbmc.executeJSONRPC(
        '{ "jsonrpc": "2.0", "method": "Application.GetProperties", "params": {"properties": ["version", "name"]}, "id": 1 }')

    result = json.loads(jsonData)

    try:
        result = result.get("result")
        versionData = result.get("version")
        version = float(str(versionData.get("major")) + "." + str(versionData.get("minor")))
        log.info("Version : " + str(version) + " - " + str(versionData))
    except:
        version = 0.0
        log.error("Version Error : RAW Version Data : " + str(result))

    return version

def getDetailsString():
    detailsString = "EpisodeCount,SeasonCount,Path,Genres,Studios,CumulativeRunTimeTicks,MediaStreams,Overview,Etag"
    #detailsString = "EpisodeCount,SeasonCount,Path,Genres,CumulativeRunTimeTicks"
    return detailsString

def getChecksum(item):
    userdata = item['UserData']
    checksum = "%s_%s_%s_%s_%s_%s_%s" % (
        item['Etag'],
        userdata['Played'],
        userdata['IsFavorite'],
        userdata.get('Likes', "-"),
        userdata['PlaybackPositionTicks'],
        userdata.get('UnplayedItemCount', "-"),
        userdata.get("PlayedPercentage", "-")
    )

    return checksum

def getArt(item, server, widget=False):
    art = {
        'thumb': '',
        'fanart': '',
        'poster': '',
        'banner': '',
        'clearlogo': '',
        'clearart': '',
        'discart': '',
        'landscape': '',
        'tvshow.poster': ''
    }
    item_id = item.get("Id")

    image_id = item_id
    imageTags = item.get("ImageTags")
    if (imageTags is not None) and (imageTags.get("Primary") is not None):
        image_tag = imageTags.get("Primary")
        if widget:
            art['thumb'] = downloadUtils.imageUrl(image_id, "Primary", 0, 400, 400, image_tag, server=server)
        else:
            art['thumb'] = downloadUtils.getArtwork(item, "Primary", server=server)

    if item.get("Type") == "Episode":
        art['thumb'] = art['thumb'] if art['thumb'] else downloadUtils.getArtwork(item, "Thumb", server=server)
        art['landscape'] = art['thumb'] if art['thumb'] else downloadUtils.getArtwork(item, "Thumb", parent=True, server=server)
        art['tvshow.poster'] = downloadUtils.getArtwork(item, "Primary", parent=True, server=server)
    else:
        art['poster'] = art['thumb']

    art['fanart'] = downloadUtils.getArtwork(item, "Backdrop", server=server)
    if not art['fanart']:
        art['fanart'] = downloadUtils.getArtwork(item, "Backdrop", parent=True, server=server)

    if not art['landscape']:
        art['landscape'] = downloadUtils.getArtwork(item, "Thumb", server=server)
        if not art['landscape']:
            art['landscape'] = art['fanart']

    if not art['thumb']:
        art['thumb'] = art['landscape']

    art['banner'] = downloadUtils.getArtwork(item, "Banner", server=server)
    art['clearlogo'] = downloadUtils.getArtwork(item, "Logo", server=server)
    art['clearart'] = downloadUtils.getArtwork(item, "Art", server=server)
    art['discart'] = downloadUtils.getArtwork(item, "Disc", server=server)

    return art

class HomeWindow():
    """
        xbmcgui.Window(10000) with add-on id prefixed to keys
    """
    def __init__(self):
        self.id_string = 'plugin.video.embycon-%s'
        self.window = xbmcgui.Window(10000)

    def getProperty(self, key):
        key = self.id_string % key
        value = self.window.getProperty(key)
        # log.debug('HomeWindow: getProperty |%s| -> |%s|' % (key, value))
        return value

    def setProperty(self, key, value):
        key = self.id_string % key
        # log.debug('HomeWindow: setProperty |%s| -> |%s|' % (key, value))
        self.window.setProperty(key, value)

    def clearProperty(self, key):
        key = self.id_string % key
        # log.debug('HomeWindow: clearProperty |%s|' % key)
        self.window.clearProperty(key)
