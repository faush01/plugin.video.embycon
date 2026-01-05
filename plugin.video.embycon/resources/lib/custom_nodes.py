from __future__ import annotations
import os
import json
from typing import cast

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

from .datamanager import DataManager
from .simple_logging import SimpleLogging

log = SimpleLogging(__name__)

"""
&reload=$INFO[Window(Home).Property(plugin.video.embycon-embycon_widget_reload)]

Node types :

Resume ({server}/emby/Users/c3d953c03c084d71a8ecbbf9d6e865fc/Items/Resume)

Latest ({server}/emby/Users/{userid}/Items/Latest)
- Limit (item count)
- SortBy (DateCreated)
- SortOrder (Descending)
- IncludeItemTypes (Episode)

NextUp ({server}/emby/Shows/NextUp)
- Legacynextup (True, False)
- Limit (item count)
- SortBy (DateCreated)
- SortOrder (Descending)
- IncludeItemTypes (Episode)
- media_type (Episodes)

Items ({server}/emby/Users/{userid}/Items)
- IncludeItemTypes (Movie, Boxset, Series, Episode, MusicAlbum, Audio)
- Limit (item count int)
- Recursive (True, False)
- ParentId (GUID)
- GroupItemsIntoCollections & CollapseBoxSetItems (True, False)
- IsPlayed (False, True)
- Filters (IsResumable, IsNotFolder)

- SortBy (DatePlayed, DateCreated, PlayCount)
- SortOrder (Descending, )

- IsFavorite
- Fields (DateCreated,EpisodeCount,SeasonCount,Path,Genres,Studios,Etag,Taglines,SortName,RecursiveItemCount,ChildCount,ProductionLocations,CriticRating,OfficialRating,CommunityRating,PremiereDate,ProductionYear,AirTime,Status,Tags,MediaStreams,Overview)
- IsMissing

- media_type (movies, tvshows, homevideos, Episodes, MusicAlbums, MusicArtists, musicvideos, boxsets)
- sort
- use cache
"""


def get_view_list() -> dict[str, dict[str, str]]:
    data_manager = DataManager()
    views_url = "{server}/emby/Users/{userid}/Views?format=json"
    views = data_manager.get_content(views_url)
    if not views:
        return {"name": {}, "id": {}}
    views = views.get("Items")
    if not views:
        return {"name": {}, "id": {}}

    view_list_id = {}
    view_list_name = {}
    for view in views:
        view_id = view.get("Id")
        view_name = view.get("Name")
        view_list_id[view_id] = view_name
        view_list_name[view_name] = view_id

    view_list = {}
    view_list["name"] = view_list_name
    view_list["id"] = view_list_id
    return view_list


def load_custom_nodes() -> dict[str, dict[str, str]]:
    log.debug("load_custom_nodes")
    addon_dir = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo("profile"))
    node_info_path = os.path.join(addon_dir, "custom_nodes.json")
    if xbmcvfs.exists(node_info_path):
        log.debug("custom_nodes.json : Exists")
        with open(node_info_path) as json_file:
            custom_nodes = json.load(json_file)
            log.debug("custom_nodes.json Loaded : {0}", custom_nodes)
            return custom_nodes
    else:
        log.debug("custom_nodes.json : Does not exist ({0})", node_info_path)
        return {}


def add_custom_node(
    existing_name: str | None, new_name: str | None, node_info: dict | None
) -> None:
    log.debug("add_custom_node")
    custom_nodes = load_custom_nodes()

    if existing_name is not None:
        del custom_nodes[existing_name]

    if new_name is not None and node_info is not None:
        custom_nodes[new_name] = node_info

    addon_dir = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo("profile"))
    node_info_path = os.path.join(addon_dir, "custom_nodes.json")
    with open(node_info_path, "w") as outfile:
        json.dump(custom_nodes, outfile)


