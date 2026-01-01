# Gnu General Public License - see LICENSE.TXT
from __future__ import annotations

import xbmcaddon
import xbmc
import xbmcvfs

import string
import random
import urllib.parse
import json
import base64
import time
import math
from datetime import datetime
import calendar
import re
from dataclasses import dataclass
from typing import List, Tuple

from .downloadutils import DownloadUtils
from .simple_logging import SimpleLogging


log = SimpleLogging(__name__)

# hack to get datetime strptime loaded
throwaway = time.strptime("20110101", "%Y%m%d")


def get_emby_url(base_url: str, params: dict[str, object]) -> str:
    params["format"] = "json"
    param_list = []
    for key in params:
        if params[key] is not None:
            value = params[key]
            if not isinstance(value, str):
                value = str(value)
            param_list.append(
                key + "=" + urllib.parse.quote_plus(str(value), safe="{}")
            )
    param_string = "&".join(param_list)
    return base_url + "?" + param_string


###########################################################################
@dataclass
class StrmDetails:
    """Result from get_strm_details containing playback URL and listitem properties."""

    playurl: str | None
    listitem_props: List[Tuple[str, str]]


@dataclass
class PlayUrlResult:
    """Result from get_play_url containing playback URL, playback type, and listitem properties."""

    playurl: str | None
    playback_type: str | None
    listitem_props: List[Tuple[str, str]]


class PlayUtils:
    @staticmethod
    def get_play_url(media_source: dict) -> PlayUrlResult:
        log.debug("get_play_url - media_source: {0}", media_source)

        # check if strm file Container
        if media_source.get("Container") == "strm":
            log.debug("Detected STRM Container")
            strm_result = PlayUtils().get_strm_details(media_source)
            if strm_result.playurl is None:
                log.debug("Error, no strm content")
                return PlayUrlResult(
                    playurl=None, playback_type=None, listitem_props=[]
                )
            return PlayUrlResult(
                playurl=strm_result.playurl,
                playback_type="0",
                listitem_props=strm_result.listitem_props,
            )

        # get all the options
        addon_settings = xbmcaddon.Addon()
        download_utils = DownloadUtils()
        server = download_utils.get_server(add_user_id=True)
        if server is None:
            log.debug("Error, no server info")
            return PlayUrlResult(playurl=None, playback_type=None, listitem_props=[])

        use_https = addon_settings.getSetting("protocol") == "1"
        verify_cert = addon_settings.getSetting("verify_cert") == "true"
        allow_direct_file_play = (
            addon_settings.getSetting("allow_direct_file_play") == "true"
        )

        can_direct_play = media_source["SupportsDirectPlay"]
        can_direct_stream = media_source["SupportsDirectStream"]
        can_transcode = media_source["SupportsTranscoding"]
        container = media_source["Container"]

        playurl = None
        playback_type = None

        # check if file can be directly played
        if allow_direct_file_play and can_direct_play:
            direct_path = media_source["Path"]
            direct_path = direct_path.replace("\\", "/")
            direct_path = direct_path.strip()

            # handle DVD structure
            if container == "dvd":
                direct_path = direct_path + "/VIDEO_TS/VIDEO_TS.IFO"
            elif container == "bluray":
                direct_path = direct_path + "/BDMV/index.bdmv"

            if direct_path.startswith("//"):
                direct_path = "smb://" + direct_path[2:]

            log.debug("playback_direct_path: {0}", direct_path)

            if xbmcvfs.exists(direct_path):
                playurl = direct_path
                playback_type = "0"

        # check if file can be direct streamed
        if can_direct_stream and playurl is None:
            direct_stream_path = media_source["DirectStreamUrl"]
            direct_stream_path = server + "/emby" + direct_stream_path
            if use_https and not verify_cert:
                direct_stream_path += "|verifypeer=false"
            playurl = direct_stream_path
            playback_type = "1"

        # check is file can be transcoded
        if can_transcode and playurl is None:
            transcode_stream_path = media_source["TranscodingUrl"]

            url_path, url_params = transcode_stream_path.split("?")

            params = url_params.split("&")
            log.debug("Streaming Params Before : {0}", params)

            # remove the audio and subtitle indexes
            # this will be replaced by user selection dialogs in Kodi
            params_to_remove = [
                "AudioStreamIndex",
                "SubtitleStreamIndex",
                "AudioBitrate",
            ]
            reduced_params: list[str] = []
            for param in params:
                param_bits = param.split("=")
                if param_bits[0] not in params_to_remove:
                    reduced_params.append(param)

            audio_playback_bitrate = addon_settings.getSetting("audio_playback_bitrate")
            audio_bitrate = int(audio_playback_bitrate) * 1000
            reduced_params.append("AudioBitrate=%s" % audio_bitrate)

            playback_max_width = addon_settings.getSetting("playback_max_width")
            reduced_params.append("MaxWidth=%s" % playback_max_width)

            log.debug("Streaming Params After : {0}", reduced_params)

            new_url_params = "&".join(reduced_params)

            transcode_stream_path = server + "/emby" + url_path + "?" + new_url_params

            if use_https and not verify_cert:
                transcode_stream_path += "|verifypeer=false"

            playurl = transcode_stream_path
            playback_type = "2"

        return PlayUrlResult(
            playurl=playurl, playback_type=playback_type, listitem_props=[]
        )

    @staticmethod
    def get_strm_details(media_source: dict) -> StrmDetails:
        playurl = None
        listitem_props = []

        # contains contents of strm file with linebreaks
        contents = media_source.get("Path", "")

        line_break = "\r"
        if "\r\n" in contents:
            line_break = "\r\n"
        elif "\n" in contents:
            line_break = "\n"

        lines = contents.split(line_break)
        for line in lines:
            line = line.strip()
            log.debug("STRM Line: {0}", line)
            if line.startswith("#KODIPROP:"):
                match = re.search(
                    "#KODIPROP:(?P<item_property>[^=]+?)=(?P<property_value>.+)", line
                )
                if match:
                    item_property = match.group("item_property")
                    property_value = match.group("property_value")
                    log.debug(
                        "STRM property found: {0} value: {1}",
                        item_property,
                        property_value,
                    )
                    listitem_props.append((item_property, property_value))
                else:
                    log.debug("STRM #KODIPROP incorrect format")
            elif line.startswith("#"):
                #  unrecognized, treat as comment
                log.debug("STRM unrecognized line identifier, ignored")
            elif line != "":
                playurl = line
                log.debug("STRM playback url found")

        log.debug("Playback URL: {0} ListItem Properties: {1}", playurl, listitem_props)
        return StrmDetails(playurl=playurl, listitem_props=listitem_props)


