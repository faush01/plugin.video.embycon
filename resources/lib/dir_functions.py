# Gnu General Public License - see LICENSE.TXT

import xbmcaddon
import xbmcplugin
import xbmcgui
import xbmcvfs

import urllib.request
import urllib.parse
import urllib.error
import sys
import os
import re

from .datamanager import DataManager
from .downloadutils import DownloadUtils
from .translation import string_load
from .simple_logging import SimpleLogging
from .item_functions import add_gui_item, ItemDetails
from .utils import send_event_notification
from .tracking import timer
from .filelock import FileLock

log = SimpleLogging(__name__)


@timer
def get_content(url, params):
    log.debug("== ENTER: getContent ==")

    default_sort = params.get("sort")
    media_type = params.get("media_type", None)
    if not media_type:
        xbmcgui.Dialog().ok(string_load(30135), string_load(30139))

    log.debug("URL: {0}", url)
    log.debug("MediaType: {0}", media_type)
    pluginhandle = int(sys.argv[1])

    settings = xbmcaddon.Addon()
    # determine view type, map it from media type to view type
    view_type = ""
    content_type = ""
    media_type = str(media_type).lower().strip()
    if media_type.startswith("movie"):
        view_type = "Movies"
        content_type = 'movies'
    elif media_type == "musicalbums":
        view_type = "Albums"
        content_type = 'albums'
    elif media_type == "musicartists":
        view_type = "Artists"
        content_type = 'artists'
    elif media_type == "musicartist":
        view_type = "Albums"
        content_type = 'albums'
    elif media_type == "music" or media_type == "audio" or media_type == "musicalbum":
        view_type = "Music"
        content_type = 'songs'
    elif media_type.startswith("boxsets"):
        view_type = "Movies"
        content_type = 'sets'
    elif media_type.startswith("boxset"):
        view_type = "BoxSets"
        content_type = 'movies'
    elif media_type == "tvshows":
        view_type = "Series"
        content_type = 'tvshows'
    elif media_type == "series":
        view_type = "Seasons"
        content_type = 'seasons'
    elif media_type == "season" or media_type == "episodes":
        view_type = "Episodes"
        content_type = 'episodes'
    elif media_type == "playlists":
        view_type = "Playlists"

    log.debug("media_type:{0} content_type:{1} view_type:{2} ", media_type, content_type, view_type)

    # show a progress indicator if needed
    progress = None
    if settings.getSetting('showLoadProgress') == "true":
        progress = xbmcgui.DialogProgress()
        progress.create(string_load(30112))
        progress.update(0, string_load(30113))

    # update url for paging
    start_index = 0
    page_limit = int(settings.getSetting('itemsPerPage'))
    url_prev = None
    url_next = None
    if page_limit > 0 and media_type.lower() in ["movies", "movie", "tvshows"]:
        log.debug("Creating Paging URLS: {0}", url)
        start_index_rex = "startindex=([0-9]{1,5})"
        limit_rex = "&limit=([0-9]{1,5})"
        limit_rex_p = "&Limit={ItemLimit}"

        # add StartIndex and Limit to the url if they are not there already
        # update limit to page limit if it is alreayd there
        if not re.search(start_index_rex, url, flags=re.IGNORECASE):
            url += "&StartIndex=0"

        if not re.search(limit_rex, url, flags=re.IGNORECASE) and not re.search(limit_rex_p, url, flags=re.IGNORECASE):
            url += "&Limit=" + str(page_limit)
        else:
            url = re.sub(limit_rex, '&Limit=' + str(page_limit), url, flags=re.IGNORECASE)
            url = re.sub(limit_rex_p, '&Limit=' + str(page_limit), url, flags=re.IGNORECASE)

        # create NEXT and PREV urls
        start_index_match = re.search(start_index_rex, url, flags=re.IGNORECASE)
        start_index = int(start_index_match.group(1))
        if start_index > 0:
            prev_index = start_index - page_limit
            if prev_index < 0:
                prev_index = 0
            url_prev = re.sub(start_index_rex, 'StartIndex=' + str(prev_index), url, flags=re.IGNORECASE)
        url_next = re.sub(start_index_rex, 'StartIndex=' + str(start_index + page_limit), url, flags=re.IGNORECASE)

        log.debug("Paged URLS - url_current: {0}", url)
        log.debug("Paged URLS - url_prev: {0}", url_prev)
        log.debug("Paged URLS - url_next: {0}", url_next)

    # use the data manager to get the data
    # result = dataManager.get_content(url)

    # total_records = 0
    # if result is not None and isinstance(result, dict):
    #    total_records = result.get("TotalRecordCount", 0)

    use_cache = params.get("use_cache", "true") == "true"
    dir_items = None
    try:
        dir_items, detected_type, total_records = process_directory(url, progress, params, use_cache)
    except Exception as e:
        log.debug("There was an error processing the URL : {0}", e)
        data_manager = DataManager()
        cache_file_path = data_manager.get_cache_filename(url)
        if os.path.isfile(cache_file_path):
            log.debug("Clearing cache data file of failed process_directory : {0}", url)
            with FileLock(cache_file_path, timeout=5):
                xbmcvfs.delete(cache_file_path)
        raise

    if dir_items is None:
        return 0

    log.debug("total_records: {0}", total_records)

    # add paging items
    if page_limit > 0 and media_type.lower() in ["movies", "movie", "tvshows"]:
        if url_prev:
            list_item = xbmcgui.ListItem("Prev Page (" + str(start_index - page_limit + 1) + "-" + str(start_index) +
                                         " of " + str(total_records) + ")")
            u = sys.argv[0] + "?url=" + urllib.parse.quote(url_prev) + "&mode=GET_CONTENT&media_type=movies"
            log.debug("ADDING PREV ListItem: {0} - {1}", u, list_item)
            dir_items.insert(0, (u, list_item, True))

        if start_index + page_limit < total_records:
            upper_count = start_index + (page_limit * 2)
            if upper_count > total_records:
                upper_count = total_records
            list_item = xbmcgui.ListItem("Next Page (" + str(start_index + page_limit + 1) + "-" +
                                         str(upper_count) + " of " + str(total_records) + ")")
            u = sys.argv[0] + "?url=" + urllib.parse.quote(url_next) + "&mode=GET_CONTENT&media_type=movies"
            log.debug("ADDING NEXT ListItem: {0} - {1}", u, list_item)
            dir_items.append((u, list_item, True))

    # set the Kodi content type
    if content_type:
        xbmcplugin.setContent(pluginhandle, content_type)
    elif detected_type is not None:
        # if the media type is not set then try to use the detected type
        log.debug("Detected content type: {0}", detected_type)
        if detected_type == "Movie":
            view_type = "Movies"
            content_type = 'movies'
        if detected_type == "Episode":
            view_type = "Episodes"
            content_type = 'episodes'
        xbmcplugin.setContent(pluginhandle, content_type)

    # set the sort items
    if page_limit > 0 and media_type.lower() in ["movies", "movie", "tvshows"]:
        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_UNSORTED)
    else:
        set_sort(pluginhandle, view_type, default_sort)

    xbmcplugin.addDirectoryItems(pluginhandle, dir_items)
    xbmcplugin.endOfDirectory(pluginhandle, cacheToDisc=False)

    # set the view based on saved value
    view_key = "view-" + content_type
    view_id = settings.getSetting(view_key)
    if view_id:
        log.debug("Setting view for type:{0} to id:{1}", view_key, view_id)
        display_items_notification = {"view_id": view_id}
        send_event_notification("set_view", display_items_notification)
    else:
        log.debug("No view id for view type:{0}", view_key)

    # send display items event
    # display_items_notification = {"view_type": view_type}
    # log.debug("Sending display_items with data {0}", display_items_notification)
    # send_event_notification("display_items", display_items_notification)

    if progress is not None:
        progress.update(100, string_load(30125))
        progress.close()

    return len(dir_items)


