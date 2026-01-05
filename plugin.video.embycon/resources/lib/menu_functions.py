# coding=utf-8
# Gnu General Public License - see LICENSE.TXT
from __future__ import annotations

import os
import sys
import urllib.parse
import base64
import json
import hashlib

import xbmcplugin
import xbmcaddon
import xbmcvfs
import xbmcgui
import xbmc

from .downloadutils import DownloadUtils, save_user_details, load_user_details
from .kodi_utils import add_menu_directory_item, HomeWindow
from .simple_logging import SimpleLogging
from .translation import string_load
from .datamanager import DataManager
from .utils import get_art, get_emby_url
from .custom_nodes import CustomNode, load_custom_nodes

log = SimpleLogging(__name__)


def do_user_change(menu_params: dict[str, str]) -> None:
    log.info("do_user_change: {0}", menu_params)

    settings = xbmcaddon.Addon()

    user_details = load_user_details(settings)
    current_username = user_details.get("username", "")
    user_name = menu_params.get("user")
    user_id = menu_params.get("userid")

    if current_username != user_name:
        log.info("Changing user to: {0}", user_name)

        # looking up new user details
        du = DownloadUtils()
        server = du.get_server()
        if server is None or len(server) == 0:
            return

        # get a list of users
        log.debug("Getting user list")
        json_data = du.download_url(
            server + "/emby/Users/Public?format=json", authenticate=False
        )

        log.debug("jsonData: {0}", json_data)
        try:
            result = json.loads(json_data)
        except Exception:
            result = None

        if result is None:
            xbmcgui.Dialog().ok("Error", "Failed to retrieve user list.")
            return

        selected_user = None
        for user in result:
            if user.get("Id") == user_id:
                selected_user = user
                break

        if selected_user is None:
            xbmcgui.Dialog().ok("Error", "Could not find selected user.")
            return

        selected_user_name = selected_user.get("Name", "")

        # handle passwords
        if selected_user.get("HasPassword", False) is True:
            m = hashlib.md5()
            m.update(selected_user_name.encode("utf-8"))
            hashed_username = m.hexdigest()
            saved_password = settings.getSetting(
                "saved_user_password_" + hashed_username
            )
            allow_password_saving = (
                settings.getSetting("allow_password_saving") == "true"
            )

            # if not saving passwords but have a saved ask to clear it
            if not allow_password_saving and saved_password:
                clear_password = xbmcgui.Dialog().yesno(
                    string_load(30368), string_load(30369)
                )
                if clear_password:
                    settings.setSetting("saved_user_password_" + hashed_username, "")

            if saved_password:
                log.debug("Saving username and password: {0}", selected_user_name)
                log.debug("Using stored password for user: {0}", hashed_username)
                save_user_details(settings, selected_user_name, saved_password)

            else:
                kb = xbmc.Keyboard()
                kb.setHeading(string_load(30006))
                kb.setHiddenInput(True)
                kb.doModal()
                if kb.isConfirmed():
                    log.debug("Saving username and password: {0}", selected_user_name)
                    save_user_details(settings, selected_user_name, kb.getText())

                    # should we save the password
                    if allow_password_saving:
                        save_password = xbmcgui.Dialog().yesno(
                            string_load(30363), string_load(30364)
                        )
                        if save_password:
                            log.debug(
                                "Saving password for fast user switching: {0}",
                                hashed_username,
                            )
                            settings.setSetting(
                                "saved_user_password_" + hashed_username,
                                kb.getText(),
                            )

        else:
            log.debug("User has no password, saving details.")
            save_user_details(settings, selected_user_name, "")

        home_window = HomeWindow()
        home_window.clear_property("userid")
        home_window.clear_property("AccessToken")
        home_window.clear_property("userimage")
        home_window.clear_property("embycon_widget_reload")
        du = DownloadUtils()
        du.authenticate()
        du.get_user_id()
        log.debug("Changed user - reloading skin")
        xbmc.executebuiltin("Dialog.Close(all,true)")
        xbmc.executebuiltin("ActivateWindow(Home)")
        if "estuary_embycon" in xbmc.getSkinDir():
            xbmc.executebuiltin("SetFocus(9000, 0, absolute)")
        xbmc.executebuiltin("ReloadSkin()")