def get_checksum(item: dict) -> str:
    userdata = item["UserData"]
    return "%s_%s_%s_%s_%s_%s_%s" % (
        item["Etag"],
        userdata["Played"],
        userdata["IsFavorite"],
        userdata.get("Likes", "-"),
        userdata["PlaybackPositionTicks"],
        userdata.get("UnplayedItemCount", "-"),
        userdata.get("PlayedPercentage", "-"),
    )


def get_art(
    item: dict, server: str, maxwidth: int, download_utils: DownloadUtils
) -> dict[str, str]:
    art = {
        "thumb": "",
        "fanart": "",
        "poster": "",
        "banner": "",
        "clearlogo": "",
        "clearart": "",
        "discart": "",
        "landscape": "",
        "tvshow.fanart": "",
        "tvshow.poster": "",
        "tvshow.clearart": "",
        "tvshow.clearlogo": "",
        "tvshow.banner": "",
        "tvshow.landscape": "",
    }

    def set_artwork(
        art_keys: list[str], artwork_type: str, parent: bool = False
    ) -> None:
        """Helper to set multiple art keys with the same artwork type."""
        artwork_url = download_utils.get_artwork(
            item, artwork_type, parent=parent, server=server, maxwidth=maxwidth
        )
        for key in art_keys:
            art[key] = artwork_url

    image_tags = item["ImageTags"]
    if image_tags is not None and image_tags["Primary"] is not None:
        art["thumb"] = download_utils.get_artwork(
            item, "Primary", server=server, maxwidth=maxwidth
        )

    item_type = item["Type"]

    if item_type == "Genre":
        set_artwork(["poster"], "Primary")
    elif item_type == "Episode":
        set_artwork(["tvshow.poster"], "Primary", parent=True)
        set_artwork(["tvshow.clearart", "clearart"], "Art", parent=True)
        set_artwork(["tvshow.clearlogo", "clearlogo"], "Logo", parent=True)
        set_artwork(["tvshow.banner", "banner"], "Banner", parent=True)
        set_artwork(["tvshow.landscape", "landscape"], "Thumb", parent=True)
        set_artwork(["tvshow.fanart", "fanart"], "Backdrop", parent=True)
    elif item_type == "Season":
        set_artwork(["tvshow.poster"], "Primary", parent=True)
        set_artwork(["season.poster", "poster"], "Primary", parent=False)
        set_artwork(["tvshow.clearart", "clearart"], "Art", parent=True)
        set_artwork(["tvshow.clearlogo", "clearlogo"], "Logo", parent=True)
        set_artwork(["tvshow.banner"], "Banner", parent=True)
        set_artwork(["season.banner", "banner"], "Banner", parent=False)
        set_artwork(["tvshow.landscape"], "Thumb", parent=True)
        set_artwork(["season.landscape", "landscape"], "Thumb", parent=False)
        set_artwork(["tvshow.fanart", "fanart"], "Backdrop", parent=True)
    elif item_type == "Series":
        set_artwork(["tvshow.poster", "poster"], "Primary", parent=False)
        set_artwork(["tvshow.clearart", "clearart"], "Art", parent=False)
        set_artwork(["tvshow.clearlogo", "clearlogo"], "Logo", parent=False)
        set_artwork(["tvshow.banner", "banner"], "Banner", parent=False)
        set_artwork(["tvshow.landscape", "landscape"], "Thumb", parent=False)
        set_artwork(["tvshow.fanart", "fanart"], "Backdrop", parent=False)
    elif item_type == "Movie" or item_type == "BoxSet":
        set_artwork(["poster"], "Primary")
        set_artwork(["landscape"], "Thumb")
        set_artwork(["banner"], "Banner")
        set_artwork(["clearlogo"], "Logo")
        set_artwork(["clearart"], "Art")
        set_artwork(["discart"], "Disc")
        set_artwork(["fanart"], "Backdrop")

    if not art["fanart"]:
        art["fanart"] = download_utils.get_artwork(
            item, "Backdrop", parent=True, server=server, maxwidth=maxwidth
        )

    return art


