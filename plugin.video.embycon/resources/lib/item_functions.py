from __future__ import annotations
import sys
from dataclasses import dataclass
import urllib.parse

from datetime import datetime

from collections import defaultdict

import xbmc
import xbmcgui

from .utils import get_art, datetime_from_string
from .downloadutils import DownloadUtils
from .simple_logging import SimpleLogging


log = SimpleLogging(__name__)


@dataclass
class GuiItem:
    """Represents a GUI item for Kodi directory listings.

    Attributes:
        url: The URL or path for the item
        list_item: The Kodi ListItem object with metadata
        is_folder: Whether this item is a folder (True) or playable item (False)
    """

    url: str
    list_item: xbmcgui.ListItem
    is_folder: bool

    def as_tuple(self) -> tuple[str, xbmcgui.ListItem, bool]:
        """Returns the item as a tuple for compatibility with xbmcplugin.addDirectoryItems."""
        return (self.url, self.list_item, self.is_folder)


@dataclass
class GuiOptions:
    """GUI options for item extraction.

    Attributes:
        server: The server URL
        name_format: Optional format string for item names
        name_format_type: Optional item type to apply name format to
        use_prem_date_for_added: Whether to use premiere date for date added
        max_image_width: Maximum width for images
    """

    server: str
    name_format: str | None = None
    name_format_type: str | None = None
    use_prem_date_for_added: bool = False
    max_image_width: int = 400


@dataclass
class DisplayOptions:
    """Display options for GUI items.

    Attributes:
        addCounts: Whether to add unwatched counts to item names
        addResumePercent: Whether to add resume percentage to item names
        addSubtitleAvailable: Whether to add subtitle indicator to item names
        addUserRatings: Whether to add user ratings to items
    """

    addCounts: bool = False
    addResumePercent: bool = False
    addSubtitleAvailable: bool = False


class MediaStream:
    type = "na"
    width: int = 0
    height: int = 0
    channels: int = 0
    codec: str = "na"
    aspect_ratio: float = 1.0
    language: str = "na"
    hdr_type: str = ""

    # "default" if x is None else x

    def set_hdr_type(self, value: str | None) -> None:
        # Kodi options : dolbyvision, hdr10, hlg
        if value is not None:
            value = value.lower()
            if value in ("hdr10plus", "hdr10"):
                self.hdr_type = "hdr10"
            elif value == "hyperloghamma":
                self.hdr_type = "hlg"
            elif value == "dolbyvision":
                self.hdr_type = "dolbyvision"

    def set_channels(self, value: int | None) -> None:
        if value is not None:
            self.channels = int(value)

    def set_language(self, value: str | None) -> None:
        if value is not None:
            self.language = value

    def set_aspect_ratio(self, value: float | None) -> None:
        if value is not None:
            self.aspect_ratio = float(value)

    def set_type(self, value: str | None) -> None:
        if value is not None:
            self.type = value

    def set_codec(self, value: str | None) -> None:
        if value is not None:
            self.codec = value

    def set_width(self, value: int | None) -> None:
        if value is not None:
            self.width = int(value)

    def set_height(self, value: int | None) -> None:
        if value is not None:
            self.height = int(value)


class Person:
    name: str = ""
    role: str = ""
    thumbnail: str = ""

    def __init__(self, n: str, r: str, t: str) -> None:
        self.name = n
        self.role = r
        self.thumbnail = t