def show_user_lists(menu_params: dict[str, str]) -> None:
    log.info("show_user_lists: {0}", menu_params)
    du = DownloadUtils()

    server = du.get_server()
    if server is None or len(server) == 0:
        return

    # get a list of users
    log.info("Getting user list")
    json_data = du.download_url(
        server + "/emby/Users/Public?format=json", authenticate=False
    )

    log.debug("jsonData: {0}", json_data)
    try:
        result = json.loads(json_data)
    except Exception:
        result = []

    if result is None:
        result = []

    settings = xbmcaddon.Addon()
    user_details = load_user_details(settings)
    current_username = user_details.get("username", "")

    for user in result:
        is_hidden = False
        if user.get("Configuration", {}).get("IsHidden", False) is True:
            is_hidden = True

        if not is_hidden:
            name = user.get("Name")
            display_name = name
            if name == current_username:
                display_name = name + " *"
            user_item = xbmcgui.ListItem(
                label=display_name, label2=name, offscreen=True
            )
            user_image = du.get_user_artwork(user, "Primary")
            if not user_image:
                user_image = "DefaultUser.png"
            art = {"Thumb": user_image}
            user_item.setArt(art)

            url = sys.argv[0] + (
                "?mode=DO_USER_CHANGE" + "&user=" + name + "&userid=" + user.get("Id")
            )

            log.info("Adding User: {0}", name)
            xbmcplugin.addDirectoryItem(
                handle=int(sys.argv[1]), url=url, listitem=user_item, isFolder=False
            )

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def show_movie_tags(menu_params: dict[str, str]) -> None:
    log.debug("show_movie_tags: {0}", menu_params)
    parent_id = menu_params.get("parent_id")

    url_params: dict[str, object] = {}
    url_params["UserId"] = "{userid}"
    url_params["SortBy"] = "SortName"
    url_params["SortOrder"] = "Ascending"
    url_params["CollapseBoxSetItems"] = False
    url_params["GroupItemsIntoCollections"] = False
    url_params["Recursive"] = True
    url_params["IsMissing"] = False
    url_params["EnableTotalRecordCount"] = False
    url_params["EnableUserData"] = False
    url_params["IncludeItemTypes"] = "Movie"

    if parent_id:
        url_params["ParentId"] = parent_id

    url = get_emby_url("{server}/emby/Tags", url_params)
    data_manager = DataManager()
    result = data_manager.get_content(url)

    if not result:
        return

    tags = result.get("Items", [])

    log.debug("Tags : {0}", result)

    for tag in tags:
        name = tag["Name"]
        tag_id = tag["Id"]

        url_params: dict[str, object] = {}
        url_params["IncludeItemTypes"] = "Movie"
        url_params["CollapseBoxSetItems"] = False
        url_params["GroupItemsIntoCollections"] = False
        url_params["Recursive"] = True
        url_params["IsMissing"] = False
        url_params["ImageTypeLimit"] = 1
        url_params["SortBy"] = "Name"
        url_params["SortOrder"] = "Ascending"
        url_params["Fields"] = "{field_filters}"
        url_params["TagIds"] = tag_id

        if parent_id:
            menu_params["ParentId"] = parent_id

        item_url = get_emby_url("{server}/emby/Users/{userid}/Items", url_params)

        art = {
            "thumb": "http://localhost:24276/"
            + base64.b64encode(item_url.encode("utf-8")).decode("utf-8")
        }

        content_url = urllib.parse.quote(item_url)
        url = sys.argv[0] + (
            "?url=" + content_url + "&mode=GET_CONTENT" + "&media_type=movies"
        )
        log.debug("addMenuDirectoryItem: {0} - {1}", name, url)
        add_menu_directory_item(name, url, art=art)

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def show_movie_years(menu_params: dict[str, str]) -> None:
    log.debug("show_movie_years: {0}", menu_params)
    parent_id = menu_params.get("parent_id")
    group_into_decades = menu_params.get("group") == "true"

    url_params: dict[str, object] = {}
    url_params["UserId"] = "{userid}"
    url_params["SortBy"] = "SortName"
    url_params["SortOrder"] = "Ascending"
    url_params["CollapseBoxSetItems"] = False
    url_params["GroupItemsIntoCollections"] = False
    url_params["Recursive"] = True
    url_params["IsMissing"] = False
    url_params["EnableTotalRecordCount"] = False
    url_params["EnableUserData"] = False
    url_params["IncludeItemTypes"] = "Movie"

    if parent_id:
        url_params["ParentId"] = parent_id

    url = get_emby_url("{server}/emby/Years", url_params)

    data_manager = DataManager()
    result = data_manager.get_content(url)

    if not result:
        return

    years_list = result.get("Items", [])
    result_names = {}
    for year in years_list:
        name = year.get("Name")
        if group_into_decades:
            year_int = int(name)
            decade = str(year_int - year_int % 10)
            decade_end = str((year_int - year_int % 10) + 9)
            decade_name = decade + "-" + decade_end
            result_names[decade_name] = year_int - year_int % 10
        else:
            result_names[name] = [name]

    keys = list(result_names.keys())
    keys.sort()

    if group_into_decades:
        for decade_key in keys:
            year_list = []
            decade_start = result_names[decade_key]
            for include_year in range(decade_start, decade_start + 10):
                year_list.append(str(include_year))
            result_names[decade_key] = year_list

    for year in keys:
        name = year
        value = ",".join(result_names[year])

        params: dict[str, object] = {}
        params["IncludeItemTypes"] = "Movie"
        params["CollapseBoxSetItems"] = False
        params["GroupItemsIntoCollections"] = False
        params["Recursive"] = True
        params["IsMissing"] = False
        params["ImageTypeLimit"] = 1
        params["SortBy"] = "Name"
        params["SortOrder"] = "Ascending"
        params["Fields"] = "{field_filters}"
        params["Years"] = value

        if parent_id:
            params["ParentId"] = parent_id

        item_url = get_emby_url("{server}/emby/Users/{userid}/Items", params)

        art = {
            "thumb": "http://localhost:24276/"
            + base64.b64encode(item_url.encode("utf-8")).decode("utf-8")
        }

        content_url = urllib.parse.quote(item_url)
        url = sys.argv[0] + (
            "?url=" + content_url + "&mode=GET_CONTENT" + "&media_type=movies"
        )
        log.debug("addMenuDirectoryItem: {0} - {1}", name, url)
        add_menu_directory_item(name, url, art=art)

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def show_movie_pages(menu_params: dict[str, str]) -> None:
    log.debug("showMoviePages: {0}", menu_params)

    parent_id = menu_params.get("parent_id")
    settings = xbmcaddon.Addon()

    params: dict[str, object] = {}
    params["IncludeItemTypes"] = "Movie"
    params["CollapseBoxSetItems"] = False
    params["GroupItemsIntoCollections"] = False
    params["Recursive"] = True
    params["IsMissing"] = False
    params["ImageTypeLimit"] = 0

    if parent_id:
        params["ParentId"] = parent_id

    url = get_emby_url("{server}/emby/Users/{userid}/Items", params)

    data_manager = DataManager()
    result = data_manager.get_content(url)

    if result is None:
        return

    total_results = result.get("TotalRecordCount", 0)
    log.debug("showMoviePages TotalRecordCount {0}", total_results)

    if result == 0:
        return

    page_limit = int(settings.getSetting("itemsPerPage"))
    if page_limit == 0:
        page_limit = 20

    start_index = 0
    collections = []

    while start_index < total_results:
        params: dict[str, object] = {}
        params["IncludeItemTypes"] = "Movie"
        params["CollapseBoxSetItems"] = False
        params["GroupItemsIntoCollections"] = False
        params["Recursive"] = True
        params["IsMissing"] = False
        params["ImageTypeLimit"] = 1
        params["SortBy"] = "Name"
        params["SortOrder"] = "Ascending"
        params["Fields"] = "{field_filters}"
        params["StartIndex"] = start_index
        params["Limit"] = page_limit

        if parent_id:
            params["ParentId"] = parent_id

        item_url = get_emby_url("{server}/emby/Users/{userid}/Items", params)

        page_upper = start_index + page_limit
        if page_upper > total_results:
            page_upper = total_results

        item_data = {}
        item_data["title"] = (
            "Page (" + str(start_index + 1) + " - " + str(page_upper) + ")"
        )
        item_data["path"] = item_url
        item_data["media_type"] = "movies"

        item_data["art"] = {
            "thumb": "http://localhost:24276/"
            + base64.b64encode(item_url.encode("utf-8")).decode("utf-8")
        }

        collections.append(item_data)
        start_index = start_index + page_limit

    for collection in collections:
        content_url = urllib.parse.quote(collection["path"])
        url = sys.argv[0] + (
            "?url="
            + content_url
            + "&mode=GET_CONTENT"
            + "&media_type="
            + collection["media_type"]
        )
        log.debug(
            "addMenuDirectoryItem: {0} - {1} - {2}",
            collection.get("title"),
            url,
            collection.get("art"),
        )
        add_menu_directory_item(
            collection.get("title", string_load(30250)), url, art=collection.get("art")
        )

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def show_genre_list(menu_params: dict[str, str]) -> None:
    log.debug("showGenreList: {0}", menu_params)

    download_utils = DownloadUtils()
    server = download_utils.get_server()
    if server is None:
        return

    parent_id = menu_params.get("parent_id")
    item_type = menu_params.get("item_type")

    kodi_type = "Movies"
    emby_type = "Movie"
    if item_type is not None and item_type == "tvshow":
        emby_type = "Series"
        kodi_type = "tvshows"

    params: dict[str, object] = {}
    params["IncludeItemTypes"] = emby_type
    params["UserId"] = "{userid}"
    params["Recursive"] = True
    params["SortBy"] = "Name"
    params["SortOrder"] = "Ascending"
    params["ImageTypeLimit"] = 1

    if parent_id is not None:
        params["ParentId"] = parent_id

    url = get_emby_url("{server}/emby/Genres", params)

    data_manager = DataManager()
    result = data_manager.get_content(url)

    if result is not None:
        result = result.get("Items", [])
    else:
        result = []

    collections = []
    xbmcplugin.setContent(int(sys.argv[1]), "genres")

    for genre in result:
        item_data = {}
        item_data["title"] = genre.get("Name")
        item_data["media_type"] = kodi_type

        # art = getArt(item=genre, server=server)
        # item_data['art'] = art

        params: dict[str, object] = {}
        params["Recursive"] = True
        params["CollapseBoxSetItems"] = False
        params["GroupItemsIntoCollections"] = False
        params["GenreIds"] = genre.get("Id")
        params["IncludeItemTypes"] = emby_type
        params["ImageTypeLimit"] = 1
        params["Fields"] = "{field_filters}"

        if parent_id is not None:
            params["ParentId"] = parent_id

        url = get_emby_url("{server}/emby/Users/{userid}/Items", params)

        art = {
            "thumb": "http://localhost:24276/"
            + base64.b64encode(url.encode("utf-8")).decode("utf-8")
        }
        item_data["art"] = art

        item_data["path"] = url
        collections.append(item_data)

    for collection in collections:
        url = sys.argv[0] + (
            "?url="
            + urllib.parse.quote(collection["path"])
            + "&mode=GET_CONTENT"
            + "&media_type="
            + collection["media_type"]
        )
        log.debug(
            "addMenuDirectoryItem: {0} - {1} - {2}",
            collection.get("title"),
            url,
            collection.get("art"),
        )
        add_menu_directory_item(
            collection.get("title", string_load(30250)), url, art=collection.get("art")
        )

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def show_movie_alpha_list(menu_params: dict[str, str]) -> None:
    log.debug("== ENTER: showMovieAlphaList() ==")

    xbmcplugin.setContent(int(sys.argv[1]), "movies")

    download_utils = DownloadUtils()
    server = download_utils.get_server()
    if server is None:
        return

    parent_id = menu_params.get("parent_id")

    url_params: dict[str, object] = {}
    url_params["IncludeItemTypes"] = "Movie"
    url_params["Recursive"] = True
    url_params["CollapseBoxSetItems"] = False
    url_params["GroupItemsIntoCollections"] = False
    url_params["UserId"] = "{userid}"
    url_params["SortBy"] = "Name"
    url_params["SortOrder"] = "Ascending"
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
        item_data = {}
        item_data["title"] = alphaName
        item_data["media_type"] = "Movies"

        params: dict[str, object] = {}
        params["Fields"] = "{field_filters}"
        params["CollapseBoxSetItems"] = False
        params["GroupItemsIntoCollections"] = False
        params["Recursive"] = True
        params["IncludeItemTypes"] = "Movie"
        params["SortBy"] = "Name"
        params["SortOrder"] = "Ascending"
        params["ImageTypeLimit"] = 1

        if parent_id is not None:
            params["ParentId"] = parent_id

        if alphaName == "#":
            params["NameLessThan"] = "A"
        else:
            params["NameStartsWith"] = alphaName

        url = get_emby_url("{server}/emby/Users/{userid}/Items", params)
        item_data["path"] = url

        art = {
            "thumb": "http://localhost:24276/"
            + base64.b64encode(url.encode("utf-8")).decode("utf-8")
        }
        item_data["art"] = art

        collections.append(item_data)

    for collection in collections:
        url = (
            sys.argv[0]
            + "?url="
            + urllib.parse.quote(collection["path"])
            + "&mode=GET_CONTENT&media_type="
            + collection["media_type"]
        )
        log.debug("addMenuDirectoryItem: {0} ({1})", collection.get("title"), url)
        add_menu_directory_item(
            collection.get("title", string_load(30250)), url, art=collection.get("art")
        )

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def show_tvshow_alpha_list(menu_params: dict[str, str]) -> None:
    log.debug("== ENTER: showTvShowAlphaList() ==")

    download_utils = DownloadUtils()
    server = download_utils.get_server()
    if server is None:
        return

    parent_id = menu_params.get("parent_id")

    url_params: dict[str, object] = {}
    url_params["IncludeItemTypes"] = "Series"
    url_params["Recursive"] = True
    url_params["UserId"] = "{userid}"
    url_params["SortBy"] = "Name"
    url_params["SortOrder"] = "Ascending"
    if parent_id is not None:
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
        item_data = {}
        item_data["title"] = alpha_name
        item_data["media_type"] = "tvshows"

        params: dict[str, object] = {}
        params["Fields"] = "{field_filters}"
        params["ImageTypeLimit"] = 1
        params["IncludeItemTypes"] = "Series"
        params["SortBy"] = "Name"
        params["SortOrder"] = "Ascending"
        params["Recursive"] = True
        params["IsMissing"] = False

        if parent_id is not None:
            params["ParentId"] = parent_id

        if alpha_name == "#":
            params["NameLessThan"] = "A"
        else:
            params["NameStartsWith"] = alpha_name

        path = get_emby_url("{server}/emby/Users/{userid}/Items", params)

        item_data["path"] = path

        art = {
            "thumb": "http://localhost:24276/"
            + base64.b64encode(path.encode("utf-8")).decode("utf-8")
        }
        item_data["art"] = art

        collections.append(item_data)

    for collection in collections:
        url = (
            sys.argv[0]
            + "?url="
            + urllib.parse.quote(collection["path"])
            + "&mode=GET_CONTENT&media_type="
            + collection["media_type"]
        )
        log.debug("addMenuDirectoryItem: {0} ({1})", collection.get("title"), url)
        add_menu_directory_item(
            collection.get("title", string_load(30250)), url, art=collection.get("art")
        )

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def show_tvshow_pages(menu_params: dict[str, str]) -> None:
    log.debug("showTvShowPages: {0}", menu_params)

    parent_id = menu_params.get("parent_id")
    settings = xbmcaddon.Addon()

    params: dict[str, object] = {}
    params["IncludeItemTypes"] = "Series"
    params["IsMissing"] = False
    params["Recursive"] = True
    params["ImageTypeLimit"] = 0

    if parent_id:
        params["ParentId"] = parent_id

    url = get_emby_url("{server}/emby/Users/{userid}/Items", params)

    data_manager = DataManager()
    result = data_manager.get_content(url)

    if result is None:
        return

    total_results = result.get("TotalRecordCount", 0)
    log.debug("showMoviePages TotalRecordCount {0}", total_results)

    if result == 0:
        return

    page_limit = int(settings.getSetting("itemsPerPage"))
    if page_limit == 0:
        page_limit = 20

    start_index = 0
    collections = []

    while start_index < total_results:
        params: dict[str, object] = {}
        params["IncludeItemTypes"] = "Series"
        params["IsMissing"] = False
        params["Recursive"] = True
        params["ImageTypeLimit"] = 1
        params["SortBy"] = "Name"
        params["SortOrder"] = "Ascending"
        params["Fields"] = "{field_filters}"
        params["StartIndex"] = start_index
        params["Limit"] = page_limit

        if parent_id:
            params["ParentId"] = parent_id

        item_url = get_emby_url("{server}/emby/Users/{userid}/Items", params)

        page_upper = start_index + page_limit
        if page_upper > total_results:
            page_upper = total_results

        item_data = {}
        item_data["title"] = (
            "Page (" + str(start_index + 1) + " - " + str(page_upper) + ")"
        )
        item_data["path"] = item_url
        item_data["media_type"] = "tvshows"

        item_data["art"] = {
            "thumb": "http://localhost:24276/"
            + base64.b64encode(item_url.encode("utf-8")).decode("utf-8")
        }

        collections.append(item_data)
        start_index = start_index + page_limit

    for collection in collections:
        content_url = urllib.parse.quote(collection["path"])
        url = sys.argv[0] + (
            "?url="
            + content_url
            + "&mode=GET_CONTENT"
            + "&media_type="
            + collection["media_type"]
        )
        log.debug(
            "addMenuDirectoryItem: {0} - {1} - {2}",
            collection.get("title"),
            url,
            collection.get("art"),
        )
        add_menu_directory_item(
            collection.get("title", string_load(30250)), url, art=collection.get("art")
        )

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def display_main_menu() -> None:
    handle = int(sys.argv[1])
    xbmcplugin.setContent(handle, "files")

    add_menu_directory_item(
        string_load(30406),
        "plugin://plugin.video.embycon/?mode=SHOW_ADDON_MENU&type=library",
    )
    add_menu_directory_item(
        string_load(30407),
        "plugin://plugin.video.embycon/?mode=SHOW_ADDON_MENU&type=show_global_types",
    )
    add_menu_directory_item(
        string_load(30408),
        "plugin://plugin.video.embycon/?mode=SHOW_ADDON_MENU&type=show_custom_widgets",
    )
    add_menu_directory_item(
        string_load(30409),
        "plugin://plugin.video.embycon/?mode=SHOW_ADDON_MENU&type=addon_items",
    )
    add_menu_directory_item(
        "Custom Nodes",
        "plugin://plugin.video.embycon/?mode=SHOW_ADDON_MENU&type=custom_nodes",
    )

    xbmcplugin.endOfDirectory(handle)


