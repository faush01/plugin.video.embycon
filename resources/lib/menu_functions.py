# coding=utf-8
# Gnu General Public License - see LICENSE.TXT

from typing import List, Dict, Union
import os
import sys
import urllib.request
import urllib.parse
import urllib.error
import base64

import xbmcplugin
import xbmcaddon
import xbmcvfs

from .downloadutils import DownloadUtils
from .kodi_utils import add_menu_directory_item, HomeWindow
from .simple_logging import SimpleLogging
from .translation import string_load
from .datamanager import DataManager
from .utils import get_art, get_emby_url
from .custom_nodes import CustomNode, load_custom_nodes

log = SimpleLogging(__name__)
downloadUtils = DownloadUtils()


__addon__ = xbmcaddon.Addon()


def show_movie_tags(menu_params: Dict[str, str]) -> None:
    log.debug("show_movie_tags: {0}", menu_params)
    parent_id: str = menu_params.get("parent_id", "")

    url_params: Dict[str, str] = {
        "UserId": "{userid}",
        "SortBy": "SortName",
        "SortOrder": "Ascending",
        "CollapseBoxSetItems": str(False),
        "GroupItemsIntoCollections": str(False),
        "Recursive": str(True),
        "IsMissing": str(False),
        "EnableTotalRecordCount": str(False),
        "EnableUserData": str(False),
        "IncludeItemTypes": "Movie"
    }

    if parent_id:
        url_params["ParentId"] = parent_id

    url: str = get_emby_url("{server}/emby/Tags", url_params)
    data_manager: DataManager = DataManager()
    result = data_manager.get_content(url)

    if not result:
        return

    tags = result.get("Items")

    log.debug("Tags : {0}", result)

    for tag in tags:
        name: str = tag["Name"]
        tag_id: str = tag["Id"]

        movie_tag_url_params: Dict[str, str] = {
            "IncludeItemTypes": "Movie",
            "CollapseBoxSetItems": str(False),
            "GroupItemsIntoCollections": str(False),
            "Recursive": str(True),
            "IsMissing": str(False),
            "ImageTypeLimit": str(1),
            "SortBy": "Name",
            "SortOrder": "Ascending",
            "Fields": "{field_filters}",
            "TagIds": tag_id
        }

        if parent_id:
            movie_tag_url_params["ParentId"] = parent_id

        item_url = get_emby_url("{server}/emby/Users/{userid}/Items", movie_tag_url_params)

        art = {
            "thumb": "http://localhost:24276/" + base64.b64encode(item_url.encode("utf-8")).decode("utf-8")
        }

        content_url = urllib.parse.quote(item_url)
        url = sys.argv[0] + ("?url=" +
                             content_url +
                             "&mode=GET_CONTENT" +
                             "&media_type=movies")
        log.debug("addMenuDirectoryItem: {0} - {1}", name, url)
        add_menu_directory_item(name, url, art=art)

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def show_movie_years(menu_params: Dict[str, str]) -> None:
    log.debug("show_movie_years: {0}", menu_params)
    parent_id: str = menu_params.get("parent_id", "")
    group_into_decades: bool = menu_params.get("group", "false") == "true"

    url_params: Dict[str, str] = {
        "UserId": "{userid}",
        "SortBy": "SortName",
        "SortOrder": "Ascending",
        "CollapseBoxSetItems": str(False),
        "GroupItemsIntoCollections": str(False),
        "Recursive": str(True),
        "IsMissing": str(False),
        "EnableTotalRecordCount": str(False),
        "EnableUserData": str(False),
        "IncludeItemTypes": "Movie"
    }

    if parent_id:
        url_params["ParentId"] = parent_id

    url = get_emby_url("{server}/emby/Years", url_params)

    data_manager = DataManager()
    result = data_manager.get_content(url)

    if not result:
        return

    years_list: List[Dict] = result.get("Items")
    result_names: Dict[str, List[str]] = {}
    for year in years_list:
        year_name: str = year.get("Name", "-1")
        year_int: int = int(year_name)
        if year_int > -1 and group_into_decades:
            decade_start: int = year_int - year_int % 10
            decade_end: int = (year_int - year_int % 10) + 9
            decade_name: str = str(decade_start) + "-" + str(decade_end)
            if decade_name not in result_names:
                result_names[decade_name] = [str(i) for i in range(decade_start, decade_end + 1)]
        elif year_int > -1:
            result_names[year_name] = [year_name]

    keys: List[str] = list(result_names.keys())
    keys.sort()

    for year_name in keys:
        years_list_str: str = ",".join(result_names[year_name])

        year_params: Dict[str, str] = {
            "IncludeItemTypes": "Movie",
            "CollapseBoxSetItems": str(False),
            "GroupItemsIntoCollections": str(False),
            "Recursive": str(True),
            "IsMissing": str(False),
            "ImageTypeLimit": str(1),
            "SortBy": "Name",
            "SortOrder": "Ascending",
            "Fields": "{field_filters}",
            "Years": years_list_str
        }

        if parent_id:
            year_params["ParentId"] = parent_id

        item_url = get_emby_url("{server}/emby/Users/{userid}/Items", year_params)

        art: Dict[str, str] = {
            "thumb": "http://localhost:24276/" + base64.b64encode(item_url.encode("utf-8")).decode("utf-8")
        }

        content_url = urllib.parse.quote(item_url)
        url = sys.argv[0] + ("?url=" +
                             content_url +
                             "&mode=GET_CONTENT" +
                             "&media_type=movies")
        log.debug("addMenuDirectoryItem: {0} - {1}", year_name, url)
        add_menu_directory_item(year_name, url, art=art)

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def show_movie_pages(menu_params):
    log.debug("showMoviePages: {0}", menu_params)

    parent_id = menu_params.get("parent_id")
    settings = xbmcaddon.Addon()

    params: Dict[str, str] = {
        "IncludeItemTypes": "Movie",
        "CollapseBoxSetItems": str(False),
        "GroupItemsIntoCollections": str(False),
        "Recursive": str(True),
        "IsMissing": str(False),
        "ImageTypeLimit": str(0)
    }

    if parent_id:
        params["ParentId"] = parent_id

    url = get_emby_url("{server}/emby/Users/{userid}/Items", params)

    data_manager = DataManager()
    result = data_manager.get_content(url)

    if result is None:
        return

    total_results: int = result.get("TotalRecordCount", 0)
    log.debug("showMoviePages TotalRecordCount {0}", total_results)

    if result == 0:
        return

    page_limit: int = int(settings.getSetting('itemsPerPage'))
    if page_limit == 0:
        page_limit = 20

    start_index: int = 0
    collections: List[Dict[str, object]] = []

    while start_index < total_results:

        movie_url_params: Dict[str, str] = {
            "IncludeItemTypes": "Movie",
            "CollapseBoxSetItems": str(False),
            "GroupItemsIntoCollections": str(False),
            "Recursive": str(True),
            "IsMissing": str(False),
            "ImageTypeLimit": str(1),
            "SortBy": "Name",
            "SortOrder": "Ascending",
            "Fields": "{field_filters}",
            "StartIndex": str(start_index),
            "Limit": str(page_limit)
        }

        if parent_id:
            movie_url_params["ParentId"] = parent_id

        item_url = get_emby_url("{server}/emby/Users/{userid}/Items", movie_url_params)

        page_upper = start_index + page_limit
        if page_upper > total_results:
            page_upper = total_results

        art_links: Dict[str, str] = {
            "thumb": "http://localhost:24276/" + base64.b64encode(item_url.encode("utf-8")).decode("utf-8")
        }
        item_data: Dict[str, object] = {
            'title': "Page (" + str(start_index + 1) + " - " + str(page_upper) + ")",
            'path': item_url,
            'media_type': 'movies',
            "art": art_links
        }

        collections.append(item_data)
        start_index = start_index + page_limit

    for collection in collections:
        content_url = urllib.parse.quote(str(collection.get("path", "")))
        url = sys.argv[0] + ("?url=" + content_url +
                             "&mode=GET_CONTENT" +
                             "&media_type=" + str(collection.get("media_type", "")))
        log.debug("addMenuDirectoryItem: {0} - {1} - {2}", collection.get('title'), url, collection.get("art"))
        add_menu_directory_item(collection.get('title', string_load(30250)), url, art=collection.get("art"))

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def show_genre_list(menu_params):
    log.debug("showGenreList: {0}", menu_params)

    server: str = downloadUtils.get_server()
    if server is None:
        return

    parent_id = menu_params.get("parent_id")
    item_type = menu_params.get("item_type")

    kodi_type: str = "Movies"
    emby_type: str = "Movie"
    if item_type is not None and item_type == "tvshow":
        emby_type = "Series"
        kodi_type = "tvshows"

    params: Dict[str, str] = {
        "IncludeItemTypes": emby_type,
        "UserId": "{userid}",
        "Recursive": str(True),
        "SortBy": "Name",
        "SortOrder": "Ascending",
        "ImageTypeLimit": str(1)
    }

    if parent_id is not None:
        params["ParentId"] = parent_id

    genres_url: str = get_emby_url("{server}/emby/Genres", params)

    data_manager = DataManager()
    result = data_manager.get_content(genres_url)

    if result is not None:
        result = result.get("Items")
    else:
        result = []

    collections = []
    xbmcplugin.setContent(int(sys.argv[1]), 'genres')

    for genre in result:
        item_data: Dict[str, Union[str, Dict[str, str]]] = {
            'title': genre.get("Name"),
            'media_type': kodi_type
        }

        genre_params: Dict[str, str] = {
            "Recursive": str(True),
            "CollapseBoxSetItems": str(False),
            "GroupItemsIntoCollections": str(False),
            "GenreIds": genre.get("Id"),
            "IncludeItemTypes": emby_type,
            "ImageTypeLimit": str(1),
            "Fields": "{field_filters}"
        }

        if genre_params is not None:
            params["ParentId"] = parent_id

        item_url: str = get_emby_url("{server}/emby/Users/{userid}/Items", genre_params)

        art = {
            "thumb": "http://localhost:24276/" + base64.b64encode(item_url.encode("utf-8")).decode("utf-8")
        }
        item_data['art'] = art

        item_data['path'] = item_url
        collections.append(item_data)

    for collection in collections:
        url_string: str = "{0}?url={1}&mode=GET_CONTENT&media_type={2}"
        col_url: str = url_string.format(sys.argv[0],
                                     urllib.parse.quote(str(collection['path']),
                                     str(collection["media_type"])))
        log.debug("addMenuDirectoryItem: {0} - {1} - {2}", collection.get('title'), col_url, collection.get("art"))
        add_menu_directory_item(collection.get('title', string_load(30250)), col_url, art=collection.get("art"))

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def show_movie_alpha_list(menu_params):
    log.debug("== ENTER: showMovieAlphaList() ==")

    xbmcplugin.setContent(int(sys.argv[1]), 'movies')

    server = downloadUtils.get_server()
    if server is None:
        return

    parent_id = menu_params.get("parent_id")

    url_params: Dict[str, str] = {
        "IncludeItemTypes": "Movie",
        "Recursive": str(True),
        "CollapseBoxSetItems": str(False),
        "GroupItemsIntoCollections": str(False),
        "UserId": "{userid}",
        "SortBy": "Name",
        "SortOrder": "Ascending"
    }

    if parent_id is not None:
        url_params["ParentId"] = parent_id

    prefix_url = get_emby_url("{server}/emby/Items/Prefixes", url_params)

    data_manager = DataManager()
    result = data_manager.get_content(prefix_url)

    if not result:
        return

    alpha_list = []
    for prefix in result:
        alpha_list.append(prefix.get("Name"))

    collections = []
    for alphaName in alpha_list:
        item_data: Dict[str, Union[str, Dict[str, str]]] = {
            'title': alphaName,
            'media_type': "Movies"
        }

        movie_alpha_params: Dict[str, str] = {
            "Fields": "{field_filters}",
            "CollapseBoxSetItems": str(False),
            "GroupItemsIntoCollections": str(False),
            "Recursive": str(True),
            "IncludeItemTypes": "Movie",
            "SortBy": "Name",
            "SortOrder": "Ascending",
            "ImageTypeLimit": str(1)
        }

        if parent_id is not None:
            movie_alpha_params["ParentId"] = parent_id

        if alphaName == "#":
            movie_alpha_params["NameLessThan"] = "A"
        else:
            movie_alpha_params["NameStartsWith"] = alphaName

        url = get_emby_url("{server}/emby/Users/{userid}/Items", movie_alpha_params)
        item_data['path'] = url

        art: Dict[str, str] = {
            "thumb": "http://localhost:24276/" + base64.b64encode(url.encode("utf-8")).decode("utf-8")
        }
        item_data['art'] = art

        collections.append(item_data)

    for collection in collections:
        url = (sys.argv[0] + "?url=" + urllib.parse.quote(str(collection['path'])) +
               "&mode=GET_CONTENT&media_type=" + str(collection["media_type"]))
        log.debug("addMenuDirectoryItem: {0} ({1})", collection.get('title'), url)
        add_menu_directory_item(collection.get('title', string_load(30250)), url, art=collection.get("art"))

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def show_tvshow_alpha_list(menu_params: Dict[str, str]):
    log.debug("== ENTER: showTvShowAlphaList() ==")

    server = downloadUtils.get_server()
    if server is None:
        return

    parent_id: str = menu_params.get("parent_id", "")

    url_params: Dict[str, str] = {
        "IncludeItemTypes": "Series",
        "Recursive": str(True),
        "UserId": "{userid}",
        "SortBy": "Name",
        "SortOrder": "Ascending"
    }
    
    if parent_id:
        menu_params["ParentId"] = parent_id
    prefix_url = get_emby_url("{server}/emby/Items/Prefixes", url_params)

    data_manager = DataManager()
    result = data_manager.get_content(prefix_url)

    if not result:
        return

    alpha_list = []
    for prefix in result:
        alpha_list.append(prefix.get("Name"))

    collections = []
    for alpha_name in alpha_list:
        item_data: Dict[str, Union[str, Dict[str, str]]] = {
            'title': alpha_name,
            'media_type': "tvshows"
        }

        params: Dict[str, str] = {
            "Fields": "{field_filters}",
            "ImageTypeLimit": str(1),
            "IncludeItemTypes": "Series",
            "SortBy": "Name",
            "SortOrder": "Ascending",
            "Recursive": str(True),
            "IsMissing": str(False)
        }

        if parent_id is not None:
            params["ParentId"] = parent_id

        if alpha_name == "#":
            params["NameLessThan"] = "A"
        else:
            params["NameStartsWith"] = alpha_name

        path = get_emby_url("{server}/emby/Users/{userid}/Items", params)

        item_data['path'] = path

        art = {
            "thumb": "http://localhost:24276/" + base64.b64encode(path.encode("utf-8")).decode("utf-8")
        }
        item_data['art'] = art

        collections.append(item_data)

    for collection in collections:
        url_pattern: str = "{0}?url={1}&mode=GET_CONTENT&media_type={2}"
        target_path: str = str(collection['path'])
        url: str = url_pattern.format(sys.argv[0], urllib.parse.quote(target_path), collection["media_type"])
        log.debug("addMenuDirectoryItem: {0} ({1})", collection.get('title'), url)
        add_menu_directory_item(collection.get('title', string_load(30250)), url, art=collection.get("art"))

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def show_tvshow_pages(menu_params):
    log.debug("showTvShowPages: {0}", menu_params)

    parent_id: str = menu_params.get("parent_id")
    settings = xbmcaddon.Addon()

    show_params: Dict[str, str] = {
        "IncludeItemTypes": "Series",
        "IsMissing": str(False),
        "Recursive": str(True),
        "ImageTypeLimit": str(0)
    }

    if parent_id:
        show_params["ParentId"] = parent_id

    url = get_emby_url("{server}/emby/Users/{userid}/Items", show_params)

    data_manager = DataManager()
    result = data_manager.get_content(url)

    if result is None:
        return

    total_results = result.get("TotalRecordCount", 0)
    log.debug("showMoviePages TotalRecordCount {0}", total_results)

    if result == 0:
        return

    page_limit = int(settings.getSetting('itemsPerPage'))
    if page_limit == 0:
        page_limit = 20

    start_index: int = 0
    collections: List[Dict[str, Union[str, Dict[str, str]]]] = []

    while start_index < total_results:

        page_params: Dict[str, str] = {
            "IncludeItemTypes": "Series",
            "IsMissing": str(False),
            "Recursive": str(True),
            "ImageTypeLimit": str(1),
            "SortBy": "Name",
            "SortOrder": "Ascending",
            "Fields": "{field_filters}",
            "StartIndex": str(start_index),
            "Limit": str(page_limit)
        }

        if parent_id:
            page_params["ParentId"] = parent_id

        item_url = get_emby_url("{server}/emby/Users/{userid}/Items", page_params)

        page_upper = start_index + page_limit
        if page_upper > total_results:
            page_upper = total_results

        item_data: Dict[str, Union[str, Dict[str, str]]] = {
            'title': "Page (" + str(start_index + 1) + " - " + str(page_upper) + ")",
            'path': item_url,
            'media_type': 'tvshows',
            "art": {
                "thumb": "http://localhost:24276/" + base64.b64encode(item_url.encode("utf-8")).decode("utf-8")
            }
        }

        collections.append(item_data)
        start_index = start_index + page_limit

    for collection in collections:
        content_url: str = urllib.parse.quote(str(collection['path']))
        url_pattern: str = "{0}?url={1}&mode=GET_CONTENT&media_type={2}"
        target_url: str = url_pattern.format(sys.argv[0], content_url, collection["media_type"])
        log.debug("addMenuDirectoryItem: {0} - {1} - {2}", collection.get('title'), target_url, collection.get("art"))
        add_menu_directory_item(collection.get('title', string_load(30250)), target_url, art=collection.get("art"))

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def display_main_menu():
    handle = int(sys.argv[1])
    xbmcplugin.setContent(handle, 'files')

    add_menu_directory_item(string_load(30406),
                            "plugin://plugin.video.embycon/?mode=SHOW_ADDON_MENU&type=library")
    add_menu_directory_item(string_load(30407),
                            "plugin://plugin.video.embycon/?mode=SHOW_ADDON_MENU&type=show_global_types")
    add_menu_directory_item(string_load(30408),
                            "plugin://plugin.video.embycon/?mode=SHOW_ADDON_MENU&type=show_custom_widgets")
    add_menu_directory_item(string_load(30409),
                            "plugin://plugin.video.embycon/?mode=SHOW_ADDON_MENU&type=addon_items")
    add_menu_directory_item("Custom Nodes",
                            "plugin://plugin.video.embycon/?mode=SHOW_ADDON_MENU&type=custom_nodes")

    xbmcplugin.endOfDirectory(handle)