class ItemDetails:
    # objects
    media_streams: list[MediaStream] = []
    cast: list[Person] | None = None

    # values
    name: str | None = None
    sort_name: str | None = None
    id: str | None = None
    etag: str | None = None
    path: str | None = None
    is_folder: bool = False
    plot: str | None = None
    series_name: str | None = None
    episode_number: int = 0
    season_number: int = 0
    episode_sort_number: int = 0
    season_sort_number: int = 0
    track_number: int = 0
    series_id: str | None = None
    art: dict[str, str] | None = None

    mpaa: str | None = None
    critic_rating: float = 0.0
    community_rating: float = 0.0
    year: int | None = None
    premiere_date: str | None = None
    date_added: str | None = None
    location_type: str | None = None
    studio: str | None = None
    production_location: str | None = None
    genres: list[str] | None = None
    play_count: int = 0
    director: str = ""
    writer: str = ""
    tagline: str = ""
    status: str | None = None
    tags: list[str] | None = None

    resume_time: float = 0.0
    duration: float = 0.0
    recursive_item_count: int = 0
    recursive_unplayed_items_count: int | None = 0
    total_seasons: int = 0
    total_episodes: int = 0
    watched_episodes: int = 0
    unwatched_episodes: int = 0
    number_episodes: int = 0
    original_title: str | None = None
    item_type: str | None = None
    subtitle_available: bool = False
    total_items: int = 0
    song_artist: str = ""
    album_artist: str = ""
    album_name: str | None = ""

    program_channel_name: str | None = None
    program_end_date: str | None = None
    program_start_date: str | None = None

    favorite: str = "false"
    overlay: str = "0"

    name_format: str = ""
    mode: str = ""

    baseline_itemname: str | None = None

    def set_episode_number(self, value: int | None) -> None:
        if value is not None:
            self.episode_number = value

    def set_season_sort_number(self, value: int | None) -> None:
        if value is not None:
            self.season_sort_number = value

    def set_season_number(self, value: int | None) -> None:
        if value is not None:
            self.season_number = value

    def set_episode_sort_number(self, value: int | None) -> None:
        if value is not None:
            self.episode_sort_number = value


def extract_media_info(item: dict) -> list[str]:
    media_info = []

    media_sources = item["MediaSources"]
    if media_sources is not None:
        for media_source in media_sources:
            media_info.append("Media Stream (%s)" % (media_source["Name"],))
            media_info.append(" -Type: %s" % (media_source["Type"],))
            media_info.append(" -Protocol: %s" % (media_source["Protocol"],))
            media_info.append(" -Path: %s" % (media_source["Path"],))
            media_info.append(" -IsRemote: %s" % (media_source["IsRemote"],))
            media_info.append(" -Container: %s" % (media_source["Container"],))
            if media_source["BitRate"] is not None:
                media_info.append(" -Bitrate: {:,}".format(media_source["Bitrate"]))
            if media_source["Size"] is not None:
                media_info.append(" -Size: {:,}".format(media_source["Size"]))
            media_info.append(
                " -DefaultAudioStreamIndex: %s"
                % (media_source["DefaultAudioStreamIndex"],)
            )

            media_streams = media_source["MediaStreams"]
            if media_streams is not None:
                for mediaStream in media_streams:
                    stream_type = mediaStream["Type"]
                    if stream_type == "Video":
                        media_info.append(" -Video Stream")
                        media_info.append("   -Index: %s" % (mediaStream["Index"],))
                        media_info.append("   -Codec: %s" % (mediaStream["Codec"],))
                        media_info.append(
                            "   -Size: %sx%s"
                            % (mediaStream["Width"], mediaStream["Height"])
                        )
                        media_info.append(
                            "   -AspectRatio: %s" % (mediaStream["AspectRatio"],)
                        )
                        media_info.append(
                            "   -ColorSpace: %s" % (mediaStream["ColorSpace"],)
                        )
                        media_info.append(
                            "   -DisplayTitle: %s" % (mediaStream["DisplayTitle"],)
                        )
                        media_info.append(
                            "   -IsInterlaced: %s" % (mediaStream["IsInterlaced"],)
                        )
                        if mediaStream["BitRate"] is not None:
                            media_info.append(
                                "   -BitRate: {:,}".format(mediaStream["BitRate"])
                            )
                        media_info.append(
                            "   -BitDepth: %s" % (mediaStream["BitDepth"],)
                        )
                        media_info.append(
                            "   -AverageFrameRate: %s"
                            % (mediaStream["AverageFrameRate"],)
                        )
                        media_info.append(
                            "   -RealFrameRate: %s" % (mediaStream["RealFrameRate"],)
                        )
                        media_info.append("   -Profile: %s" % (mediaStream["Profile"],))
                        media_info.append("   -Level: %s" % (mediaStream["Level"],))
                        media_info.append(
                            "   -PixelFormat: %s" % (mediaStream["PixelFormat"],)
                        )
                        media_info.append(
                            "   -IsAnamorphic: %s" % (mediaStream["IsAnamorphic"],)
                        )

                    if stream_type == "Audio":
                        media_info.append(" -Audio Stream")
                        media_info.append("   -Index: %s" % (mediaStream["Index"],))
                        media_info.append(
                            "   -Title: %s" % (mediaStream["DisplayTitle"],)
                        )
                        media_info.append("   -Codec: %s" % (mediaStream["Codec"],))
                        media_info.append(
                            "   -ChannelLayout: %s" % (mediaStream["ChannelLayout"],)
                        )
                        media_info.append(
                            "   -Channels: %s" % (mediaStream["Channels"],)
                        )
                        if mediaStream["BitRate"] is not None:
                            media_info.append(
                                "   -BitRate: {:,}".format(mediaStream["BitRate"])
                            )
                        media_info.append(
                            "   -SampleRate: %s" % (mediaStream["SampleRate"],)
                        )
                        media_info.append(
                            "   -IsDefault: %s" % (mediaStream["IsDefault"],)
                        )
                        media_info.append(
                            "   -IsForced: %s" % (mediaStream["IsForced"],)
                        )
                        media_info.append(
                            "   -IsExternal: %s" % (mediaStream["IsExternal"],)
                        )
                        media_info.append(
                            "   -IsExternal: %s" % (mediaStream["IsExternal"],)
                        )

                    if stream_type == "Subtitle":
                        media_info.append(" -Subtitle Stream")
                        media_info.append("   -Index: %s" % (mediaStream["Index"],))
                        media_info.append("   -Codec: %s" % (mediaStream["Codec"],))
                        media_info.append(
                            "   -Language: %s" % (mediaStream["Language"],)
                        )
                        media_info.append(
                            "   -DisplayTitle: %s" % (mediaStream["DisplayTitle"],)
                        )
                        media_info.append(
                            "   -DisplayLanguage: %s"
                            % (mediaStream["DisplayLanguage"],)
                        )
                        media_info.append(
                            "   -IsDefault: %s" % (mediaStream["IsDefault"],)
                        )
                        media_info.append(
                            "   -IsForced: %s" % (mediaStream["IsForced"],)
                        )
                        media_info.append(
                            "   -IsExternal: %s" % (mediaStream["IsExternal"],)
                        )
                        media_info.append(
                            "   -IsTextSubtitleStream: %s"
                            % (mediaStream["IsTextSubtitleStream"],)
                        )

            media_info.append("")

    return media_info