def display_menu(params: dict[str, str]) -> None:
    menu_type = params.get("type")
    if menu_type == "library":
        display_library_views(params)
    elif menu_type == "library_item":
        display_library_view(params)
    elif menu_type == "show_global_types":
        show_global_types(params)
    elif menu_type == "global_list_movies":
        display_movies_type(params, {})
    elif menu_type == "global_list_tvshows":
        display_tvshow_type(params, {})
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


def create_new_node(_params: dict[str, str]) -> None:
    log.debug("Create New Custom Node")

    addon = xbmcaddon.Addon()
    addon_path = addon.getAddonInfo("path")
    skin_path = xbmcvfs.translatePath(os.path.join(addon_path))

    custom_node = CustomNode("CustomNode.xml", skin_path, "default", "720p")
    # custom_node.setActionItems(action_items)
    custom_node.doModal()


def get_node_url(node_info: dict[str, str]) -> str:
    log.debug("get_node_url : {0}", node_info)

    base_params: dict[str, object] = {}
    base_params["Fields"] = "{field_filters}"
    base_params["ImageTypeLimit"] = 1
    base_params["IsMissing"] = False

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

    return get_emby_url("{server}/emby/Users/{userid}/Items", base_params)


def show_custom_nodes(_params: dict[str, str]) -> None:
    log.debug("Show Custom Nodes")
    add_menu_directory_item(
        "[Edit Nodes]",
        "plugin://plugin.video.embycon/?mode=SHOW_ADDON_MENU&type=create_new_node",
        folder=False,
    )

    # show custom nodes
    custom_nodes = load_custom_nodes()

    node_names = []
    for node_name in custom_nodes:
        node_names.append(node_name)
    node_names.sort()

    for node_name in node_names:
        encoded_name = urllib.parse.quote(node_name)
        add_menu_directory_item(
            node_name,
            "plugin://plugin.video.embycon/?mode=SHOW_NODE_CONTENT&node_name="
            + encoded_name,
        )

    handle = int(sys.argv[1])
    xbmcplugin.endOfDirectory(handle)