def display_menu(params):
    menu_type = params.get("type")
    if menu_type == "library":
        display_library_views(params)
    elif menu_type == "library_item":
        display_library_view(params)
    elif menu_type == "show_global_types":
        show_global_types(params)
    elif menu_type == "global_list_movies":
        display_movies_type(params, None)
    elif menu_type == "global_list_tvshows":
        display_tvshow_type(params, None)
    elif menu_type == "show_custom_widgets":
        show_widgets()
    elif menu_type == "addon_items":
        display_addon_menu(params)
    elif menu_type == "show_movie_years":
        show_movie_years(params)
    elif menu_type == "show_movie_tags":
        show_movie_tags(params)
    elif menu_type == "custom_nodes":
        show_custom_nodes(params)
    elif menu_type == "create_new_node":
        create_new_node(params)


def create_new_node(params):
    log.debug("Create New Custom Node")

    addon = xbmcaddon.Addon()
    addon_path = addon.getAddonInfo('path')
    skin_path = xbmcvfs.translatePath(os.path.join(addon_path))

    custom_node = CustomNode("CustomNode.xml", skin_path, "default", "720p")
    #custom_node.setActionItems(action_items)
    custom_node.doModal()


def get_node_url(node_info):
    log.debug("get_node_url : {0}", node_info)

    base_params: Dict[str, str] = {
        "Fields": "{field_filters}",
        "ImageTypeLimit": str(1),
        "IsMissing": str(False)
    }

    if "item_parent" in node_info and node_info["item_parent"]:
        base_params["ParentId"] = node_info["item_parent"]
    if "recursive" in node_info and node_info["recursive"]:
        base_params["Recursive"] = node_info["recursive"]
    if "item_type" in node_info and node_info["item_type"]:
        base_params["IncludeItemTypes"] = node_info["item_type"]
    if "item_limit" in node_info and node_info["item_limit"]:
        base_params["Limit"] = node_info["item_limit"]
    if "group" in node_info and node_info["group"]:
        base_params["GroupItemsIntoCollections"] = node_info["group"]
        base_params["CollapseBoxSetItems"] = node_info["group"]
    if "watched" in node_info and node_info["watched"]:
        base_params["IsPlayed"] = node_info["watched"]
    if "inprogress" in node_info and node_info["inprogress"] == "True":
        base_params["Filters"] = "IsResumable"
    if "sortby" in node_info and node_info["sortby"]:
        base_params["SortBy"] = node_info["sortby"]
    if "sortorder" in node_info and node_info["sortorder"]:
        base_params["SortOrder"] = node_info["sortorder"]

    path = get_emby_url("{server}/emby/Users/{userid}/Items", base_params)
    return path


