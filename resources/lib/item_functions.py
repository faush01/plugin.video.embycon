
import sys
import os
import urllib.request
import urllib.parse
import urllib.error

from datetime import datetime

from collections import defaultdict
from typing import List, Dict, Any, Union

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from .utils import get_art, datetime_from_string
from .simple_logging import SimpleLogging
from .downloadutils import DownloadUtils
from .kodi_utils import HomeWindow

log = SimpleLogging(__name__)
kodi_version = int(xbmc.getInfoLabel('System.BuildVersion')[:2])

addon_instance = xbmcaddon.Addon()
addon_path = addon_instance.getAddonInfo('path')
PLUGINPATH = xbmcvfs.translatePath(os.path.join(addon_path))

download_utils = DownloadUtils()
home_window = HomeWindow()


class MediaStream:
    type: str = "na"
    width: int = 0
    height: int = 0
    channels: int = 0
    codec: str = "na"
    aspect_ratio: float = 1.0
    language: str = "na"

    # "default" if x is None else x

    def set_channels(self, value):
        if value is not None:
            self.channels = int(value)

    def set_language(self, value):
        if value is not None:
            self.language = value

    def set_aspect_ratio(self, value):
        if value is not None:
            self.aspect_ratio = float(value)

    def set_type(self, value):
        if value is not None:
            self.type = value

    def set_codec(self, value):
        if value is not None:
            self.codec = value

    def set_width(self, value):
        if value is not None:
            self.width = int(value)

    def set_height(self, value):
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
    media_streams: List[MediaStream] = []
    cast: List[Person] = []

    # values
    name: Union[str, None] = None
    sort_name: Union[str, None] = None
    id: Union[str, None] = None
    etag: Union[str, None] = None
    path: Union[str, None] = None
    is_folder: Union[bool, None] = False
    plot: Union[str, None] = None
    series_name: Union[str, None] = None
    episode_number: int = 0
    season_number: int = 0
    episode_sort_number: int = 0
    season_sort_number: int = 0
    track_number: int = 0
    series_id: Union[str, None] = None
    art: Union[Dict[str, str], None] = None

    mpaa: Union[str, None] = None
    rating: Union[str, None] = None
    critic_rating: float = 0.0
    community_rating: float = 0.0
    year: Union[int, None] = None
    premiere_date: str = ""
    date_added: str = ""
    location_type: Union[str, None] = None
    studio: Union[str, None] = None
    production_location: Union[str, None] = None
    genres: Union[str, None] = None
    play_count: Union[int, None] = 0
    director: str = ""
    writer: str = ""
    tagline: str = ""
    status: Union[str, None] = None
    tags: Union[List[str], None] = None

    resume_time: int = 0
    duration: int = 0
    recursive_item_count: int = 0
    recursive_unplayed_items_count: int = 0
    total_seasons: int = 0
    total_episodes: int = 0
    watched_episodes: int = 0
    unwatched_episodes: int = 0
    number_episodes: int = 0
    original_title: Union[str, None] = None
    item_type: Union[str, None] = None
    subtitle_available: bool = False
    total_items: int = 0

    song_artist: str = ""
    album_artist: str = ""
    album_name: Union[str, None] = ""

    program_channel_name: Union[str, None] = None
    program_end_date: Union[str, None] = None
    program_start_date: Union[str, None] = None

    favorite: str = "false"
    overlay: str = "0"

    name_format: str = ""
    mode: str = ""

    baseline_itemname: Union[str, None] = None

    def set_episode_number(self, value: int):
        if value is not None:
            self.episode_number = value

    def set_season_sort_number(self, value: int):
        if value is not None:
            self.season_sort_number = value

    def set_season_number(self, value: int):
        if value is not None:
            self.season_number = value

    def set_episode_sort_number(self, value: int):
        if value is not None:
            self.episode_sort_number = value


