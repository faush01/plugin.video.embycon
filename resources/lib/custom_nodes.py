import os
import json
from typing import List, cast, Any, Dict, Union

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

from .datamanager import DataManager
from .simple_logging import SimpleLogging

log = SimpleLogging(__name__)

'''
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
'''


def get_view_list() -> Dict[str, Dict[str, str]]:

    data_manager = DataManager()
    views_url = "{server}/emby/Users/{userid}/Views?format=json"
    views = data_manager.get_content(views_url)
    if not views:
        return {"name": {}, "id": {}}
    views = views.get("Items")

    view_list_id = {}
    view_list_name = {}
    for view in views:
        view_id: str = view.get("Id")
        view_name: str = view.get("Name")
        view_list_id[view_id] = view_name
        view_list_name[view_name] = view_id

    view_list: Dict[str, Dict[str, str]] = {
        "name": view_list_name,
        "id": view_list_id
    }
    return view_list


def load_custom_nodes():
    log.debug("load_custom_nodes")
    addon_dir = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))
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


def add_custom_node(existing_name, new_name, node_info):
    log.debug("add_custom_node")
    custom_nodes = load_custom_nodes()

    if existing_name is not None:
        del custom_nodes[existing_name]

    if new_name is not None and node_info is not None:
        custom_nodes[new_name] = node_info

    addon_dir = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))
    node_info_path = os.path.join(addon_dir, "custom_nodes.json")
    with open(node_info_path, 'w') as outfile:
        json.dump(custom_nodes, outfile)