def set_sort(pluginhandle, view_type, default_sort):
    log.debug("SETTING_SORT for media type: {0}", view_type)

    if default_sort == "none":
        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_UNSORTED)

    sorting_order_mapping = {
        "1": xbmcplugin.SORT_METHOD_UNSORTED,
        "2": xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE_IGNORE_THE,
        "3": xbmcplugin.SORT_METHOD_VIDEO_YEAR,
        "4": xbmcplugin.SORT_METHOD_DATEADDED,
        "5": xbmcplugin.SORT_METHOD_GENRE,
        "6": xbmcplugin.SORT_METHOD_LABEL,
        "7": xbmcplugin.SORT_METHOD_VIDEO_RATING
    }

    settings = xbmcaddon.Addon()
    preset_sort_order = settings.getSetting("sort-" + view_type)
    log.debug("SETTING_SORT preset_sort_order: {0}", preset_sort_order)
    if preset_sort_order in sorting_order_mapping:
        xbmcplugin.addSortMethod(pluginhandle, sorting_order_mapping[preset_sort_order])

    if view_type == "BoxSets":
        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_VIDEO_YEAR)
        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE_IGNORE_THE)
    elif view_type == "Episodes":
        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_EPISODE)
    elif view_type == "Music":
        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_TRACKNUM)
    else:
        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE_IGNORE_THE)
        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_VIDEO_YEAR)

    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_DATEADDED)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_GENRE)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_VIDEO_RATING)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)