def extract_media_info(item):
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
            media_info.append(" -DefaultAudioStreamIndex: %s" % (media_source["DefaultAudioStreamIndex"],))

            media_streams = media_source["MediaStreams"]
            if media_streams is not None:
                for mediaStream in media_streams:
                    stream_type = mediaStream["Type"]
                    if stream_type == "Video":
                        media_info.append(" -Video Stream")
                        media_info.append("   -Index: %s" % (mediaStream["Index"],))
                        media_info.append("   -Codec: %s" % (mediaStream["Codec"],))
                        media_info.append("   -Size: %sx%s" % (mediaStream["Width"], mediaStream["Height"]))
                        media_info.append("   -AspectRatio: %s" % (mediaStream["AspectRatio"],))
                        media_info.append("   -ColorSpace: %s" % (mediaStream["ColorSpace"],))
                        media_info.append("   -DisplayTitle: %s" % (mediaStream["DisplayTitle"],))
                        media_info.append("   -IsInterlaced: %s" % (mediaStream["IsInterlaced"],))
                        if mediaStream["BitRate"] is not None:
                            media_info.append("   -BitRate: {:,}".format(mediaStream["BitRate"]))
                        media_info.append("   -BitDepth: %s" % (mediaStream["BitDepth"],))
                        media_info.append("   -AverageFrameRate: %s" % (mediaStream["AverageFrameRate"],))
                        media_info.append("   -RealFrameRate: %s" % (mediaStream["RealFrameRate"],))
                        media_info.append("   -Profile: %s" % (mediaStream["Profile"],))
                        media_info.append("   -Level: %s" % (mediaStream["Level"],))
                        media_info.append("   -PixelFormat: %s" % (mediaStream["PixelFormat"],))
                        media_info.append("   -IsAnamorphic: %s" % (mediaStream["IsAnamorphic"],))

                    if stream_type == "Audio":
                        media_info.append(" -Audio Stream")
                        media_info.append("   -Index: %s" % (mediaStream["Index"],))
                        media_info.append("   -Title: %s" % (mediaStream["DisplayTitle"],))
                        media_info.append("   -Codec: %s" % (mediaStream["Codec"],))
                        media_info.append("   -ChannelLayout: %s" % (mediaStream["ChannelLayout"],))
                        media_info.append("   -Channels: %s" % (mediaStream["Channels"],))
                        if mediaStream["BitRate"] is not None:
                            media_info.append("   -BitRate: {:,}".format(mediaStream["BitRate"]))
                        media_info.append("   -SampleRate: %s" % (mediaStream["SampleRate"],))
                        media_info.append("   -IsDefault: %s" % (mediaStream["IsDefault"],))
                        media_info.append("   -IsForced: %s" % (mediaStream["IsForced"],))
                        media_info.append("   -IsExternal: %s" % (mediaStream["IsExternal"],))
                        media_info.append("   -IsExternal: %s" % (mediaStream["IsExternal"],))

                    if stream_type == "Subtitle":
                        media_info.append(" -Subtitle Stream")
                        media_info.append("   -Index: %s" % (mediaStream["Index"],))
                        media_info.append("   -Codec: %s" % (mediaStream["Codec"],))
                        media_info.append("   -Language: %s" % (mediaStream["Language"],))
                        media_info.append("   -DisplayTitle: %s" % (mediaStream["DisplayTitle"],))
                        media_info.append("   -DisplayLanguage: %s" % (mediaStream["DisplayLanguage"],))
                        media_info.append("   -IsDefault: %s" % (mediaStream["IsDefault"],))
                        media_info.append("   -IsForced: %s" % (mediaStream["IsForced"],))
                        media_info.append("   -IsExternal: %s" % (mediaStream["IsExternal"],))
                        media_info.append("   -IsTextSubtitleStream: %s" % (mediaStream["IsTextSubtitleStream"],))

            media_info.append("")

    return media_info


def extract_item_info(item: Any, gui_options: Dict[str, str]) -> ItemDetails:

    item_details = ItemDetails()

    item_details.id = item["Id"]
    item_details.etag = item["Etag"]
    item_details.is_folder = item["IsFolder"]
    item_details.item_type = item["Type"]
    item_details.location_type = item["LocationType"]
    item_details.name = item["Name"]
    item_details.sort_name = item["SortName"]
    item_details.original_title = item_details.name

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
    name_format = gui_options["name_format"]
    name_format_type = gui_options["name_format_type"]

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

    create_date = item["DateCreated"]
    if create_date is not None:
        item_details.date_added = create_date.split('.')[0].replace('T', " ")

    # add the premiered date for Upcoming TV
    if item_details.location_type == "Virtual":
        airtime: str = item["AirTime"]
        new_name: str = "{0} - {1} - {2}".format(item_details.name, item_details.premiere_date, airtime)
        item_details.name = new_name

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
                        aspect_width, aspect_height = aspect_ratio.split(':')
                        ar = float(aspect_width) / float(aspect_height)
                    except:
                        pass
                media_info.set_aspect_ratio(ar)
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
        cast: List[Person] = []
        for person in people:
            person_type = person["Type"]
            if person_type == "Director" and person["Name"] is not None:
                item_details.director = item_details.director + person["Name"] + ' '
            elif person_type == "Writing" and person["Name"] is not None:
                item_details.writer = person["Name"]
            elif person_type == "Actor" and person["Name"] is not None:
                # log.debug("Person: {0}", person)
                person_name = person["Name"]
                person_role = person["Role"]
                person_id = person["Id"]
                person_tag = person["PrimaryImageTag"]
                if person_tag is not None:
                    person_thumbnail = download_utils.image_url(person_id,
                                                                "Primary", 0, 400, 400,
                                                                person_tag,
                                                                server=gui_options["server"])
                else:
                    person_thumbnail = ""
                new_person: Person = Person(person_name, person_role, person_thumbnail)
                cast.append(new_person)
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
    if prod_location and len(prod_location) > 0:
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
        item_details.duration = int(int(runtime) / 10000000)

    child_count = item["ChildCount"]
    if child_count is not None:
        item_details.total_seasons = child_count

    recursive_item_count = item["RecursiveItemCount"]
    if recursive_item_count is not None:
        item_details.total_episodes = recursive_item_count

    unplayed_item_count = user_data["UnplayedItemCount"]
    if unplayed_item_count is not None:
        item_details.unwatched_episodes = unplayed_item_count
        item_details.watched_episodes = item_details.total_episodes - unplayed_item_count

    item_details.number_episodes = item_details.total_episodes

    item_details.art = get_art(item, gui_options["server"], maxwidth=gui_options["max_image_width"])
    item_details.rating = item["OfficialRating"]
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