def show_custom_nodes(params):
    log.debug("Show Custom Nodes")
    add_menu_directory_item("[Edit Nodes]",
                            "plugin://plugin.video.embycon/?mode=SHOW_ADDON_MENU&type=create_new_node")

    # show custom nodes
    custom_nodes = load_custom_nodes()

    node_names = []
    for node_name in custom_nodes:
        node_names.append(node_name)
    node_names.sort()

    for node_name in node_names:
        encoded_name =  urllib.parse.quote(node_name)
        add_menu_directory_item(node_name,
                                "plugin://plugin.video.embycon/?mode=SHOW_NODE_CONTENT&node_name=" + encoded_name)

    handle = int(sys.argv[1])
    xbmcplugin.endOfDirectory(handle)


def show_global_types(params):
    handle = int(sys.argv[1])

    add_menu_directory_item(string_load(30256),
                            "plugin://plugin.video.embycon/?mode=SHOW_ADDON_MENU&type=global_list_movies")
    add_menu_directory_item(string_load(30261),
                            "plugin://plugin.video.embycon/?mode=SHOW_ADDON_MENU&type=global_list_tvshows")

    xbmcplugin.endOfDirectory(handle)


def display_homevideos_type(menu_params, view):
    handle = int(sys.argv[1])
    view_name = view.get("Name")
    settings = xbmcaddon.Addon()
    show_x_filtered_items = settings.getSetting("show_x_filtered_items")
    hide_watched = settings.getSetting("hide_watched") == "true"

    # All Home Movies
    base_params: Dict[str, str] = {
        "ParentId": view.get("Id"),
        "Recursive": str(False),
        "IsMissing": str(False),
        "Fields": "{field_filters}",
        "ImageTypeLimit": str(1)
    }

    path = get_emby_url("{server}/emby/Users/{userid}/Items", base_params)
    url = sys.argv[0] + "?url=" + urllib.parse.quote(path) + "&mode=GET_CONTENT&media_type=homevideos"
    add_menu_directory_item(view_name + string_load(30405), url)

    # In progress home movies
    params: Dict[str, str] = {}
    params.update(base_params)
    params["Filters"] = "IsResumable"
    params["Recursive"] = str(True)
    params["Limit"] = "{ItemLimit}"
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.parse.quote(path) + "&mode=GET_CONTENT&media_type=homevideos"
    add_menu_directory_item(view_name + string_load(30267) + " (" + show_x_filtered_items + ")", url)

    # Recently added
    params = {}
    params.update(base_params)
    params["Recursive"] = str(True)
    params["SortBy"] = "DateCreated"
    params["SortOrder"] = "Descending"
    params["Filters"] = "IsNotFolder"
    if hide_watched:
        params["IsPlayed"] = str(False)
    params["Limit"] = "{ItemLimit}"
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.parse.quote(path) + "&mode=GET_CONTENT&media_type=homevideos"
    add_menu_directory_item(view_name + string_load(30268) + " (" + show_x_filtered_items + ")", url)

    xbmcplugin.endOfDirectory(handle)