class CustomNode(xbmcgui.WindowXMLDialog):

    view_list_lookup: Dict[str, Dict[str, str]]

    def __init__(self, *args, **kwargs):
        log.debug("CustomNode: __init__")
        xbmcgui.WindowXML.__init__(self, *args, **kwargs)

    def onInit(self):
        log.debug("CustomNode: onInit")
        self.action_exitkeys_id = [10, 13]

        self.view_list_lookup = get_view_list()
        log.debug("view_list_lookup : {0}", self.view_list_lookup)

    def onFocus(self, control_id):
        pass

    def doAction(self, action_id):
        pass

    def onMessage(self, message):
        log.debug("CustomNode: onMessage: {0}", message)

    def onAction(self, action):

        if action.getId() == 10:  # ACTION_PREVIOUS_MENU
            self.close()
        elif action.getId() == 92:  # ACTION_NAV_BACK
            self.close()

    def show_setting_for_select(self, control_id: int, option_list: List[str]) -> int:
        control: xbmcgui.ControlButton = cast(xbmcgui.ControlButton, self.getControl(control_id))
        current_value: str = control.getLabel()
        selected_id: int = 0
        if current_value in option_list:
            selected_id = option_list.index(current_value)
        return_index: int = xbmcgui.Dialog().select("Select Value", option_list, preselect=selected_id)   # type: ignore
        if return_index > -1:
            new_setting: str = option_list[return_index]
            control.setLabel(new_setting)
        return return_index

    def show_setting_for_select_multi(self, control_id: int, option_list: List[str]) -> int:
        control: xbmcgui.ControlButton = cast(xbmcgui.ControlButton, self.getControl(control_id))
        current_value: str = control.getLabel()
        types: List[str] = current_value.split(",")
        selected: List[int] = []
        for index in range(0, len(option_list)):
            if option_list[index] in types:
                selected.append(index)
        return_indexes = xbmcgui.Dialog().multiselect("Select Value", option_list, preselect=selected)  # type: ignore
        if return_indexes is not None:
            type_list = []
            for selected_index in return_indexes:
                type_list.append(option_list[selected_index])
            control.setLabel(",".join(type_list))
            return len(return_indexes)
        else:
            return 0

    def onClick(self, control_id):
        log.debug("CustomNode: control_id: {0}", control_id)
        if control_id == 3000:
            self.close()

        elif control_id == 3153:
            current_nodes = load_custom_nodes()
            option_list = ["New Node"]
            for node_name in current_nodes:
                option_list.append(node_name)
            resp = self.show_setting_for_select(3153, option_list)
            if resp > 0:
                self.getControl(3154).setLabel(option_list[resp])  # type: ignore
                self.getControl(3155).setLabel(current_nodes[option_list[resp]].get("item_type", ""))  # type: ignore
                self.getControl(3156).setLabel(current_nodes[option_list[resp]].get("item_limit", ""))  # type: ignore
                self.getControl(3158).setLabel(current_nodes[option_list[resp]].get("recursive", ""))  # type: ignore
                self.getControl(3159).setLabel(current_nodes[option_list[resp]].get("group", ""))  # type: ignore
                self.getControl(3160).setLabel(current_nodes[option_list[resp]].get("watched", ""))  # type: ignore
                self.getControl(3161).setLabel(current_nodes[option_list[resp]].get("inprogress", ""))  # type: ignore
                self.getControl(3162).setLabel(current_nodes[option_list[resp]].get("sortby", ""))  # type: ignore
                self.getControl(3163).setLabel(current_nodes[option_list[resp]].get("sortorder", ""))  # type: ignore

                self.getControl(3164).setLabel(current_nodes[option_list[resp]].get("kodi_media_type", ""))  # type: ignore
                self.getControl(3165).setLabel(current_nodes[option_list[resp]].get("kodi_sort", ""))  # type: ignore
                self.getControl(3166).setLabel(current_nodes[option_list[resp]].get("use_cache", ""))  # type: ignore

                parent_id = current_nodes[option_list[resp]].get("item_parent", "")
                if parent_id:
                    view_name = self.view_list_lookup["id"].get(parent_id, parent_id)   # type: ignore
                    self.getControl(3157).setLabel(view_name)  # type: ignore

        elif control_id == 3154:
            control_3154: xbmcgui.ControlButton = cast(xbmcgui.ControlButton, self.getControl(3154))
            current_value = control_3154.getLabel()
            kb = xbmc.Keyboard()
            kb.setHeading("Set Node Name")
            kb.setDefault(current_value)
            kb.doModal()
            if kb.isConfirmed():
                new_node_name = kb.getText().strip()
                control_3154.setLabel(new_node_name)

        elif control_id == 3155:
            option_list = ["Movie", "Boxset", "Series", "Episode", "MusicAlbum", "Audio"]
            self.show_setting_for_select_multi(3155, option_list)

        elif control_id == 3156:
            control: xbmcgui.ControlButton = cast(xbmcgui.ControlButton, self.getControl(3156))
            current_value = control.getLabel()
            set_value = xbmcgui.Dialog().numeric(0, "Set Value", current_value)
            control.setLabel(set_value)

        elif control_id == 3157:
            view_names = self.view_list_lookup["name"]
            option_list = ["None"]
            for name in view_names:
                option_list.append(name)
            self.show_setting_for_select(3157, option_list)

        elif control_id == 3158:
            control_3158: xbmcgui.ControlButton = cast(xbmcgui.ControlButton, self.getControl(3158))
            current_value = control_3158.getLabel()
            if current_value == "True":
                control_3158.setLabel("False")
            else:
                control_3158.setLabel("True")

        elif control_id == 3159:
            control_3159: xbmcgui.ControlButton = cast(xbmcgui.ControlButton, self.getControl(3159))
            current_value = control_3159.getLabel()
            if current_value == "True":
                control_3159.setLabel("False")
            else:
                control_3159.setLabel("True")

        elif control_id == 3160:
            control_3160: xbmcgui.ControlButton = cast(xbmcgui.ControlButton, self.getControl(3160))
            current_value = control_3160.getLabel()
            if current_value == "True":
                control_3160.setLabel("False")
            elif current_value == "False":
                control_3160.setLabel(" ")
            elif current_value == " " or current_value == "":
                control_3160.setLabel("True")

        elif control_id == 3161:
            control_3161: xbmcgui.ControlButton = cast(xbmcgui.ControlButton, self.getControl(3161))
            current_value = control_3161.getLabel()
            if current_value == "True":
                control_3161.setLabel(" ")
            else:
                control_3161.setLabel("True")

        elif control_id == 3162:
            # Album, AlbumArtist, Artist, Budget, CommunityRating, CriticRating, DateCreated, DatePlayed,
            # PlayCount, PremiereDate, ProductionYear, SortName, Random, Revenue, Runtime
            option_list = ["None", "DatePlayed", "DateCreated", "PlayCount", "ProductionYear", "PremiereDate"]
            self.show_setting_for_select(3162, option_list)

        elif control_id == 3163:
            option_list = ["Descending", "Ascending"]
            self.show_setting_for_select(3163, option_list)

        elif control_id == 3164:
            option_list = ["movies", "tvshows", "homevideos", "episodes", "musicalbums", "musicartists", "musicvideos", "boxsets"]
            self.show_setting_for_select(3164, option_list)

        elif control_id == 3165:
            control_3165: xbmcgui.ControlButton = cast(xbmcgui.ControlButton, self.getControl(3165))
            current_value = control_3165.getLabel()
            if current_value == "True":
                control_3165.setLabel("False")
            else:
                control_3165.setLabel("True")

        elif control_id == 3166:
            control_3166: xbmcgui.ControlButton = cast(xbmcgui.ControlButton, self.getControl(3166))
            current_value = control_3166.getLabel()
            if current_value == "True":
                control_3166.setLabel("False")
            else:
                control_3166.setLabel("True")

        elif control_id == 3180:
            button_3153: xbmcgui.ControlButton = cast(xbmcgui.ControlButton, self.getControl(3153))
            existing_name: Union[str, None] = button_3153.getLabel()
            if existing_name == "New Node":
                existing_name = None
            button_3154: xbmcgui.ControlButton = cast(xbmcgui.ControlButton, self.getControl(3154))
            new_name: str = button_3154.getLabel()
            if new_name:
                i_type: str = self.getControl(3155).getLabel().strip()  # type: ignore
                i_limit: str = self.getControl(3156).getLabel().strip()  # type: ignore
                i_parent: str = self.getControl(3157).getLabel().strip()  # type: ignore
                i_parent: str = self.view_list_lookup["name"].get(i_parent, "").strip()  # type: ignore
                recursive: str = self.getControl(3158).getLabel().strip()  # type: ignore
                group: str = self.getControl(3159).getLabel().strip()  # type: ignore
                watched: str = self.getControl(3160).getLabel().strip()  # type: ignore
                inprogress: str = self.getControl(3161).getLabel().strip()  # type: ignore
                sortby: str = self.getControl(3162).getLabel().strip()  # type: ignore
                sortorder: str = self.getControl(3163).getLabel().strip()  # type: ignore

                kodi_media_type: str = self.getControl(3164).getLabel().strip()  # type: ignore
                kodi_sort: str = self.getControl(3165).getLabel().strip()  # type: ignore
                use_cache: str = self.getControl(3166).getLabel().strip()  # type: ignore

                new_node: Dict[str, str] = {
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
                    "use_cache": use_cache
                }
                add_custom_node(existing_name, new_name, new_node)
            self.close()

        elif control_id == 3181:
            button_3153_2: xbmcgui.ControlButton = cast(xbmcgui.ControlButton, self.getControl(3153))
            existing_name_2: str = button_3153_2.getLabel()
            if existing_name_2 != "New Node":
                add_custom_node(existing_name_2, None, None)
            self.close()