def extract_item_info(
    item: dict, gui_options: GuiOptions, download_utils: DownloadUtils
) -> ItemDetails:
    item_details = ItemDetails()

    item_details.id = item["Id"]
    item_details.etag = item["Etag"]
    item_details.is_folder = item["IsFolder"]
    item_details.item_type = item["Type"]
    item_details.location_type = item["LocationType"]
    item_details.name = item["Name"]
    item_details.sort_name = item["SortName"]
    item_details.original_title = item_details.name

    server_url = gui_options.server

    if item_details.item_type == "Episode":
        item_details.set_episode_number(item["IndexNumber"])
        item_details.set_season_number(item["ParentIndexNumber"])
        item_details.series_id = item["SeriesId"]

        if item_details.season_number != 0:
            item_details.set_season_sort_number(item_details.season_number)
            item_details.set_episode_sort_number(item_details.episode_number)
        else:
            special_after_season = item["AirsAfterSeasonNumber"]
            special_before_season = item["AirsBeforeSeasonNumber"]
            special_before_episode = item["AirsBeforeEpisodeNumber"]

            if special_after_season:
                item_details.set_season_sort_number(special_after_season + 1)
            elif special_before_season:
                item_details.set_season_sort_number(special_before_season - 1)

            if special_before_episode:
                item_details.set_episode_sort_number(special_before_episode - 1)

    elif item_details.item_type == "Season":
        item_details.set_season_number(item["IndexNumber"])
        item_details.series_id = item["SeriesId"]

    elif item_details.item_type == "Series":
        item_details.status = item["Status"]

    elif item_details.item_type == "Audio":
        item_details.track_number = item["IndexNumber"]
        item_details.album_name = item["Album"]
        artists = item["Artists"]
        if artists is not None and len(artists) > 0:
            item_details.song_artist = artists[0]  # get first artist

    elif item_details.item_type == "MusicAlbum":
        item_details.album_artist = item["AlbumArtist"]
        item_details.album_name = item_details.name

    if item["Taglines"] is not None and len(item["Taglines"]) > 0:
        item_details.tagline = item["Taglines"][0]

    item_details.tags = []
    if item["TagItems"] is not None and len(item["TagItems"]) > 0:
        for tag_info in item["TagItems"]:
            item_details.tags.append(tag_info["Name"])

    # set the item name
    # override with name format string from request
    name_format = gui_options.name_format
    name_format_type = gui_options.name_format_type

    if name_format is not None and item_details.item_type == name_format_type:
        name_info = {}
        name_info["ItemName"] = item["Name"]
        season_name = item["SeriesName"]
        if season_name:
            name_info["SeriesName"] = season_name
        else:
            name_info["SeriesName"] = ""
        name_info["SeasonIndex"] = "%02d" % item_details.season_number
        name_info["EpisodeIndex"] = "%02d" % item_details.episode_number
        log.debug("FormatName: {0} | {1}", name_format, name_info)
        item_details.name = str(name_format).format(**name_info).strip()

    year = item["ProductionYear"]
    prem_date = item["PremiereDate"]

    if year is not None:
        item_details.year = year
    elif prem_date is not None:
        item_details.year = int(prem_date[:4])

    if prem_date is not None:
        tokens = prem_date.split("T")
        item_details.premiere_date = tokens[0]

    # use premier date for date added
    if gui_options.use_prem_date_for_added and item_details.premiere_date is not None:
        item_details.date_added = item_details.premiere_date + " 00:00:00"
    else:
        create_date = item["DateCreated"]
        if create_date is not None:
            item_details.date_added = create_date.split(".")[0].replace("T", " ")

    # add the premiered date for Upcoming TV
    if item_details.location_type == "Virtual":
        airtime = item["AirTime"]
        if (
            item_details.name
            and item_details.premiere_date is not None
            and airtime is not None
        ):
            item_details.name = (
                f"{item_details.name} - {item_details.premiere_date} - {airtime}"
            )

    if item_details.item_type == "Program":
        item_details.program_channel_name = item["ChannelName"]
        item_details.program_start_date = item["StartDate"]
        item_details.program_end_date = item["EndDate"]

    # Process MediaStreams
    media_streams = item["MediaStreams"]
    if media_streams is not None:
        media_info_list = []
        for mediaStream in media_streams:
            stream_type = mediaStream["Type"]
            if stream_type == "Video":
                media_info = MediaStream()
                media_info.set_type("video")
                media_info.set_codec(mediaStream["Codec"])
                media_info.set_height(mediaStream["Height"])
                media_info.set_width(mediaStream["Width"])
                aspect_ratio = mediaStream["AspectRatio"]
                ar = 1.85
                if aspect_ratio is not None and len(aspect_ratio) >= 3:
                    try:
                        aspect_width, aspect_height = aspect_ratio.split(":")
                        ar = float(aspect_width) / float(aspect_height)
                    except Exception:
                        pass
                media_info.set_aspect_ratio(ar)
                media_info.set_hdr_type(mediaStream["ExtendedVideoType"])
                media_info_list.append(media_info)
            if stream_type == "Audio":
                media_info = MediaStream()
                media_info.set_type("audio")
                media_info.set_codec(mediaStream["Codec"])
                media_info.set_channels(mediaStream["Channels"])
                media_info.set_language(mediaStream["Language"])
                media_info_list.append(media_info)
            if stream_type == "Subtitle":
                item_details.subtitle_available = True
                media_info = MediaStream()
                media_info.set_type("sub")
                media_info.set_language(mediaStream["Language"])
                media_info_list.append(media_info)

        item_details.media_streams = media_info_list

    # Process People
    people = item["People"]
    if people is not None:
        cast = []
        for person in people:
            person_type = person["Type"]
            if person_type == "Director" and person["Name"] is not None:
                item_details.director = item_details.director + person["Name"] + " "
            elif person_type == "Writing" and person["Name"] is not None:
                item_details.writer = person["Name"]
            elif person_type == "Actor" and person["Name"] is not None:
                # log.debug("Person: {0}", person)
                person_name = person["Name"]
                person_role = person["Role"]
                person_id = person["Id"]
                person_tag = person["PrimaryImageTag"]
                if person_tag is not None:
                    person_thumbnail = download_utils.image_url(
                        person_id,
                        "Primary",
                        0,
                        400,
                        400,
                        person_tag,
                        server=server_url,
                    )
                else:
                    person_thumbnail = ""
                person = Person(person_name, person_role, person_thumbnail)
                cast.append(person)
        item_details.cast = cast

    # Process Studios
    studios = item["Studios"]
    if studios is not None:
        for studio in studios:
            if item_details.studio is None:  # Just take the first one
                studio_name = studio["Name"]
                item_details.studio = studio_name
                break

    # production location
    prod_location = item["ProductionLocations"]
    # log.debug("ProductionLocations : {0}", prod_location)
    if prod_location is not None and len(prod_location) > 0:
        item_details.production_location = prod_location[0]

    # Process Genres
    genres = item["Genres"]
    if genres is not None and len(genres) > 0:
        item_details.genres = genres

    # Process UserData
    user_data = item["UserData"]
    if user_data is None:
        user_data = defaultdict(lambda: None, {})

    if user_data["Played"] is True:
        item_details.overlay = "6"
        item_details.play_count = 1
    else:
        item_details.overlay = "7"
        item_details.play_count = 0

    if user_data["IsFavorite"] is True:
        item_details.overlay = "5"
        item_details.favorite = "true"
    else:
        item_details.favorite = "false"

    reasonable_ticks = user_data["PlaybackPositionTicks"]
    if reasonable_ticks is not None:
        reasonable_ticks = int(reasonable_ticks) / 1000
        item_details.resume_time = int(reasonable_ticks / 10000)

    item_details.series_name = item["SeriesName"]
    item_details.plot = item["Overview"]

    runtime = item["RunTimeTicks"]
    if item_details.is_folder is False and runtime is not None:
        item_details.duration = int(runtime) / 10000000

    child_count = item["ChildCount"]
    if child_count is not None:
        item_details.total_seasons = child_count

    recursive_item_count = item["RecursiveItemCount"]
    if recursive_item_count is not None:
        item_details.total_episodes = recursive_item_count

    unplayed_item_count = user_data["UnplayedItemCount"]
    if unplayed_item_count is not None:
        item_details.unwatched_episodes = unplayed_item_count
        item_details.watched_episodes = (
            item_details.total_episodes - unplayed_item_count
        )

    item_details.number_episodes = item_details.total_episodes

    item_details.art = get_art(
        item,
        server_url,
        maxwidth=gui_options.max_image_width,
        download_utils=download_utils,
    )
    item_details.mpaa = item["OfficialRating"]

    item_details.community_rating = item["CommunityRating"]
    if item_details.community_rating is None:
        item_details.community_rating = 0.0

    item_details.critic_rating = item["CriticRating"]
    if item_details.critic_rating is None:
        item_details.critic_rating = 0.0

    item_details.location_type = item["LocationType"]
    item_details.recursive_item_count = item["RecursiveItemCount"]
    item_details.recursive_unplayed_items_count = user_data["UnplayedItemCount"]

    item_details.mode = "GET_CONTENT"

    return item_details