def display_addon_menu(params):

    add_menu_directory_item(string_load(30246), "plugin://plugin.video.embycon/?mode=SEARCH")
    add_menu_directory_item(string_load(30017), "plugin://plugin.video.embycon/?mode=SHOW_SERVER_SESSIONS")
    add_menu_directory_item(string_load(30012), "plugin://plugin.video.embycon/?mode=CHANGE_USER")
    add_menu_directory_item(string_load(30011), "plugin://plugin.video.embycon/?mode=DETECT_SERVER_USER")
    add_menu_directory_item(string_load(30435), "plugin://plugin.video.embycon/?mode=DETECT_CONNECTION_SPEED")
    add_menu_directory_item(string_load(30254), "plugin://plugin.video.embycon/?mode=SHOW_SETTINGS")
    add_menu_directory_item(string_load(30395), "plugin://plugin.video.embycon/?mode=CLEAR_CACHE")
    add_menu_directory_item(string_load(30293), "plugin://plugin.video.embycon/?mode=CACHE_ARTWORK")
    add_menu_directory_item("List Performance Profiles", "plugin://plugin.video.embycon/?mode=LIST_AVAILABLE_PROFILES")
    # add_menu_directory_item("Clone default skin", "plugin://plugin.video.embycon/?mode=CLONE_SKIN")

    handle = int(sys.argv[1])
    xbmcplugin.endOfDirectory(handle)