def show_global_types(_params: dict[str, str]) -> None:
    handle = int(sys.argv[1])

    add_menu_directory_item(
        string_load(30256),
        "plugin://plugin.video.embycon/?mode=SHOW_ADDON_MENU&type=global_list_movies",
    )
    add_menu_directory_item(
        string_load(30261),
        "plugin://plugin.video.embycon/?mode=SHOW_ADDON_MENU&type=global_list_tvshows",
    )

    xbmcplugin.endOfDirectory(handle)


def display_homevideos_type(_menu_params: dict[str, str], view: dict[str, str]) -> None:
    handle = int(sys.argv[1])
    view_name = view.get("Name", "Unknown")
    settings = xbmcaddon.Addon()
    show_x_filtered_items = settings.getSetting("show_x_filtered_items")
    hide_watched = settings.getSetting("hide_watched") == "true"

    # All Home Movies
    base_params: dict[str, object] = {}
    base_params["ParentId"] = view.get("Id")
    base_params["Recursive"] = False
    base_params["IsMissing"] = False
    base_params["Fields"] = "{field_filters}"
    base_params["ImageTypeLimit"] = 1
    path = get_emby_url("{server}/emby/Users/{userid}/Items", base_params)
    url = (
        sys.argv[0]
        + "?url="
        + urllib.parse.quote(path)
        + "&mode=GET_CONTENT&media_type=homevideos"
    )
    add_menu_directory_item(view_name + string_load(30405), url)

    # In progress home movies
    params: dict[str, object] = {}
    params.update(base_params)
    params["Filters"] = "IsResumable"
    params["Recursive"] = True
    params["Limit"] = "{ItemLimit}"
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = (
        sys.argv[0]
        + "?url="
        + urllib.parse.quote(path)
        + "&mode=GET_CONTENT&media_type=homevideos"
    )
    add_menu_directory_item(
        view_name + string_load(30267) + " (" + show_x_filtered_items + ")", url
    )

    # Recently added
    params: dict[str, object] = {}
    params.update(base_params)
    params["Recursive"] = True
    params["SortBy"] = "DateCreated"
    params["SortOrder"] = "Descending"
    params["Filters"] = "IsNotFolder"
    if hide_watched:
        params["IsPlayed"] = False
    params["Limit"] = "{ItemLimit}"
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = (
        sys.argv[0]
        + "?url="
        + urllib.parse.quote(path)
        + "&mode=GET_CONTENT&media_type=homevideos"
    )
    add_menu_directory_item(
        view_name + string_load(30268) + " (" + show_x_filtered_items + ")", url
    )

    xbmcplugin.endOfDirectory(handle)