class CustomNode(xbmcgui.WindowXMLDialog):
    view_list_lookup: dict[str, dict[str, str]] | None = None

    def __init__(
        self, xmlFilename: str, scriptPath: str, defaultSkin: str, defaultRes: str
    ) -> None:
        log.debug("CustomNode: __init__")
        super(CustomNode, self).__init__(
            xmlFilename, scriptPath, defaultSkin, defaultRes
        )

    def onInit(self) -> None:
        log.debug("CustomNode: onInit")
        self.action_exitkeys_id = [10, 13]

        self.view_list_lookup = get_view_list()
        log.debug("view_list_lookup : {0}", self.view_list_lookup)

    def onFocus(self, controlId: int) -> None:
        pass

    def onAction(self, action: xbmcgui.Action) -> None:
        if action.getId() == 10:  # ACTION_PREVIOUS_MENU
            self.close()
        elif action.getId() == 92:  # ACTION_NAV_BACK
            self.close()

    def show_setting_for_select(
        self, control_id: int, option_list: list[str | xbmcgui.ListItem]
    ) -> int:
        control = cast(xbmcgui.ControlLabel, self.getControl(control_id))
        current_value: str = control.getLabel()
        selected_id: int = 0
        if current_value in option_list:
            selected_id = option_list.index(current_value)
        return_index = xbmcgui.Dialog().select(
            "Select Value",
            option_list,
            preselect=selected_id,
        )
        if return_index > -1:
            new_setting: str | xbmcgui.ListItem = option_list[return_index]
            if isinstance(new_setting, xbmcgui.ListItem):
                new_setting = new_setting.getLabel()
            control.setLabel(new_setting)
        return return_index

    def show_setting_for_select_multi(
        self, control_id: int, option_list: list[str | xbmcgui.ListItem]
    ) -> int:
        control = cast(xbmcgui.ControlLabel, self.getControl(control_id))
        current_value = control.getLabel()
        types = current_value.split(",")
        selected = []

        for index in range(0, len(option_list)):
            if option_list[index] in types:
                selected.append(index)
        return_indexes = xbmcgui.Dialog().multiselect(
            "Select Value",
            option_list,
            preselect=selected,
        )

        if return_indexes is not None:
            type_list = []
            for selected_index in return_indexes:
                type_list.append(option_list[selected_index])
            control.setLabel(",".join(type_list))
            return len(return_indexes)

        return 0

    def set_label_on_item(
        self,
        controlId: int,
        option_list: list[str | xbmcgui.ListItem],
        selected_id: int,
    ) -> None:
        control = cast(xbmcgui.ControlButton, self.getControl(controlId))
        new_setting: str | xbmcgui.ListItem = option_list[selected_id]
        if isinstance(new_setting, xbmcgui.ListItem):
            new_setting = new_setting.getLabel()
        control.setLabel(new_setting)

    def set_label_on_item_multi(
        self,
        controlId: int,
        current_nodes: dict[str, dict[str, str]],
        option_list: list[str | xbmcgui.ListItem],
        selected_indexes: int,
        value_type: str,
    ) -> None:
        control = cast(xbmcgui.ControlButton, self.getControl(controlId))
        selected_item: str | xbmcgui.ListItem = option_list[selected_indexes]
        if isinstance(selected_item, xbmcgui.ListItem):
            selected_item = selected_item.getLabel()
        value_to_set: str = current_nodes[selected_item].get(value_type, "")
        control.setLabel(value_to_set)

    def onClick(self, controlId: int) -> None:
        log.debug("CustomNode: control_id: {0}", controlId)
        if controlId == 3000:
            self.close()

        elif controlId == 3153:
            current_nodes = load_custom_nodes()
            option_list: list[str | xbmcgui.ListItem] = ["New Node"]
            for node_name in current_nodes:
                option_list.append(node_name)
            resp = self.show_setting_for_select(3153, option_list)
            if resp > 0:
                self.set_label_on_item(3154, option_list, resp)
                self.set_label_on_item_multi(
                    3155, current_nodes, option_list, resp, "item_type"
                )
                self.set_label_on_item_multi(
                    3156, current_nodes, option_list, resp, "item_limit"
                )
                self.set_label_on_item_multi(
                    3158, current_nodes, option_list, resp, "recursive"
                )
                self.set_label_on_item_multi(
                    3159, current_nodes, option_list, resp, "group"
                )
                self.set_label_on_item_multi(
                    3160, current_nodes, option_list, resp, "watched"
                )
                self.set_label_on_item_multi(
                    3161, current_nodes, option_list, resp, "inprogress"
                )
                self.set_label_on_item_multi(
                    3162, current_nodes, option_list, resp, "sortby"
                )
                self.set_label_on_item_multi(
                    3163, current_nodes, option_list, resp, "sortorder"
                )
                self.set_label_on_item_multi(
                    3164, current_nodes, option_list, resp, "kodi_media_type"
                )
                self.set_label_on_item_multi(
                    3165, current_nodes, option_list, resp, "kodi_sort"
                )
                self.set_label_on_item_multi(
                    3166, current_nodes, option_list, resp, "use_cache"
                )

                sel_item: str | xbmcgui.ListItem = option_list[resp]
                if isinstance(sel_item, xbmcgui.ListItem):
                    sel_item = sel_item.getLabel()
                parent_id = current_nodes[sel_item].get("item_parent", "")
                if parent_id and self.view_list_lookup is not None:
                    view_name = self.view_list_lookup["id"].get(parent_id, parent_id)
                    cast(xbmcgui.ControlButton, self.getControl(3157)).setLabel(
                        view_name
                    )

        elif controlId == 3154:
            control = cast(xbmcgui.ControlButton, self.getControl(3154))
            current_value = control.getLabel()
            kb = xbmc.Keyboard()
            kb.setHeading("Set Node Name")
            kb.setDefault(current_value)
            kb.doModal()
            if kb.isConfirmed():
                new_node_name = kb.getText().strip()
                control.setLabel(new_node_name)

        elif controlId == 3155:
            option_list = [
                "Movie",
                "Boxset",
                "Series",
                "Episode",
                "MusicAlbum",
                "Audio",
            ]
            self.show_setting_for_select_multi(3155, option_list)

        elif controlId == 3156:
            control = cast(xbmcgui.ControlButton, self.getControl(3156))
            current_value = control.getLabel()
            set_value = xbmcgui.Dialog().numeric(0, "Set Value", current_value)
            control.setLabel(set_value)

        elif controlId == 3157 and self.view_list_lookup is not None:
            view_names = self.view_list_lookup["name"]
            option_list = ["None"]
            for name in view_names:
                option_list.append(name)
            self.show_setting_for_select(3157, option_list)

        elif controlId == 3158:
            control = cast(xbmcgui.ControlButton, self.getControl(3158))
            current_value = control.getLabel()
            if current_value == "True":
                control.setLabel("False")
            else:
                control.setLabel("True")

        elif controlId == 3159:
            control = cast(xbmcgui.ControlButton, self.getControl(3159))
            current_value = control.getLabel()
            if current_value == "True":
                control.setLabel("False")
            else:
                control.setLabel("True")

        elif controlId == 3160:
            control = cast(xbmcgui.ControlButton, self.getControl(3160))
            current_value = control.getLabel()
            if current_value == "True":
                control.setLabel("False")
            elif current_value == "False":
                control.setLabel(" ")
            elif current_value == " " or current_value == "":
                control.setLabel("True")

        elif controlId == 3161:
            control = cast(xbmcgui.ControlButton, self.getControl(3161))
            current_value = control.getLabel()
            if current_value == "True":
                control.setLabel(" ")
            else:
                control.setLabel("True")

        elif controlId == 3162:
            # Album, AlbumArtist, Artist, Budget, CommunityRating, CriticRating, DateCreated, DatePlayed,
            # PlayCount, PremiereDate, ProductionYear, SortName, Random, Revenue, Runtime
            option_list = [
                "None",
                "DatePlayed",
                "DateCreated",
                "PlayCount",
                "ProductionYear",
                "PremiereDate",
            ]
            self.show_setting_for_select(3162, option_list)

        elif controlId == 3163:
            option_list = ["Descending", "Ascending"]
            self.show_setting_for_select(3163, option_list)

        elif controlId == 3164:
            option_list = [
                "movies",
                "tvshows",
                "homevideos",
                "episodes",
                "musicalbums",
                "musicartists",
                "musicvideos",
                "boxsets",
            ]
            self.show_setting_for_select(3164, option_list)

        elif controlId == 3165:
            control = cast(xbmcgui.ControlButton, self.getControl(3165))
            current_value = control.getLabel()
            if current_value == "True":
                control.setLabel("False")
            else:
                control.setLabel("True")

        elif controlId == 3166:
            control = cast(xbmcgui.ControlButton, self.getControl(3166))
            current_value = control.getLabel()
            if current_value == "True":
                control.setLabel("False")
            else:
                control.setLabel("True")

        elif controlId == 3180:
            existing_name = cast(
                xbmcgui.ControlButton, self.getControl(3153)
            ).getLabel()
            if existing_name == "New Node":
                existing_name = None
            new_name = cast(xbmcgui.ControlButton, self.getControl(3154)).getLabel()
            if new_name:
                i_type = (
                    cast(xbmcgui.ControlButton, self.getControl(3155))
                    .getLabel()
                    .strip()
                )
                i_limit = (
                    cast(xbmcgui.ControlButton, self.getControl(3156))
                    .getLabel()
                    .strip()
                )
                i_parent = (
                    cast(xbmcgui.ControlButton, self.getControl(3157))
                    .getLabel()
                    .strip()
                )
                if self.view_list_lookup is not None:
                    i_parent = self.view_list_lookup["name"].get(i_parent, "").strip()
                recursive = (
                    cast(xbmcgui.ControlButton, self.getControl(3158))
                    .getLabel()
                    .strip()
                )
                group = (
                    cast(xbmcgui.ControlButton, self.getControl(3159))
                    .getLabel()
                    .strip()
                )
                watched = (
                    cast(xbmcgui.ControlButton, self.getControl(3160))
                    .getLabel()
                    .strip()
                )
                inprogress = (
                    cast(xbmcgui.ControlButton, self.getControl(3161))
                    .getLabel()
                    .strip()
                )
                sortby = (
                    cast(xbmcgui.ControlButton, self.getControl(3162))
                    .getLabel()
                    .strip()
                )
                sortorder = (
                    cast(xbmcgui.ControlButton, self.getControl(3163))
                    .getLabel()
                    .strip()
                )

                kodi_media_type = (
                    cast(xbmcgui.ControlButton, self.getControl(3164))
                    .getLabel()
                    .strip()
                )
                kodi_sort = (
                    cast(xbmcgui.ControlButton, self.getControl(3165))
                    .getLabel()
                    .strip()
                )
                use_cache = (
                    cast(xbmcgui.ControlButton, self.getControl(3166))
                    .getLabel()
                    .strip()
                )

                new_node = {
                    "item_type": i_type,
                    "item_limit": i_limit,
                    "item_parent": i_parent,
                    "recursive": recursive,
                    "group": group,
                    "watched": watched,
                    "inprogress": inprogress,
                    "sortby": sortby,
                    "sortorder": sortorder,
                    "kodi_media_type": kodi_media_type,
                    "kodi_sort": kodi_sort,
                    "use_cache": use_cache,
                }
                add_custom_node(existing_name, new_name, new_node)
            self.close()

        elif controlId == 3181:
            existing_name = cast(
                xbmcgui.ControlButton, self.getControl(3153)
            ).getLabel()
            if existing_name != "New Node":
                add_custom_node(existing_name, None, None)
            self.close()