def display_tvshow_type(menu_params, view):
    handle = int(sys.argv[1])

    view_name = string_load(30261)
    if view is not None:
        view_name = view.get("Name")

    settings = xbmcaddon.Addon()
    show_x_filtered_items = settings.getSetting("show_x_filtered_items")

    # All TV Shows
    base_params: Dict[str, str] = {}
    if view is not None:
        base_params["ParentId"] = view.get("Id")
    base_params["Fields"] = "{field_filters}"
    base_params["ImageTypeLimit"] = str(1)
    base_params["IsMissing"] = str(False)
    base_params["IncludeItemTypes"] = "Series"
    base_params["Recursive"] = str(True)
    path = get_emby_url("{server}/emby/Users/{userid}/Items", base_params)
    url = sys.argv[0] + "?url=" + urllib.parse.quote(path) + "&mode=GET_CONTENT&media_type=tvshows"
    add_menu_directory_item(view_name + string_load(30405), url)

    # Favorite TV Shows
    params: Dict[str, str] = {}
    params.update(base_params)
    params["Filters"] = "IsFavorite"
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.parse.quote(path) + "&mode=GET_CONTENT&media_type=tvshows"
    add_menu_directory_item(view_name + string_load(30414), url)

    # Tv Shows with unplayed
    params = {}
    params.update(base_params)
    params["IsPlayed"] = str(False)
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.parse.quote(path) + "&mode=GET_CONTENT&media_type=tvshows"
    add_menu_directory_item(view_name + string_load(30285), url)

    # In progress episodes
    params = {}
    params.update(base_params)
    params["Limit"] = "{ItemLimit}"
    params["SortBy"] = "DatePlayed"
    params["SortOrder"] = "Descending"
    params["Filters"] = "IsResumable"
    params["IncludeItemTypes"] = "Episode"
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.parse.quote(path) + "&mode=GET_CONTENT&media_type=Episodes&sort=none"
    url += "&name_format=" + urllib.parse.quote('Episode|episode_name_format')
    add_menu_directory_item(view_name + string_load(30267) + " (" + show_x_filtered_items + ")", url)

    # Latest Episodes
    params = {}
    params.update(base_params)
    params["Limit"] = "{ItemLimit}"
    params["SortBy"] = "DateCreated"
    params["SortOrder"] = "Descending"
    params["IncludeItemTypes"] = "Episode"
    path = get_emby_url("{server}/emby/Users/{userid}/Items/Latest", params)
    url = sys.argv[0] + "?url=" + urllib.parse.quote(path) + "&mode=GET_CONTENT&media_type=tvshows&sort=none"
    add_menu_directory_item(view_name + string_load(30288) + " (" + show_x_filtered_items + ")", url)

    # Recently Added
    params = {}
    params.update(base_params)
    params["Limit"] = "{ItemLimit}"
    params["SortBy"] = "DateCreated"
    params["SortOrder"] = "Descending"
    params["Filters"] = "IsNotFolder"
    params["IncludeItemTypes"] = "Episode"
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.parse.quote(path) + "&mode=GET_CONTENT&media_type=Episodes&sort=none"
    url += "&name_format=" + urllib.parse.quote('Episode|episode_name_format')
    add_menu_directory_item(view_name + string_load(30268) + " (" + show_x_filtered_items + ")", url)

    # Next Up Episodes
    params = {}
    params.update(base_params)
    params["Limit"] = "{ItemLimit}"
    params["Userid"] = "{userid}"
    params["SortBy"] = "DateCreated"
    params["SortOrder"] = "Descending"
    params["Filters"] = "IsNotFolder"
    params["IncludeItemTypes"] = "Episode"
    params["Legacynextup"] = "true"
    path = get_emby_url("{server}/emby/Shows/NextUp", params)
    url = sys.argv[0] + "?url=" + urllib.parse.quote(path) + "&mode=GET_CONTENT&media_type=Episodes&sort=none"
    url += "&name_format=" + urllib.parse.quote('Episode|episode_name_format')
    add_menu_directory_item(view_name + string_load(30278) + " (" + show_x_filtered_items + ")", url)

    # TV Show Genres
    path = "plugin://plugin.video.embycon/?mode=GENRES&item_type=tvshow"
    if view is not None:
        path += "&parent_id=" + view.get("Id")
    add_menu_directory_item(view_name + string_load(30325), path)

    # TV Show Alpha picker
    path = "plugin://plugin.video.embycon/?mode=TVSHOW_ALPHA"
    if view is not None:
        path += "&parent_id=" + view.get("Id")
    add_menu_directory_item(view_name + string_load(30404), path)

    # Tv Show Pages
    path = "plugin://plugin.video.embycon/?mode=TVSHOW_PAGES"
    if view is not None:
        path += "&parent_id=" + view.get("Id")
    add_menu_directory_item(view_name + string_load(30397), path)

    xbmcplugin.endOfDirectory(handle)