def display_addon_menu(_params: dict[str, str]) -> None:
    add_menu_directory_item(
        string_load(30246), "plugin://plugin.video.embycon/?mode=SEARCH"
    )
    add_menu_directory_item(
        string_load(30017), "plugin://plugin.video.embycon/?mode=SHOW_SERVER_SESSIONS"
    )
    add_menu_directory_item(
        string_load(30012), "plugin://plugin.video.embycon/?mode=CHANGE_USER"
    )
    add_menu_directory_item(
        "Show Users", "plugin://plugin.video.embycon/?mode=SHOW_USERS"
    )
    add_menu_directory_item(
        string_load(30011), "plugin://plugin.video.embycon/?mode=DETECT_SERVER_USER"
    )
    add_menu_directory_item(
        string_load(30435),
        "plugin://plugin.video.embycon/?mode=DETECT_CONNECTION_SPEED",
    )
    add_menu_directory_item(
        string_load(30254), "plugin://plugin.video.embycon/?mode=SHOW_SETTINGS"
    )
    add_menu_directory_item(
        string_load(30395), "plugin://plugin.video.embycon/?mode=CLEAR_CACHE"
    )
    add_menu_directory_item(
        string_load(30293), "plugin://plugin.video.embycon/?mode=CACHE_ARTWORK"
    )
    add_menu_directory_item(
        "List Performance Profiles",
        "plugin://plugin.video.embycon/?mode=LIST_AVAILABLE_PROFILES",
    )
    add_menu_directory_item(
        "Clone default skin", "plugin://plugin.video.embycon/?mode=CLONE_SKIN"
    )

    handle = int(sys.argv[1])
    xbmcplugin.endOfDirectory(handle)


def display_tvshow_type(_menu_params: dict[str, str], view: dict[str, str]) -> None:
    handle = int(sys.argv[1])

    view_name = string_load(30261)
    if view is not None:
        view_name = view.get("Name", view_name)

    settings = xbmcaddon.Addon()
    show_x_filtered_items = settings.getSetting("show_x_filtered_items")

    # All TV Shows
    base_params: dict[str, object] = {}
    if view is not None:
        base_params["ParentId"] = view.get("Id")
    base_params["Fields"] = "{field_filters}"
    base_params["ImageTypeLimit"] = 1
    base_params["IsMissing"] = False
    base_params["IncludeItemTypes"] = "Series"
    base_params["Recursive"] = True
    path = get_emby_url("{server}/emby/Users/{userid}/Items", base_params)
    url = (
        sys.argv[0]
        + "?url="
        + urllib.parse.quote(path)
        + "&mode=GET_CONTENT&media_type=tvshows"
    )
    add_menu_directory_item(view_name + string_load(30405), url)

    # Favorite TV Shows
    params: dict[str, object] = {}
    params.update(base_params)
    params["Filters"] = "IsFavorite"
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = (
        sys.argv[0]
        + "?url="
        + urllib.parse.quote(path)
        + "&mode=GET_CONTENT&media_type=tvshows"
    )
    add_menu_directory_item(view_name + string_load(30414), url)

    # Tv Shows with unplayed
    params: dict[str, object] = {}
    params.update(base_params)
    params["IsPlayed"] = False
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = (
        sys.argv[0]
        + "?url="
        + urllib.parse.quote(path)
        + "&mode=GET_CONTENT&media_type=tvshows"
    )
    add_menu_directory_item(view_name + string_load(30285), url)

    # In progress episodes
    params: dict[str, object] = {}
    params.update(base_params)
    params["Limit"] = "{ItemLimit}"
    params["SortBy"] = "DatePlayed"
    params["SortOrder"] = "Descending"
    params["Filters"] = "IsResumable"
    params["IncludeItemTypes"] = "Episode"
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = (
        sys.argv[0]
        + "?url="
        + urllib.parse.quote(path)
        + "&mode=GET_CONTENT&media_type=Episodes&sort=none"
    )
    url += "&name_format=" + urllib.parse.quote("Episode|episode_name_format")
    add_menu_directory_item(
        view_name + string_load(30267) + " (" + show_x_filtered_items + ")", url
    )

    # Latest Episodes
    params: dict[str, object] = {}
    params.update(base_params)
    params["Limit"] = "{ItemLimit}"
    params["SortBy"] = "DateCreated"
    params["SortOrder"] = "Descending"
    params["IncludeItemTypes"] = "Episode"
    path = get_emby_url("{server}/emby/Users/{userid}/Items/Latest", params)
    url = (
        sys.argv[0]
        + "?url="
        + urllib.parse.quote(path)
        + "&mode=GET_CONTENT&media_type=tvshows&sort=none"
    )
    add_menu_directory_item(
        view_name + string_load(30288) + " (" + show_x_filtered_items + ")", url
    )

    # Recently Added
    params: dict[str, object] = {}
    params.update(base_params)
    params["Limit"] = "{ItemLimit}"
    params["SortBy"] = "DateCreated"
    params["SortOrder"] = "Descending"
    params["Filters"] = "IsNotFolder"
    params["IncludeItemTypes"] = "Episode"
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = (
        sys.argv[0]
        + "?url="
        + urllib.parse.quote(path)
        + "&mode=GET_CONTENT&media_type=Episodes&sort=none"
    )
    url += "&name_format=" + urllib.parse.quote("Episode|episode_name_format")
    add_menu_directory_item(
        view_name + string_load(30268) + " (" + show_x_filtered_items + ")", url
    )

    # Next Up Episodes
    params: dict[str, object] = {}
    params.update(base_params)
    params["Limit"] = "{ItemLimit}"
    params["Userid"] = "{userid}"
    params["SortBy"] = "DateCreated"
    params["SortOrder"] = "Descending"
    params["Filters"] = "IsNotFolder"
    params["IncludeItemTypes"] = "Episode"
    params["Legacynextup"] = "true"
    path = get_emby_url("{server}/emby/Shows/NextUp", params)
    url = (
        sys.argv[0]
        + "?url="
        + urllib.parse.quote(path)
        + "&mode=GET_CONTENT&media_type=Episodes&sort=none"
    )
    url += "&name_format=" + urllib.parse.quote("Episode|episode_name_format")
    add_menu_directory_item(
        view_name + string_load(30278) + " (" + show_x_filtered_items + ")", url
    )

    # TV Show Genres
    path = "plugin://plugin.video.embycon/?mode=GENRES&item_type=tvshow"
    if view is not None:
        path += "&parent_id=" + view.get("Id", "none")
    add_menu_directory_item(view_name + string_load(30325), path)

    # TV Show Alpha picker
    path = "plugin://plugin.video.embycon/?mode=TVSHOW_ALPHA"
    if view is not None:
        path += "&parent_id=" + view.get("Id", "none")
    add_menu_directory_item(view_name + string_load(30404), path)

    # Tv Show Pages
    path = "plugin://plugin.video.embycon/?mode=TVSHOW_PAGES"
    if view is not None:
        path += "&parent_id=" + view.get("Id", "none")
    add_menu_directory_item(view_name + string_load(30397), path)

    xbmcplugin.endOfDirectory(handle)