def add_gui_item(url, item_details, display_options, folder=True, default_sort=False):

    # log.debug("item_details: {0}", item_details.__dict__)

    if not item_details.name:
        return None

    if item_details.mode:
        mode = "&mode=%s" % item_details.mode
    else:
        mode = "&mode=0"

    # Create the URL to pass to the item
    if folder:
        u = sys.argv[0] + "?url=" + urllib.parse.quote(url) + mode + "&media_type=" + item_details.item_type
        if item_details.name_format:
            u += '&name_format=' + urllib.parse.quote(item_details.name_format)
        if default_sort:
            u += '&sort=none'
    else:
        u = sys.argv[0] + "?item_id=" + url + "&mode=PLAY"

    # Create the ListItem that will be displayed
    thumb_path = item_details.art["thumb"]

    list_item_name = item_details.name
    item_type = item_details.item_type.lower()
    is_video = item_type not in ['musicalbum', 'audio', 'music']

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
    add_counts = display_options["addCounts"]
    if add_counts and item_details.unwatched_episodes != 0:
        counts_added = True
        list_item_name = list_item_name + (" (%s)" % item_details.unwatched_episodes)

    add_resume_percent = display_options["addResumePercent"]
    if (not counts_added
            and add_resume_percent
            and capped_percentage not in [0, 100]):
        list_item_name = list_item_name + (" (%s%%)" % capped_percentage)

    subtitle_available = display_options["addSubtitleAvailable"]
    if subtitle_available and item_details.subtitle_available:
        list_item_name += " (cc)"

    if item_details.item_type == "Program":
        start_time = datetime_from_string(item_details.program_start_date)
        end_time = datetime_from_string(item_details.program_end_date)

        duration = (end_time - start_time).total_seconds()
        time_done = (datetime.now() - start_time).total_seconds()
        percentage_done = (float(time_done) / float(duration)) * 100.0
        capped_percentage = int(percentage_done)

        start_time_string = start_time.strftime("%H:%M")
        end_time_string = end_time.strftime("%H:%M")

        item_details.duration = int(duration)
        item_details.resume_time = int(time_done)

        list_item_name = (item_details.program_channel_name +
                          " - " + list_item_name +
                          " - " + start_time_string + " to " + end_time_string +
                          " (" + str(int(percentage_done)) + "%)")

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

    # calculate percentage
    #if capped_percentage != 0:
    #    item_properties["complete_percentage"] = str(capped_percentage)

    item_properties["IsPlayable"] = 'false'

    #if not folder and is_video:
    #    item_properties["TotalTime"] = str(item_details.duration)
    #    item_properties["ResumeTime"] = str(item_details.resume_time)

    list_item.setArt(item_details.art)

    item_properties["fanart_image"] = item_details.art['fanart']  # back compat
    item_properties["discart"] = item_details.art['discart']  # not avail to setArt
    item_properties["tvshow.poster"] = item_details.art['tvshow.poster']  # not avail to setArt

    if item_details.series_id:
        item_properties["series_id"] = item_details.series_id

    # new way
    # info_labels = {}

    # add cast
    #if item_details.cast is not None:
    #    list_item.setCast(item_details.cast)

    #info_labels["title"] = list_item_name
    #if item_details.sort_name:
    #    info_labels["sorttitle"] = item_details.sort_name
    #else:
    #    info_labels["sorttitle"] = list_item_name

    #info_labels["duration"] = item_details.duration
    #info_labels["playcount"] = item_details.play_count
    # if item_details.favorite == 'true':
    #    info_labels["top250"] = "1"

    #info_labels["rating"] = item_details.rating
    #info_labels["year"] = item_details.year

    #if item_details.genres is not None and len(item_details.genres) > 0:
    #    genres_list = []
    #    for genre in item_details.genres:
    #        genres_list.append(urllib.parse.quote(genre.encode('utf8')))
    #    item_properties["genres"] = urllib.parse.quote("|".join(genres_list))

    #    info_labels["genre"] = " / ".join(item_details.genres)

    mediatype = 'video'

    if item_type == 'movie':
        mediatype = 'movie'
    elif item_type == 'boxset':
        mediatype = 'set'
    elif item_type == 'series':
        mediatype = 'tvshow'
    elif item_type == 'season':
        mediatype = 'season'
    elif item_type == 'episode':
        mediatype = 'episode'
    elif item_type == 'musicalbum':
        mediatype = 'album'
    elif item_type == 'musicartist':
        mediatype = 'artist'
    elif item_type == 'audio' or item_type == 'music':
        mediatype = 'song'

    # info_labels["mediatype"] = mediatype

    if is_video:
        info_tag_video = list_item.getVideoInfoTag()
        info_tag_video.setMediaType(mediatype)

        info_tag_video.setTitle(list_item_name)
        if item_details.sort_name:
            info_tag_video.setSortTitle(item_details.sort_name)

        info_tag_video.setPlaycount(item_details.play_count)
        if item_details.year is not None:
            info_tag_video.setYear(item_details.year)
        info_tag_video.setMpaa(item_details.rating)

        if item_details.genres is not None and len(item_details.genres) > 0:
            info_tag_video.setGenres(item_details.genres)

        if item_details.cast is not None:
            actors = []
            for actor in item_details.cast:
                actors.append(xbmc.Actor(name=actor.name, role=actor.role, thumbnail=actor.thumbnail))
            info_tag_video.setCast(actors)

        if item_type == 'episode':
            info_tag_video.setEpisode(item_details.episode_number)
            info_tag_video.setSeason(item_details.season_number)
            info_tag_video.setSortSeason(item_details.season_sort_number)
            info_tag_video.setSortEpisode(item_details.episode_sort_number)
            info_tag_video.setTvShowTitle(item_details.series_name)
            # info_labels["episode"] = item_details.episode_number
            # info_labels["season"] = item_details.season_number
            # info_labels["sortseason"] = item_details.season_sort_number
            # info_labels["sortepisode"] = item_details.episode_sort_number
            # info_labels["tvshowtitle"] = item_details.series_name
            if item_details.season_number == 0:
                item_properties["IsSpecial"] = "true"

        elif item_type == 'season':
            info_tag_video.setSeason(item_details.season_number)
            info_tag_video.setEpisode(item_details.total_episodes)
            info_tag_video.setTvShowTitle(item_details.series_name)
            # info_labels["season"] = item_details.season_number
            # info_labels["episode"] = item_details.total_episodes
            # info_labels["tvshowtitle"] = item_details.series_name
            if item_details.season_number == 0:
                item_properties["IsSpecial"] = "true"

        elif item_type == "series":
            info_tag_video.setEpisode(item_details.total_episodes)
            info_tag_video.setSeason(item_details.total_seasons)
            info_tag_video.setTvShowStatus(item_details.status)
            info_tag_video.setTvShowTitle(item_details.name)
            # info_labels["episode"] = item_details.total_episodes
            # info_labels["season"] = item_details.total_seasons
            # info_labels["status"] = item_details.status
            # info_labels["tvshowtitle"] = item_details.name

        info_tag_video.setTagLine(item_details.tagline)
        info_tag_video.setStudios([item_details.studio])
        info_tag_video.setPremiered(item_details.premiere_date)
        info_tag_video.setPlot(item_details.plot)
        info_tag_video.setDirectors([item_details.director])
        info_tag_video.setWriters([item_details.writer])
        info_tag_video.setDateAdded(item_details.date_added)
        info_tag_video.setCountries([item_details.production_location])
        if item_details.tags is not None and len(item_details.tags) > 0:
            info_tag_video.setTags(item_details.tags)

        # info_labels["Overlay"] = item_details.overlay # not used ??
        # info_labels["tagline"] = item_details.tagline
        # info_labels["studio"] = item_details.studio
        # info_labels["premiered"] = item_details.premiere_date
        # info_labels["plot"] = item_details.plot
        # info_labels["director"] = item_details.director
        # info_labels["writer"] = item_details.writer
        # info_labels["dateadded"] = item_details.date_added
        # info_labels["country"] = item_details.production_location
        # info_labels["mpaa"] = item_details.mpaa
        # info_labels["tag"] = item_details.tags

        # if display_options["addUserRatings"]:
        #    info_labels["userrating"] = item_details.critic_rating

        if item_type in ('movie', 'series'):
            # info_labels["trailer"] = "plugin://plugin.video.embycon?mode=playTrailer&id=" + item_details.id
            info_tag_video.setTrailer("plugin://plugin.video.embycon?mode=playTrailer&id=" + item_details.id)

        # list_item.setInfo('video', info_labels)
        # log.debug("info_labels: {0}", info_labels)
        for stream in item_details.media_streams:
            if stream.type == "video":
                vsd = xbmc.VideoStreamDetail()
                vsd.setDuration(int(item_details.duration))
                vsd.setAspect(stream.aspect_ratio)
                vsd.setCodec(stream.codec)
                vsd.setWidth(stream.width)
                vsd.setHeight(stream.height)
                info_tag_video.addVideoStream(vsd)

                # list_item.addStreamInfo('video',
                #                        {'duration': item_details.duration,
                #                         'aspect': stream["apect_ratio"],
                #                         'codec': stream["codec"],
                #                         'width': stream["width"],
                #                         'height': stream["height"]})

            elif stream.type == "audio":
                asd = xbmc.AudioStreamDetail()
                asd.setCodec(stream.codec)
                asd.setChannels(stream.channels)
                asd.setLanguage(stream.language)
                info_tag_video.addAudioStream(asd)

                # list_item.addStreamInfo('audio',
                #                        {'codec': stream["codec"],
                #                         'channels': stream["channels"],
                #                         'language': stream["language"]})

            elif stream.type == "sub":
                ssd = xbmc.SubtitleStreamDetail()
                ssd.setLanguage(stream.language)
                info_tag_video.addSubtitleStream(ssd)

                # list_item.addStreamInfo('subtitle',
                #                        {'language': stream["language"]})

        item_properties["TotalSeasons"] = str(item_details.total_seasons)
        item_properties["TotalEpisodes"] = str(item_details.total_episodes)
        item_properties["NumEpisodes"] = str(item_details.number_episodes)

        if item_details.watched_episodes is not None and item_details.watched_episodes > 0:
            item_properties["WatchedEpisodes"] = str(item_details.watched_episodes)
        item_properties["UnWatchedEpisodes"] = str(item_details.unwatched_episodes)
        item_properties["SeriesUnwatched"] = str(item_details.unwatched_episodes)

        info_tag_video.setRating(item_details.community_rating, type="imdb")
        info_tag_video.setUserRating(int(item_details.critic_rating))

        info_tag_video.setResumePoint(item_details.resume_time, item_details.duration)
        #info_tag_video.setDuration(item_details.duration)

        #list_item.setRating("imdb", item_details.community_rating, 0, True)
        # list_item.setRating("rt", item_details.critic_rating, 0, False)
        #item_properties["TotalTime"] = str(item_details.duration)

    else:
        info_tag_music = list_item.getMusicInfoTag()
        info_tag_music.setMediaType(mediatype)

        info_tag_music.setTitle(list_item_name)
        info_tag_music.setDuration(int(item_details.duration))

        if item_details.year is not None:
            info_tag_music.setYear(item_details.year)

        if item_details.genres is not None and len(item_details.genres) > 0:
            info_tag_music.setGenres(item_details.genres)

        info_tag_music.setTrack(item_details.track_number)
        info_tag_music.setAlbum(item_details.album_name)
        if item_details.album_artist:
            info_tag_music.setAlbumArtist(item_details.album_artist)
        if item_details.song_artist:
            info_tag_music.setArtist(item_details.song_artist)

        # info_labels = {}
        # info_labels["tracknumber"] = item_details.track_number
        # if item_details.album_artist:
        #    info_labels["artist"] = item_details.album_artist
        # elif item_details.song_artist:
        #    info_labels["artist"] = item_details.song_artist
        # info_labels["album"] = item_details.album_name
        # log.debug("info_labels: {0}", info_labels)
        # list_item.setInfo('music', info_labels)

    list_item.setContentLookup(False)
    item_properties["ItemType"] = item_details.item_type
    item_properties["id"] = item_details.id

    if item_details.baseline_itemname is not None:
        item_properties["suggested_from_watching"] = item_details.baseline_itemname

    # log.debug("item_properties: {0}", item_properties)
    list_item.setProperties(item_properties)

    return u, list_item, folder