def display_music_type(menu_params, view):
    handle = int(sys.argv[1])
    view_name = view.get("Name")

    settings = xbmcaddon.Addon()
    show_x_filtered_items = settings.getSetting("show_x_filtered_items")

    # all albums
    params: Dict[str, str] = {}
    params["ParentId"] = view.get("Id")
    params["Recursive"] = str(True)
    params["ImageTypeLimit"] = str(1)
    params["IncludeItemTypes"] = "MusicAlbum"
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.parse.quote(path) + "&mode=GET_CONTENT&media_type=MusicAlbums"
    add_menu_directory_item(view_name + string_load(30320), url)

    # recently added
    params = {}
    params["ParentId"] = view.get("Id")
    params["ImageTypeLimit"] = str(1)
    params["IncludeItemTypes"] = "Audio"
    params["Limit"] = "{ItemLimit}"
    path = get_emby_url("{server}/emby/Users/{userid}/Items/Latest", params)
    url = sys.argv[0] + "?url=" + urllib.parse.quote(path) + "&mode=GET_CONTENT&media_type=MusicAlbums"
    add_menu_directory_item(view_name + string_load(30268) + " (" + show_x_filtered_items + ")", url)

    # recently played
    params = {}
    params["ParentId"] = view.get("Id")
    params["Recursive"] = str(True)
    params["ImageTypeLimit"] = str(1)
    params["IncludeItemTypes"] = "Audio"
    params["Limit"] = "{ItemLimit}"
    params["IsPlayed"] = str(True)
    params["SortBy"] = "DatePlayed"
    params["SortOrder"] = "Descending"
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.parse.quote(path) + "&mode=GET_CONTENT&media_type=MusicAlbum"
    add_menu_directory_item(view_name + string_load(30349) + " (" + show_x_filtered_items + ")", url)

    # most played
    params = {}
    params["ParentId"] = view.get("Id")
    params["Recursive"] = str(True)
    params["ImageTypeLimit"] = str(1)
    params["IncludeItemTypes"] = "Audio"
    params["Limit"] = "{ItemLimit}"
    params["IsPlayed"] = str(True)
    params["SortBy"] = "PlayCount"
    params["SortOrder"] = "Descending"
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.parse.quote(path) + "&mode=GET_CONTENT&media_type=MusicAlbum"
    add_menu_directory_item(view_name + string_load(30353) + " (" + show_x_filtered_items + ")", url)

    # artists
    params = {}
    params["ParentId"] = view.get("Id")
    params["Recursive"] = str(True)
    params["ImageTypeLimit"] = str(1)
    path = get_emby_url("{server}/emby/Artists/AlbumArtists", params)
    url = sys.argv[0] + "?url=" + urllib.parse.quote(path) + "&mode=GET_CONTENT&media_type=MusicArtists"
    add_menu_directory_item(view_name + string_load(30321), url)

    xbmcplugin.endOfDirectory(handle)


def display_musicvideos_type(params: Dict[str, str], view):
    handle: int = int(sys.argv[1])
    xbmcplugin.setContent(handle, 'files')

    view_name = view.get("Name")

    # artists
    url_params: Dict[str, str] = {}
    url_params["ParentId"] = view.get("Id")
    url_params["Recursive"] = str(False)
    url_params["ImageTypeLimit"] = str(1)
    url_params["IsMissing"] = str(False)
    url_params["Fields"] = "{field_filters}"
    path = get_emby_url("{server}/emby/Users/{userid}/Items", url_params)
    url = sys.argv[0] + "?url=" + urllib.parse.quote(path) + "&mode=GET_CONTENT&media_type=musicvideos"
    add_menu_directory_item(view_name + string_load(30405), url)

    xbmcplugin.endOfDirectory(handle)


def display_livetv_type(menu_params, view):
    handle = int(sys.argv[1])
    xbmcplugin.setContent(handle, 'files')

    view_name = view.get("Name")

    # channels
    params: Dict[str, str] = {}
    params["UserId"] = "{userid}"
    params["Recursive"] = str(False)
    params["ImageTypeLimit"] = str(1)
    params["Fields"] = "{field_filters}"
    path = get_emby_url("{server}/emby/LiveTv/Channels", params)
    url = sys.argv[0] + "?url=" + urllib.parse.quote(path) + "&mode=GET_CONTENT&media_type=livetv"
    add_menu_directory_item(view_name + string_load(30360), url)

    # programs
    params = {}
    params["UserId"] = "{userid}"
    params["IsAiring"] = str(True)
    params["ImageTypeLimit"] = str(1)
    params["Fields"] = "ChannelInfo,{field_filters}"
    params["EnableTotalRecordCount"] = str(False)
    path = get_emby_url("{server}/emby/LiveTv/Programs/Recommended", params)
    url = sys.argv[0] + "?url=" + urllib.parse.quote(path) + "&mode=GET_CONTENT&media_type=livetv"
    add_menu_directory_item(view_name + string_load(30361), url)

    # recordings
    params = {}
    params["UserId"] = "{userid}"
    params["Recursive"] = str(False)
    params["ImageTypeLimit"] = str(1)
    params["Fields"] = "{field_filters}"
    params["EnableTotalRecordCount"] = str(False)
    path = get_emby_url("{server}/emby/LiveTv/Recordings", params)
    url = sys.argv[0] + "?url=" + urllib.parse.quote(path) + "&mode=GET_CONTENT&media_type=livetv"
    add_menu_directory_item(view_name + string_load(30362), url)

    xbmcplugin.endOfDirectory(handle)