@timer
def process_directory(url, progress, params, use_cache_data=False):
    log.debug("== ENTER: processDirectory ==")

    data_manager = DataManager()
    settings = xbmcaddon.Addon()
    download_utils = DownloadUtils()
    server = download_utils.get_server()

    name_format = params.get("name_format", None)
    name_format_type = None
    if name_format is not None:
        name_format = urllib.parse.unquote(name_format)
        tokens = name_format.split("|")
        if len(tokens) == 2:
            name_format_type = tokens[0]
            name_format = settings.getSetting(tokens[1])
        else:
            name_format_type = None
            name_format = None

    gui_options = {}
    gui_options["server"] = server
    gui_options["name_format"] = name_format
    gui_options["name_format_type"] = name_format_type

    use_cache = settings.getSetting("use_cache") == "true" and use_cache_data
    cache_file, item_list, total_records, cache_thread = data_manager.get_items(url, gui_options, use_cache)

    # flatten single season
    # if there is only one result and it is a season and you have flatten signle season turned on then
    # build a new url, set the content media type and call get content again
    flatten_single_season = settings.getSetting("flatten_single_season") == "true"
    if flatten_single_season and len(item_list) == 1 and item_list[0].item_type == "Season":
        season_id = item_list[0].id
        series_id = item_list[0].series_id
        season_url = ('{server}/emby/Shows/' + series_id +
                      '/Episodes'
                      '?userId={userid}' +
                      '&seasonId=' + season_id +
                      '&IsVirtualUnAired=false' +
                      '&IsMissing=false' +
                      '&Fields=SpecialEpisodeNumbers,{field_filters}' +
                      '&format=json')
        if progress is not None:
            progress.close()
        params["media_type"] = "Episodes"
        get_content(season_url, params)
        return None, None, None

    hide_unwatched_details = settings.getSetting('hide_unwatched_details') == 'true'

    display_options = {}
    display_options["addCounts"] = settings.getSetting("addCounts") == 'true'
    display_options["addResumePercent"] = settings.getSetting("addResumePercent") == 'true'
    display_options["addSubtitleAvailable"] = settings.getSetting("addSubtitleAvailable") == 'true'
    display_options["addUserRatings"] = settings.getSetting("add_user_ratings") == 'true'

    show_empty_folders = settings.getSetting("show_empty_folders") == 'true'

    item_count = len(item_list)
    current_item = 1
    first_season_item = None
    total_unwatched = 0
    total_episodes = 0
    total_watched = 0

    detected_type = None
    dir_items = []

    for item_details in item_list:

        item_details.total_items = item_count

        if progress is not None:
            percent_done = (float(current_item) / float(item_count)) * 100
            progress.update(int(percent_done), string_load(30126) + str(current_item))
            current_item = current_item + 1

        if detected_type is not None:
            if item_details.item_type != detected_type:
                detected_type = "mixed"
        else:
            detected_type = item_details.item_type

        if item_details.item_type == "Season" and first_season_item is None:
            log.debug("Setting First Season to : {0}", item_details.__dict__)
            first_season_item = item_details

        total_unwatched += item_details.unwatched_episodes
        total_episodes += item_details.total_episodes
        total_watched += item_details.watched_episodes

        # if set, for unwatched episodes dont show some of the info
        if hide_unwatched_details and item_details.item_type == "Episode" and item_details.play_count == 0:
            item_details.plot = "[Spoiler Alert]"
            item_details.art["poster"] = item_details.art["tvshow.poster"]
            item_details.art["thumb"] = item_details.art["tvshow.poster"]

        if item_details.is_folder is True:
            if item_details.item_type == "Series":
                u = ('{server}/emby/Shows/' + item_details.id +
                     '/Seasons'
                     '?userId={userid}' +
                     '&Fields={field_filters}' +
                     '&format=json')

            elif item_details.item_type == "Season":
                u = ('{server}/emby/Shows/' + item_details.series_id +
                     '/Episodes'
                     '?userId={userid}' +
                     '&seasonId=' + item_details.id +
                     '&IsVirtualUnAired=false' +
                     '&IsMissing=false' +
                     '&Fields=SpecialEpisodeNumbers,{field_filters}' +
                     '&format=json')

            else:
                u = ('{server}/emby/Users/{userid}/items' +
                     '?ParentId=' + item_details.id +
                     '&IsVirtualUnAired=false' +
                     '&IsMissing=false' +
                     '&Fields={field_filters}' +
                     '&format=json')

            default_sort = item_details.item_type == "Playlist"

            if show_empty_folders or item_details.recursive_item_count != 0:
                gui_item = add_gui_item(u, item_details, display_options, default_sort=default_sort)
                if gui_item:
                    dir_items.append(gui_item)
            else:
                log.debug("Dropping empty folder item : {0}", item_details.__dict__)

        elif item_details.item_type == "MusicArtist":
            u = ('{server}/emby/Users/{userid}/items' +
                 '?AlbumArtistIds=' + item_details.id +
                 '&IncludeItemTypes=MusicAlbum' +
                 '&CollapseBoxSetItems=false' +
                 '&Recursive=true' +
                 '&format=json')
            gui_item = add_gui_item(u, item_details, display_options)
            if gui_item:
                dir_items.append(gui_item)

        else:
            u = item_details.id
            gui_item = add_gui_item(u, item_details, display_options, folder=False)
            if gui_item:
                dir_items.append(gui_item)

    # add the all episodes item
    show_all_episodes = settings.getSetting('show_all_episodes') == 'true'
    if (show_all_episodes
            and first_season_item is not None
            and len(dir_items) > 1
            and first_season_item.series_id is not None):
        series_url = ('{server}/emby/Shows/' + first_season_item.series_id +
                      '/Episodes'
                      '?userId={userid}' +
                      # '&seasonId=' + season_id +
                      '&IsVirtualUnAired=false' +
                      '&IsMissing=false' +
                      '&Fields=SpecialEpisodeNumbers,{field_filters}' +
                      '&format=json')
        played = 0
        overlay = "7"
        if total_unwatched == 0:
            played = 1
            overlay = "6"

        item_details = ItemDetails()

        item_details.id = first_season_item.id
        item_details.name = string_load(30290)
        item_details.art = first_season_item.art
        item_details.play_count = played
        item_details.overlay = overlay
        item_details.name_format = "Episode|episode_name_format"
        item_details.series_name = first_season_item.series_name
        item_details.item_type = "Season"
        item_details.unwatched_episodes = total_unwatched
        item_details.total_episodes = total_episodes
        item_details.watched_episodes = total_watched
        item_details.mode = "GET_CONTENT"

        gui_item = add_gui_item(series_url, item_details, display_options, folder=True)
        if gui_item:
            dir_items.append(gui_item)

    if cache_thread is not None:
        cache_thread.start()

    return dir_items, detected_type, total_records