def display_music_type(_menu_params: dict[str, str], view: dict[str, str]) -> None:
    handle = int(sys.argv[1])
    view_name = view.get("Name", "Unknown")

    settings = xbmcaddon.Addon()
    show_x_filtered_items = settings.getSetting("show_x_filtered_items")

    # all albums
    params: dict[str, object] = {}
    params["ParentId"] = view.get("Id")
    params["Recursive"] = True
    params["ImageTypeLimit"] = 1
    params["IncludeItemTypes"] = "MusicAlbum"
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = (
        sys.argv[0]
        + "?url="
        + urllib.parse.quote(path)
        + "&mode=GET_CONTENT&media_type=MusicAlbums"
    )
    add_menu_directory_item(view_name + string_load(30320), url)

    # recently added
    params: dict[str, object] = {}
    params["ParentId"] = view.get("Id")
    params["ImageTypeLimit"] = 1
    params["IncludeItemTypes"] = "Audio"
    params["Limit"] = "{ItemLimit}"
    path = get_emby_url("{server}/emby/Users/{userid}/Items/Latest", params)
    url = (
        sys.argv[0]
        + "?url="
        + urllib.parse.quote(path)
        + "&mode=GET_CONTENT&media_type=MusicAlbums"
    )
    add_menu_directory_item(
        view_name + string_load(30268) + " (" + show_x_filtered_items + ")", url
    )

    # recently played
    params: dict[str, object] = {}
    params["ParentId"] = view.get("Id")
    params["Recursive"] = True
    params["ImageTypeLimit"] = 1
    params["IncludeItemTypes"] = "Audio"
    params["Limit"] = "{ItemLimit}"
    params["IsPlayed"] = True
    params["SortBy"] = "DatePlayed"
    params["SortOrder"] = "Descending"
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = (
        sys.argv[0]
        + "?url="
        + urllib.parse.quote(path)
        + "&mode=GET_CONTENT&media_type=MusicAlbum"
    )
    add_menu_directory_item(
        view_name + string_load(30349) + " (" + show_x_filtered_items + ")", url
    )

    # most played
    params: dict[str, object] = {}
    params["ParentId"] = view.get("Id")
    params["Recursive"] = True
    params["ImageTypeLimit"] = 1
    params["IncludeItemTypes"] = "Audio"
    params["Limit"] = "{ItemLimit}"
    params["IsPlayed"] = True
    params["SortBy"] = "PlayCount"
    params["SortOrder"] = "Descending"
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = (
        sys.argv[0]
        + "?url="
        + urllib.parse.quote(path)
        + "&mode=GET_CONTENT&media_type=MusicAlbum"
    )
    add_menu_directory_item(
        view_name + string_load(30353) + " (" + show_x_filtered_items + ")", url
    )

    # artists
    params: dict[str, object] = {}
    params["ParentId"] = view.get("Id")
    params["Recursive"] = True
    params["ImageTypeLimit"] = 1
    path = get_emby_url("{server}/emby/Artists/AlbumArtists", params)
    url = (
        sys.argv[0]
        + "?url="
        + urllib.parse.quote(path)
        + "&mode=GET_CONTENT&media_type=MusicArtists"
    )
    add_menu_directory_item(view_name + string_load(30321), url)

    xbmcplugin.endOfDirectory(handle)


def display_musicvideos_type(
    _menu_params: dict[str, str], view: dict[str, str]
) -> None:
    handle = int(sys.argv[1])
    xbmcplugin.setContent(handle, "files")

    view_name = view.get("Name", "Unknown")
    # artists
    base_params: dict[str, object] = {}
    base_params["ParentId"] = view.get("Id", "none")
    base_params["Recursive"] = False
    base_params["ImageTypeLimit"] = 1
    base_params["IsMissing"] = False
    base_params["Fields"] = "{field_filters}"
    path = get_emby_url("{server}/emby/Users/{userid}/Items", base_params)
    url = (
        sys.argv[0]
        + "?url="
        + urllib.parse.quote(path)
        + "&mode=GET_CONTENT&media_type=musicvideos"
    )
    add_menu_directory_item(view_name + string_load(30405), url)

    xbmcplugin.endOfDirectory(handle)


def display_livetv_type(_menu_params: dict[str, str], view: dict[str, str]) -> None:
    handle = int(sys.argv[1])
    xbmcplugin.setContent(handle, "files")

    view_name = view.get("Name", "Unknown")

    # channels
    params: dict[str, object] = {}
    params["UserId"] = "{userid}"
    params["Recursive"] = False
    params["ImageTypeLimit"] = 1
    params["Fields"] = "{field_filters}"
    path = get_emby_url("{server}/emby/LiveTv/Channels", params)
    url = (
        sys.argv[0]
        + "?url="
        + urllib.parse.quote(path)
        + "&mode=GET_CONTENT&media_type=livetv"
    )
    add_menu_directory_item(view_name + string_load(30360), url)

    # programs
    params = {}
    params["UserId"] = "{userid}"
    params["IsAiring"] = True
    params["ImageTypeLimit"] = 1
    params["Fields"] = "ChannelInfo,{field_filters}"
    params["EnableTotalRecordCount"] = False
    path = get_emby_url("{server}/emby/LiveTv/Programs/Recommended", params)
    url = (
        sys.argv[0]
        + "?url="
        + urllib.parse.quote(path)
        + "&mode=GET_CONTENT&media_type=livetv"
    )
    add_menu_directory_item(view_name + string_load(30361), url)

    # recordings
    params = {}
    params["UserId"] = "{userid}"
    params["Recursive"] = False
    params["ImageTypeLimit"] = 1
    params["Fields"] = "{field_filters}"
    params["EnableTotalRecordCount"] = False
    path = get_emby_url("{server}/emby/LiveTv/Recordings", params)
    url = (
        sys.argv[0]
        + "?url="
        + urllib.parse.quote(path)
        + "&mode=GET_CONTENT&media_type=livetv"
    )
    add_menu_directory_item(view_name + string_load(30362), url)

    xbmcplugin.endOfDirectory(handle)