def display_movies_type(menu_params, view):
    handle = int(sys.argv[1])
    xbmcplugin.setContent(handle, 'files')

    view_name = string_load(30256)
    if view is not None:
        view_name = view.get("Name")

    settings = xbmcaddon.Addon()
    show_x_filtered_items = settings.getSetting("show_x_filtered_items")
    group_movies = settings.getSetting('group_movies') == "true"
    hide_watched = settings.getSetting("hide_watched") == "true"

    base_params: Dict[str, str] = {}
    if view is not None:
        base_params["ParentId"] = view.get("Id")
    base_params["IncludeItemTypes"] = "Movie"
    base_params["CollapseBoxSetItems"] = str(group_movies)
    base_params["GroupItemsIntoCollections"] = str(group_movies)
    base_params["Recursive"] = str(True)
    base_params["IsMissing"] = str(False)
    base_params["Fields"] = "{field_filters}"
    base_params["ImageTypeLimit"] = str(1)

    # All Movies
    path = get_emby_url("{server}/emby/Users/{userid}/Items", base_params)
    url = sys.argv[0] + "?url=" + urllib.parse.quote(path) + "&mode=GET_CONTENT&media_type=movies"
    add_menu_directory_item(view_name + string_load(30405), url)

    # Favorite Movies
    params: Dict[str, str] = {}
    params.update(base_params)
    params["CollapseBoxSetItems"] = str(False)
    params["GroupItemsIntoCollections"] = str(False)
    params["Filters"] = "IsFavorite"
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.parse.quote(path) + "&mode=GET_CONTENT&media_type=movies"
    add_menu_directory_item(view_name + string_load(30414), url)

    # Unwatched Movies
    params = {}
    params.update(base_params)
    params["CollapseBoxSetItems"] = str(False)
    params["GroupItemsIntoCollections"] = str(False)
    params["IsPlayed"] = str(False)
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.parse.quote(path) + "&mode=GET_CONTENT&media_type=movies"
    add_menu_directory_item(view_name + string_load(30285), url)

    # Recently Watched Movies
    params = {}
    params.update(base_params)
    params["IsPlayed"] = str(True)
    params["SortBy"] = "DatePlayed"
    params["SortOrder"] = "Descending"
    params["CollapseBoxSetItems"] = str(False)
    params["GroupItemsIntoCollections"] = str(False)
    params["Limit"] = "{ItemLimit}"
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.parse.quote(path) + "&mode=GET_CONTENT&media_type=movies&sort=none"
    add_menu_directory_item(view_name + string_load(30349) + " (" + show_x_filtered_items + ")", url)

    # Resumable Movies
    params = {}
    params.update(base_params)
    params["Filters"] = "IsResumable"
    params["SortBy"] = "DatePlayed"
    params["SortOrder"] = "Descending"
    params["Limit"] = "{ItemLimit}"
    params["CollapseBoxSetItems"] = str(False)
    params["GroupItemsIntoCollections"] = str(False)
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.parse.quote(path) + "&mode=GET_CONTENT&media_type=movies&sort=none"
    add_menu_directory_item(view_name + string_load(30267) + " (" + show_x_filtered_items + ")", url)

    # Recently Added Movies
    params = {}
    params.update(base_params)
    if hide_watched:
        params["IsPlayed"] = str(False)
    params["SortBy"] = "DateCreated"
    params["SortOrder"] = "Descending"
    params["Filters"] = "IsNotFolder"
    params["Limit"] = "{ItemLimit}"
    params["CollapseBoxSetItems"] = str(False)
    params["GroupItemsIntoCollections"] = str(False)
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.parse.quote(path) + "&mode=GET_CONTENT&media_type=movies&sort=none"
    add_menu_directory_item(view_name + string_load(30268) + " (" + show_x_filtered_items + ")", url)

    # Collections
    params = {}
    if view is not None:
        params["ParentId"] = view.get("Id")
    params["Fields"] = "{field_filters}"
    params["ImageTypeLimit"] = str(1)
    params["IncludeItemTypes"] = "Boxset"
    params["Recursive"] = str(True)
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.parse.quote(path) + "&mode=GET_CONTENT&media_type=boxsets"
    add_menu_directory_item(view_name + string_load(30410), url)

    # Favorite Collections
    params["Filters"] = "IsFavorite"
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.parse.quote(path) + "&mode=GET_CONTENT&media_type=boxsets"
    add_menu_directory_item(view_name + string_load(30415), url)

    # Genres
    path = "plugin://plugin.video.embycon/?mode=GENRES&item_type=movie"
    if view is not None:
        path += "&parent_id=" + view.get("Id")
    add_menu_directory_item(view_name + string_load(30325), path)

    # Pages
    path = "plugin://plugin.video.embycon/?mode=MOVIE_PAGES"
    if view is not None:
        path += "&parent_id=" + view.get("Id")
    add_menu_directory_item(view_name + string_load(30397), path)

    # Alpha Picker
    path = "plugin://plugin.video.embycon/?mode=MOVIE_ALPHA"
    if view is not None:
        path += "&parent_id=" + view.get("Id")
    add_menu_directory_item(view_name + string_load(30404), path)

    # Years
    path = "plugin://plugin.video.embycon/?mode=SHOW_ADDON_MENU&type=show_movie_years"
    if view is not None:
        path += "&parent_id=" + view.get("Id")
    add_menu_directory_item(view_name + string_load(30411), path)

    # Decades
    path = "plugin://plugin.video.embycon/?mode=SHOW_ADDON_MENU&type=show_movie_years&group=true"
    if view is not None:
        path += "&parent_id=" + view.get("Id")
    add_menu_directory_item(view_name + string_load(30412), path)

    # Tags
    path = "plugin://plugin.video.embycon/?mode=SHOW_ADDON_MENU&type=show_movie_tags"
    if view is not None:
        path += "&parent_id=" + view.get("Id")
    add_menu_directory_item(view_name + string_load(30413), path)

    xbmcplugin.endOfDirectory(handle)


def display_library_views(params):
    handle = int(sys.argv[1])
    xbmcplugin.setContent(handle, 'files')

    server = downloadUtils.get_server()
    if server is None:
        return

    settings = xbmcaddon.Addon()
    max_image_width = int(settings.getSetting('max_image_width'))

    data_manager = DataManager()
    views_url = "{server}/emby/Users/{userid}/Views?format=json"
    views = data_manager.get_content(views_url)
    if not views:
        return []
    views = views.get("Items")

    view_types = ["movies", "tvshows", "homevideos", "boxsets", "playlists", "music", "musicvideos", "livetv", "Channel"]

    for view in views:
        collection_type = view.get('CollectionType', None)
        item_type = view.get('Type', None)
        if collection_type in view_types or item_type == "Channel":
            view_name = view.get("Name")
            art = get_art(item=view, server=server, maxwidth=max_image_width)
            art['landscape'] = downloadUtils.get_artwork(view, "Primary", server=server, maxwidth=max_image_width)

            plugin_path = "plugin://plugin.video.embycon/?mode=SHOW_ADDON_MENU&type=library_item&view_id=" + view.get("Id")

            if collection_type == "playlists":
                plugin_path = get_playlist_path(view)
            elif collection_type == "boxsets":
                plugin_path = get_collection_path(view)
            elif collection_type is None and view.get('Type', None) == "Channel":
                plugin_path = get_channel_path(view)

            add_menu_directory_item(view_name, plugin_path, art=art)

    xbmcplugin.endOfDirectory(handle)