def id_generator(
    size: int = 6, chars: str = string.ascii_uppercase + string.digits
) -> str:
    return "".join(random.choice(chars) for _ in range(size))


def double_urlencode(value: str) -> str:
    text: str = single_urlencode(value)
    return single_urlencode(text)


def single_urlencode(value: str) -> str:
    text: str = urllib.parse.urlencode({"1": value})
    return text[2:]


def send_event_notification(method: str, data: dict) -> None:
    message_data = json.dumps(data)
    source_id = "embycon"
    base64_data = base64.b64encode(message_data.encode("utf-8"))
    base64_data = base64_data.decode("utf-8")
    escaped_data = '\\"[\\"{0}\\"]\\"'.format(base64_data)
    command = "NotifyAll({0}.SIGNAL,{1},{2})".format(source_id, method, escaped_data)
    log.debug("Sending notification event data: {0}", command)
    xbmc.executebuiltin(command)


def datetime_from_string(time_string: str) -> datetime:
    if time_string[-1:] == "Z":
        time_string = re.sub("[0-9]{1}Z", " UTC", time_string)
    elif time_string[-6:] == "+00:00":
        time_string = re.sub("[0-9]{1}\\+00:00", " UTC", time_string)
    log.debug("New Time String : {0}", time_string)

    start_time = time.strptime(time_string, "%Y-%m-%dT%H:%M:%S.%f %Z")
    dt = datetime(*(start_time[0:6]))
    timestamp = calendar.timegm(dt.timetuple())
    local_dt = datetime.fromtimestamp(timestamp)
    local_dt.replace(microsecond=dt.microsecond)
    return local_dt


def convert_size(size_bytes: int) -> str:
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])