def display_movies_type(_menu_params: dict[str, str], view: dict[str, str]) -> None:
    handle = int(sys.argv[1])
    xbmcplugin.setContent(handle, "files")

    view_name = string_load(30256)
    if view is not None:
        view_name = view.get("Name", view_name)

    settings = xbmcaddon.Addon()
    show_x_filtered_items = settings.getSetting("show_x_filtered_items")
    group_movies = settings.getSetting("group_movies") == "true"
    hide_watched = settings.getSetting("hide_watched") == "true"

    base_params: dict[str, object] = {}
    if view is not None:
        base_params["ParentId"] = view.get("Id")
    base_params["IncludeItemTypes"] = "Movie"
    base_params["CollapseBoxSetItems"] = str(group_movies)
    base_params["GroupItemsIntoCollections"] = str(group_movies)
    base_params["Recursive"] = True
    base_params["IsMissing"] = False
    base_params["Fields"] = "{field_filters}"
    base_params["ImageTypeLimit"] = 1

    # All Movies
    path = get_emby_url("{server}/emby/Users/{userid}/Items", base_params)
    url = (
        sys.argv[0]
        + "?url="
        + urllib.parse.quote(path)
        + "&mode=GET_CONTENT&media_type=movies"
    )
    add_menu_directory_item(view_name + string_load(30405), url)

    # Favorite Movies
    params: dict[str, object] = {}
    params.update(base_params)
    params["CollapseBoxSetItems"] = False
    params["GroupItemsIntoCollections"] = False
    params["Filters"] = "IsFavorite"
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = (
        sys.argv[0]
        + "?url="
        + urllib.parse.quote(path)
        + "&mode=GET_CONTENT&media_type=movies"
    )
    add_menu_directory_item(view_name + string_load(30414), url)

    # Unwatched Movies
    params: dict[str, object] = {}
    params.update(base_params)
    params["CollapseBoxSetItems"] = False
    params["GroupItemsIntoCollections"] = False
    params["IsPlayed"] = False
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = (
        sys.argv[0]
        + "?url="
        + urllib.parse.quote(path)
        + "&mode=GET_CONTENT&media_type=movies"
    )
    add_menu_directory_item(view_name + string_load(30285), url)

    # Recently Watched Movies
    params: dict[str, object] = {}
    params.update(base_params)
    params["IsPlayed"] = True
    params["SortBy"] = "DatePlayed"
    params["SortOrder"] = "Descending"
    params["CollapseBoxSetItems"] = False
    params["GroupItemsIntoCollections"] = False
    params["Limit"] = "{ItemLimit}"
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = (
        sys.argv[0]
        + "?url="
        + urllib.parse.quote(path)
        + "&mode=GET_CONTENT&media_type=movies&sort=none"
    )
    add_menu_directory_item(
        view_name + string_load(30349) + " (" + show_x_filtered_items + ")", url
    )

    # Resumable Movies
    params: dict[str, object] = {}
    params.update(base_params)
    params["Filters"] = "IsResumable"
    params["SortBy"] = "DatePlayed"
    params["SortOrder"] = "Descending"
    params["Limit"] = "{ItemLimit}"
    params["CollapseBoxSetItems"] = False
    params["GroupItemsIntoCollections"] = False
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = (
        sys.argv[0]
        + "?url="
        + urllib.parse.quote(path)
        + "&mode=GET_CONTENT&media_type=movies&sort=none"
    )
    add_menu_directory_item(
        view_name + string_load(30267) + " (" + show_x_filtered_items + ")", url
    )

    # Recently Added Movies
    params: dict[str, object] = {}
    params.update(base_params)
    if hide_watched:
        params["IsPlayed"] = False
    params["SortBy"] = "DateCreated"
    params["SortOrder"] = "Descending"
    params["Filters"] = "IsNotFolder"
    params["Limit"] = "{ItemLimit}"
    params["CollapseBoxSetItems"] = False
    params["GroupItemsIntoCollections"] = False
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = (
        sys.argv[0]
        + "?url="
        + urllib.parse.quote(path)
        + "&mode=GET_CONTENT&media_type=movies&sort=none"
    )
    add_menu_directory_item(
        view_name + string_load(30268) + " (" + show_x_filtered_items + ")", url
    )

    # Collections
    params: dict[str, object] = {}
    if view is not None:
        params["ParentId"] = view.get("Id")
    params["Fields"] = "{field_filters}"
    params["ImageTypeLimit"] = 1
    params["IncludeItemTypes"] = "Boxset"
    params["Recursive"] = True
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = (
        sys.argv[0]
        + "?url="
        + urllib.parse.quote(path)
        + "&mode=GET_CONTENT&media_type=boxsets"
    )
    add_menu_directory_item(view_name + string_load(30410), url)

    # Favorite Collections
    params["Filters"] = "IsFavorite"
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = (
        sys.argv[0]
        + "?url="
        + urllib.parse.quote(path)
        + "&mode=GET_CONTENT&media_type=boxsets"
    )
    add_menu_directory_item(view_name + string_load(30415), url)

    # Genres
    path = "plugin://plugin.video.embycon/?mode=GENRES&item_type=movie"
    if view is not None:
        path += "&parent_id=" + view.get("Id", "none")
    add_menu_directory_item(view_name + string_load(30325), path)

    # Pages
    path = "plugin://plugin.video.embycon/?mode=MOVIE_PAGES"
    if view is not None:
        path += "&parent_id=" + view.get("Id", "none")
    add_menu_directory_item(view_name + string_load(30397), path)

    # Alpha Picker
    path = "plugin://plugin.video.embycon/?mode=MOVIE_ALPHA"
    if view is not None:
        path += "&parent_id=" + view.get("Id", "none")
    add_menu_directory_item(view_name + string_load(30404), path)

    # Years
    path = "plugin://plugin.video.embycon/?mode=SHOW_ADDON_MENU&type=show_movie_years"
    if view is not None:
        path += "&parent_id=" + view.get("Id", "none")
    add_menu_directory_item(view_name + string_load(30411), path)

    # Decades
    path = "plugin://plugin.video.embycon/?mode=SHOW_ADDON_MENU&type=show_movie_years&group=true"
    if view is not None:
        path += "&parent_id=" + view.get("Id", "none")
    add_menu_directory_item(view_name + string_load(30412), path)

    # Tags
    path = "plugin://plugin.video.embycon/?mode=SHOW_ADDON_MENU&type=show_movie_tags"
    if view is not None:
        path += "&parent_id=" + view.get("Id", "none")
    add_menu_directory_item(view_name + string_load(30413), path)

    xbmcplugin.endOfDirectory(handle)