def get_playlist_path(view_info):
    params = {
        "ParentId": view_info.get("Id"),
        "Fields": "{field_filters}",
        "ImageTypeLimit": 1
    }
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.parse.quote(path) + "&mode=GET_CONTENT&media_type=playlists"
    return url


def get_collection_path(view_info):
    params: Dict[str, str] = {
        "ParentId": view_info.get("Id"),
        "Fields": "{field_filters}",
        "ImageTypeLimit": str(1),
        "IncludeItemTypes": "Boxset",
        "CollapseBoxSetItems": str(True),
        "GroupItemsIntoCollections": str(True),
        "Recursive": str(True),
        "IsMissing": str(False)
    }
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.parse.quote(path) + "&mode=GET_CONTENT&media_type=boxsets"
    return url


def get_channel_path(view):
    params: Dict[str, str] = {
        "ParentId": view.get("Id"),
        "IsMissing": str(False),
        "ImageTypeLimit": str(1),
        "Fields": "{field_filters}"
    }
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.parse.quote(path) + "&mode=GET_CONTENT&media_type=files"
    return url


def display_library_view(params):
    node_id = params.get("view_id")

    view_info_url = "{server}/emby/Users/{userid}/Items/" + node_id
    data_manager = DataManager()
    view_info = data_manager.get_content(view_info_url)

    log.debug("VIEW_INFO : {0}", view_info)

    collection_type = view_info.get("CollectionType", None)

    if collection_type == "movies":
        display_movies_type(params, view_info)
    elif collection_type == "tvshows":
        display_tvshow_type(params, view_info)
    elif collection_type == "homevideos":
        display_homevideos_type(params, view_info)
    elif collection_type == "music":
        display_music_type(params, view_info)
    elif collection_type == "musicvideos":
        display_musicvideos_type(params, view_info)
    elif collection_type == "livetv":
        display_livetv_type(params, view_info)


def show_widgets() -> None:
    settings = xbmcaddon.Addon()
    show_x_filtered_items = settings.getSetting("show_x_filtered_items")

    add_menu_directory_item("All Movies",
                            'plugin://plugin.video.embycon/library/movies')

    add_menu_directory_item(string_load(30257) + " (" + show_x_filtered_items + ")",
                            'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=recent_movies')
    add_menu_directory_item(string_load(30258) + " (" + show_x_filtered_items + ")",
                            'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=inprogress_movies')
    add_menu_directory_item(string_load(30269) + " (" + show_x_filtered_items + ")",
                            'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=random_movies')
    add_menu_directory_item(string_load(30403) + " (" + show_x_filtered_items + ")",
                            'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=movie_recommendations')

    add_menu_directory_item(string_load(30287) + " (" + show_x_filtered_items + ")",
                            'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=recent_tvshows')
    add_menu_directory_item(string_load(30263) + " (" + show_x_filtered_items + ")",
                            'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=recent_episodes')
    add_menu_directory_item(string_load(30264) + " (" + show_x_filtered_items + ")",
                            'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=inprogress_episodes')
    add_menu_directory_item(string_load(30265) + " (" + show_x_filtered_items + ")",
                            'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=nextup_episodes')

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def show_search():
    add_menu_directory_item(string_load(30231), 'plugin://plugin.video.embycon/?mode=NEW_SEARCH&item_type=Movie')
    add_menu_directory_item(string_load(30229), 'plugin://plugin.video.embycon/?mode=NEW_SEARCH&item_type=Series')
    add_menu_directory_item(string_load(30235), 'plugin://plugin.video.embycon/?mode=NEW_SEARCH&item_type=Episode')
    add_menu_directory_item(string_load(30337), 'plugin://plugin.video.embycon/?mode=NEW_SEARCH&item_type=Audio')
    add_menu_directory_item(string_load(30338), 'plugin://plugin.video.embycon/?mode=NEW_SEARCH&item_type=MusicAlbum')
    add_menu_directory_item(string_load(30339), 'plugin://plugin.video.embycon/?mode=NEW_SEARCH&item_type=Person')

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def set_library_window_values(force=False):
    log.debug("set_library_window_values Called forced={0}", force)
    home_window = HomeWindow()

    already_set = home_window.get_property("view_item.0.name")
    if not force and already_set:
        return

    for index in range(0, 20):
        home_window.clear_property("view_item.%i.name" % index)
        home_window.clear_property("view_item.%i.id" % index)
        home_window.clear_property("view_item.%i.type" % index)
        home_window.clear_property("view_item.%i.thumb" % index)

    data_manager = DataManager()
    url = "{server}/emby/Users/{userid}/Views"
    result = data_manager.get_content(url)

    if result is None:
        return

    result = result.get("Items")
    server = downloadUtils.get_server()

    settings = xbmcaddon.Addon()
    max_image_width = int(settings.getSetting('max_image_width'))

    index = 0
    for item in result:

        collection_type = item.get("CollectionType")
        if collection_type in ["movies", "boxsets", "music", "tvshows"]:
            name = item.get("Name")
            item_id = item.get("Id")

            # plugin.video.embycon-
            prop_name = "view_item.%i.name" % index
            home_window.set_property(prop_name, name)
            log.debug("set_library_window_values: plugin.video.embycon-{0}={1}", prop_name, name)

            prop_name = "view_item.%i.id" % index
            home_window.set_property(prop_name, item_id)
            log.debug("set_library_window_values: plugin.video.embycon-{0}={1}", prop_name, item_id)

            prop_name = "view_item.%i.type" % index
            home_window.set_property(prop_name, collection_type)
            log.debug("set_library_window_values: plugin.video.embycon-{0}={1}", prop_name, collection_type)

            thumb = downloadUtils.get_artwork(item, "Primary", server=server, maxwidth=max_image_width)
            prop_name = "view_item.%i.thumb" % index
            home_window.set_property(prop_name, thumb)
            log.debug("set_library_window_values: plugin.video.embycon-{0}={1}", prop_name, thumb)

            index += 1