def add_gui_item(
    url: str,
    item_details: ItemDetails,
    display_options: DisplayOptions,
    folder: bool = True,
    default_sort: bool = False,
) -> GuiItem | None:
    # log.debug("item_details: {0}", item_details.__dict__)

    if not item_details.name:
        return None

    if item_details.mode:
        mode = "&mode=%s" % item_details.mode
    else:
        mode = "&mode=0"

    # Create the URL to pass to the item
    item_type = item_details.item_type or "none"
    if folder:
        u = (
            sys.argv[0]
            + "?url="
            + urllib.parse.quote(url)
            + mode
            + "&media_type="
            + item_type
        )
        if item_details.name_format:
            u += "&name_format=" + urllib.parse.quote(item_details.name_format)
        if default_sort:
            u += "&sort=none"
    else:
        u = sys.argv[0] + "?item_id=" + url + "&mode=PLAY"

    # Create the ListItem that will be displayed
    list_item_name = item_details.name
    item_type = item_type.lower()
    is_video = item_type not in ["musicalbum", "audio", "music"]

    # calculate percentage
    capped_percentage = 0
    if item_details.resume_time > 0:
        duration = float(item_details.duration)
        if duration > 0:
            resume = float(item_details.resume_time)
            percentage = int((resume / duration) * 100.0)
            capped_percentage = percentage

    total_items = item_details.total_episodes
    if total_items != 0:
        watched = float(item_details.watched_episodes)
        percentage = int((watched / float(total_items)) * 100.0)
        capped_percentage = percentage

    counts_added = False
    add_counts = display_options.addCounts
    if add_counts and item_details.unwatched_episodes != 0:
        counts_added = True
        list_item_name = list_item_name + (" (%s)" % item_details.unwatched_episodes)

    add_resume_percent = display_options.addResumePercent
    if not counts_added and add_resume_percent and capped_percentage not in [0, 100]:
        list_item_name = list_item_name + (" (%s%%)" % capped_percentage)

    subtitle_available = display_options.addSubtitleAvailable
    if subtitle_available and item_details.subtitle_available:
        list_item_name += " (cc)"

    if item_details.item_type == "Program":
        start_time = datetime.now()
        end_time = start_time.now()
        if (
            item_details.program_start_date is not None
            and item_details.program_end_date is not None
        ):
            start_time = datetime_from_string(item_details.program_start_date)
            end_time = datetime_from_string(item_details.program_end_date)

        duration: float = (end_time - start_time).total_seconds()
        time_done: float = (datetime.now() - start_time).total_seconds()
        percentage_done = (float(time_done) / float(duration)) * 100.0
        capped_percentage = int(percentage_done)

        start_time_string = start_time.strftime("%H:%M")
        end_time_string = end_time.strftime("%H:%M")

        item_details.duration = int(duration)
        item_details.resume_time = int(time_done)

        channel = item_details.program_channel_name or "Unknown Channel"
        list_item_name = (
            channel
            + " - "
            + list_item_name
            + " - "
            + start_time_string
            + " to "
            + end_time_string
            + " ("
            + str(int(percentage_done))
            + "%)"
        )

        time_info = "Start : " + start_time_string + "\n"
        time_info += "End : " + end_time_string + "\n"
        time_info += "Complete : " + str(int(percentage_done)) + "%\n"
        if item_details.plot:
            item_details.plot = time_info + item_details.plot
        else:
            item_details.plot = time_info

    list_item = xbmcgui.ListItem(list_item_name, offscreen=True)
    # log.debug("Setting thumbnail as: {0}", thumbPath)

    item_properties = {}
    item_properties["IsPlayable"] = "false"

    if item_details.art:
        list_item.setArt(item_details.art)
        item_properties["fanart_image"] = item_details.art["fanart"]  # back compat
        item_properties["discart"] = item_details.art["discart"]  # not avail to setArt
        item_properties["tvshow.poster"] = item_details.art[
            "tvshow.poster"
        ]  # not avail to setArt

    if item_details.series_id:
        item_properties["series_id"] = item_details.series_id

    mediatype = "video"

    if item_type == "movie":
        mediatype = "movie"
    elif item_type == "boxset":
        mediatype = "set"
    elif item_type == "series":
        mediatype = "tvshow"
    elif item_type == "season":
        mediatype = "season"
    elif item_type == "episode":
        mediatype = "episode"
    elif item_type == "musicalbum":
        mediatype = "album"
    elif item_type == "musicartist":
        mediatype = "artist"
    elif item_type == "audio" or item_type == "music":
        mediatype = "song"

    if is_video:
        info_tag_video: xbmc.InfoTagVideo = list_item.getVideoInfoTag()
        info_tag_video.setMediaType(mediatype)

        info_tag_video.setTitle(list_item_name)
        if item_details.sort_name:
            info_tag_video.setSortTitle(item_details.sort_name)

        info_tag_video.setPlaycount(item_details.play_count)
        if item_details.year is not None:
            info_tag_video.setYear(item_details.year)
        if item_details.mpaa is not None:
            info_tag_video.setMpaa(item_details.mpaa)

        if item_details.genres is not None and len(item_details.genres) > 0:
            info_tag_video.setGenres(item_details.genres)

        if item_details.cast is not None:
            actors = []
            for actor in item_details.cast:
                actors.append(
                    xbmc.Actor(
                        name=actor.name, role=actor.role, thumbnail=actor.thumbnail
                    )
                )
            info_tag_video.setCast(actors)

        if item_type == "episode":
            info_tag_video.setEpisode(item_details.episode_number)
            info_tag_video.setSeason(item_details.season_number)
            info_tag_video.setSortSeason(item_details.season_sort_number)
            info_tag_video.setSortEpisode(item_details.episode_sort_number)
            if item_details.series_name is not None:
                info_tag_video.setTvShowTitle(item_details.series_name)
            if item_details.season_number == 0:
                item_properties["IsSpecial"] = "true"

        elif item_type == "season":
            info_tag_video.setSeason(item_details.season_number)
            info_tag_video.setEpisode(item_details.total_episodes)
            if item_details.series_name is not None:
                info_tag_video.setTvShowTitle(item_details.series_name)
            if item_details.season_number == 0:
                item_properties["IsSpecial"] = "true"

        elif item_type == "series":
            info_tag_video.setEpisode(item_details.total_episodes)
            info_tag_video.setSeason(item_details.total_seasons)
            if item_details.status is not None:
                info_tag_video.setTvShowStatus(item_details.status)
            info_tag_video.setTvShowTitle(item_details.name)

        info_tag_video.setTagLine(item_details.tagline)
        if item_details.studio is not None:
            info_tag_video.setStudios([item_details.studio])
        if item_details.premiere_date is not None:
            info_tag_video.setFirstAired(item_details.premiere_date)
        if item_details.premiere_date is not None:
            info_tag_video.setPremiered(item_details.premiere_date)
        if item_details.date_added is not None:
            info_tag_video.setDateAdded(item_details.date_added)
        if item_details.plot is not None:
            info_tag_video.setPlot(item_details.plot)
        info_tag_video.setDirectors([item_details.director])
        info_tag_video.setWriters([item_details.writer])
        if item_details.production_location is not None:
            info_tag_video.setCountries([item_details.production_location])
        if item_details.tags is not None and len(item_details.tags) > 0:
            info_tag_video.setTags(item_details.tags)

        if item_details.id:
            info_tag_video.setDbId(int(item_details.id))

        if item_type in ("movie", "series") and item_details.id:
            info_tag_video.setTrailer(
                "plugin://plugin.video.embycon?mode=playTrailer&id=" + item_details.id
            )

        for stream in item_details.media_streams:
            if stream.type == "video":
                vsd = xbmc.VideoStreamDetail()
                vsd.setDuration(int(item_details.duration))
                vsd.setAspect(stream.aspect_ratio)
                vsd.setCodec(stream.codec)
                vsd.setWidth(stream.width)
                vsd.setHeight(stream.height)
                vsd.setHDRType(stream.hdr_type)
                info_tag_video.addVideoStream(vsd)

            elif stream.type == "audio":
                asd = xbmc.AudioStreamDetail()
                asd.setCodec(stream.codec)
                asd.setChannels(stream.channels)
                asd.setLanguage(stream.language)
                info_tag_video.addAudioStream(asd)

            elif stream.type == "sub":
                ssd = xbmc.SubtitleStreamDetail()
                ssd.setLanguage(stream.language)
                info_tag_video.addSubtitleStream(ssd)

        item_properties["TotalSeasons"] = str(item_details.total_seasons)
        item_properties["TotalEpisodes"] = str(item_details.total_episodes)
        item_properties["NumEpisodes"] = str(item_details.number_episodes)

        if (
            item_details.watched_episodes is not None
            and item_details.watched_episodes > 0
        ):
            item_properties["WatchedEpisodes"] = str(item_details.watched_episodes)
        item_properties["UnWatchedEpisodes"] = str(item_details.unwatched_episodes)
        item_properties["SeriesUnwatched"] = str(item_details.unwatched_episodes)

        info_tag_video.setRating(item_details.community_rating, type="imdb")
        info_tag_video.setUserRating(int(item_details.critic_rating))

        info_tag_video.setResumePoint(item_details.resume_time, item_details.duration)
        # info_tag_video.setDuration(item_details.duration)

    else:
        info_tag_music: xbmc.InfoTagMusic = list_item.getMusicInfoTag()
        info_tag_music.setMediaType(mediatype)

        info_tag_music.setTitle(list_item_name)
        info_tag_music.setDuration(int(item_details.duration))

        if item_details.year is not None:
            info_tag_music.setYear(item_details.year)

        if item_details.genres is not None and len(item_details.genres) > 0:
            info_tag_music.setGenres(item_details.genres)

        info_tag_music.setTrack(item_details.track_number)
        if item_details.album_name is not None:
            info_tag_music.setAlbum(item_details.album_name)
        if item_details.album_artist:
            info_tag_music.setAlbumArtist(item_details.album_artist)
        if item_details.song_artist:
            info_tag_music.setArtist(item_details.song_artist)

    list_item.setContentLookup(False)
    item_properties["ItemType"] = item_details.item_type
    item_properties["id"] = item_details.id

    if item_details.baseline_itemname is not None:
        item_properties["suggested_from_watching"] = item_details.baseline_itemname

    # log.debug("item_properties: {0}", item_properties)
    list_item.setProperties(item_properties)

    return GuiItem(url=u, list_item=list_item, is_folder=folder)