def display_library_views(_params: dict[str, str]) -> None:
    handle = int(sys.argv[1])
    xbmcplugin.setContent(handle, "files")

    download_utils = DownloadUtils()
    server = download_utils.get_server()
    if server is None:
        return

    settings = xbmcaddon.Addon()
    max_image_width = int(settings.getSetting("max_image_width"))

    data_manager = DataManager()
    views_url = "{server}/emby/Users/{userid}/Views?format=json"
    views = data_manager.get_content(views_url)
    if not views:
        return
    views = views.get("Items", [])

    view_types = [
        "movies",
        "tvshows",
        "homevideos",
        "boxsets",
        "playlists",
        "music",
        "musicvideos",
        "livetv",
        "Channel",
    ]

    for view in views:
        collection_type = view.get("CollectionType", None)
        item_type = view.get("Type", None)
        if collection_type in view_types or item_type == "Channel":
            view_name = view.get("Name")
            art = get_art(
                item=view,
                server=server,
                maxwidth=max_image_width,
                download_utils=download_utils,
            )
            art["landscape"] = download_utils.get_artwork(
                view, "Primary", server=server, maxwidth=max_image_width
            )

            plugin_path = (
                "plugin://plugin.video.embycon/?mode=SHOW_ADDON_MENU&type=library_item&view_id="
                + view.get("Id")
            )

            if collection_type == "playlists":
                plugin_path = get_playlist_path(view)
            elif collection_type == "boxsets":
                plugin_path = get_collection_path(view)
            elif collection_type is None and view.get("Type", None) == "Channel":
                plugin_path = get_channel_path(view)

            add_menu_directory_item(view_name, plugin_path, art=art)

    xbmcplugin.endOfDirectory(handle)


def get_playlist_path(view_info: dict[str, object]) -> str:
    params: dict[str, object] = {}
    params["ParentId"] = view_info.get("Id")
    params["Fields"] = "{field_filters}"
    params["ImageTypeLimit"] = 1

    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    return "%s?url=%s&mode=GET_CONTENT&media_type=playlists" % (
        sys.argv[0],
        urllib.parse.quote(path),
    )


def get_collection_path(view_info: dict[str, object]) -> str:
    params: dict[str, object] = {}
    params["ParentId"] = view_info.get("Id")
    params["Fields"] = "{field_filters}"
    params["ImageTypeLimit"] = 1
    params["IncludeItemTypes"] = "Boxset"
    params["CollapseBoxSetItems"] = True
    params["GroupItemsIntoCollections"] = True
    params["Recursive"] = True
    params["IsMissing"] = False

    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    return "%s?url=%s&mode=GET_CONTENT&media_type=boxsets" % (
        sys.argv[0],
        urllib.parse.quote(path),
    )


def get_channel_path(view: dict[str, object]) -> str:
    params: dict[str, object] = {}
    params["ParentId"] = view.get("Id")
    params["IsMissing"] = False
    params["ImageTypeLimit"] = 1
    params["Fields"] = "{field_filters}"

    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    return "%s?url=%s&mode=GET_CONTENT&media_type=files" % (
        sys.argv[0],
        urllib.parse.quote(path),
    )


def display_library_view(params: dict[str, str]) -> None:
    node_id = params.get("view_id", "none")

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
    settings: xbmcaddon.Addon = xbmcaddon.Addon()
    show_x_filtered_items = settings.getSetting("show_x_filtered_items")

    add_menu_directory_item(
        "All Movies",
        "plugin://plugin.video.embycon/?mode=SHOW_CONTENT&item_type=movie&media_type=movies",
    )

    add_menu_directory_item(
        "All Shows",
        "plugin://plugin.video.embycon/?mode=SHOW_CONTENT&item_type=series&media_type=tvshows",
    )

    add_menu_directory_item(
        string_load(30257) + " (" + show_x_filtered_items + ")",
        "plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=recent_movies",
    )
    add_menu_directory_item(
        string_load(30258) + " (" + show_x_filtered_items + ")",
        "plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=inprogress_movies",
    )
    add_menu_directory_item(
        string_load(30269) + " (" + show_x_filtered_items + ")",
        "plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=random_movies",
    )
    add_menu_directory_item(
        string_load(30403) + " (" + show_x_filtered_items + ")",
        "plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=movie_recommendations",
    )

    add_menu_directory_item(
        string_load(30287) + " (" + show_x_filtered_items + ")",
        "plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=recent_tvshows",
    )
    add_menu_directory_item(
        string_load(30263) + " (" + show_x_filtered_items + ")",
        "plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=recent_episodes",
    )
    add_menu_directory_item(
        string_load(30264) + " (" + show_x_filtered_items + ")",
        "plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=inprogress_episodes",
    )
    add_menu_directory_item(
        string_load(30265) + " (" + show_x_filtered_items + ")",
        "plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=nextup_episodes",
    )

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def show_search() -> None:
    add_menu_directory_item(
        string_load(30231),
        "plugin://plugin.video.embycon/?mode=NEW_SEARCH&item_type=Movie",
    )
    add_menu_directory_item(
        string_load(30229),
        "plugin://plugin.video.embycon/?mode=NEW_SEARCH&item_type=Series",
    )
    add_menu_directory_item(
        string_load(30235),
        "plugin://plugin.video.embycon/?mode=NEW_SEARCH&item_type=Episode",
    )
    add_menu_directory_item(
        string_load(30337),
        "plugin://plugin.video.embycon/?mode=NEW_SEARCH&item_type=Audio",
    )
    add_menu_directory_item(
        string_load(30338),
        "plugin://plugin.video.embycon/?mode=NEW_SEARCH&item_type=MusicAlbum",
    )
    add_menu_directory_item(
        string_load(30339),
        "plugin://plugin.video.embycon/?mode=NEW_SEARCH&item_type=Person",
    )

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def set_library_window_values(force: bool = False) -> None:
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

    result = result.get("Items", [])
    download_utils = DownloadUtils()
    server = download_utils.get_server()

    settings: xbmcaddon.Addon = xbmcaddon.Addon()
    max_image_width = int(settings.getSetting("max_image_width"))

    index = 0
    for item in result:
        collection_type = item.get("CollectionType")
        if collection_type in ["movies", "boxsets", "music", "tvshows"]:
            name = item.get("Name")
            item_id = item.get("Id")

            # plugin.video.embycon-
            prop_name = "view_item.%i.name" % index
            home_window.set_property(prop_name, name)
            log.debug(
                "set_library_window_values: plugin.video.embycon-{0}={1}",
                prop_name,
                name,
            )

            prop_name = "view_item.%i.id" % index
            home_window.set_property(prop_name, item_id)
            log.debug(
                "set_library_window_values: plugin.video.embycon-{0}={1}",
                prop_name,
                item_id,
            )

            prop_name = "view_item.%i.type" % index
            home_window.set_property(prop_name, collection_type)
            log.debug(
                "set_library_window_values: plugin.video.embycon-{0}={1}",
                prop_name,
                collection_type,
            )

            thumb = download_utils.get_artwork(
                item, "Primary", server=server, maxwidth=max_image_width
            )
            prop_name = "view_item.%i.thumb" % index
            home_window.set_property(prop_name, thumb)
            log.debug(
                "set_library_window_values: plugin.video.embycon-{0}={1}",
                prop_name,
                thumb,
            )

            index += 1
