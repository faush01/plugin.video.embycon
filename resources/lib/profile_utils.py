import json
import sys
import io
import os
import pstats
from datetime import datetime

import xbmcplugin
import xbmcgui
import xbmcvfs
import xbmcaddon

from .simple_logging import SimpleLogging

log = SimpleLogging(__name__)

ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2
ACTION_MOVE_UP = 3
ACTION_MOVE_DOWN = 4
ACTION_PREVIOUS_MENU = 10
ACTION_BACKSPACE = 110

class ProfileDetailsDialog(xbmcgui.WindowXMLDialog):

    profile_details = {}
    current_position = 0
    line_count = 0
    display_option = 0

    def __init__(self, *args, **kwargs):
        log.debug("ActionMenu: __init__")
        xbmcgui.WindowXML.__init__(self)

    def onInit(self):
        log.debug("ActionMenu: onInit")
        self.action_exitkeys_id = [10, 13]
        self.set_profile_details_text()

    def onFocus(self, control_id):
        pass

    def doAction(self, action_id):
        pass

    def onMessage(self, message):
        log.debug("ActionMenu: onMessage: {0}", message)

    def onAction(self, action):
        if action.getId() == 10:  # ACTION_PREVIOUS_MENU
            self.close()
        elif action.getId() == 92:  # ACTION_NAV_BACK
            self.close()
        elif action.getId() == ACTION_MOVE_DOWN:
            details_text_control = self.getControl(3010)
            self.current_position += 1
            if self.current_position > self.line_count:
                self.current_position = self.line_count
            details_text_control.scroll(self.current_position)
        elif action.getId() == ACTION_MOVE_UP:
            details_text_control = self.getControl(3010)
            self.current_position -= 1
            if self.current_position < 0:
                self.current_position = 0
            details_text_control.scroll(self.current_position)
        elif action.getId() == ACTION_MOVE_RIGHT:
            self.display_option += 1
            if self.display_option > 2:
                self.display_option = 0
            self.set_profile_details_text()
        elif action.getId() == ACTION_MOVE_LEFT:
            self.display_option -= 1
            if self.display_option < 0:
                self.display_option = 2
            self.set_profile_details_text()
        else:
            log.debug("ActionMenu: onAction: {0}", action.getId())

    def onClick(self, control_id):
        if control_id == 3000:
            self.close()

    def set_profile_details(self, value):
        self.profile_details = value

    def set_profile_details_text(self):

        if self.display_option == 0 or self.display_option == 1:
            # build profile details text
            profile_details_text = "Profile Data\n\n"

            profile_details_text += "Params      : " + self.profile_details["addon_action"] + "\n"
            profile_details_text += "Time Stamp  : " + self.profile_details["time_stamp"] + "\n"
            profile_details_text += "Total Calls : " + str(self.profile_details["total_calls"]) + "\n"
            profile_details_text += "Total Time  : " + str(self.profile_details["total_time"]) + "\n"
            profile_details_text += "Total Items : " + str(self.profile_details["item_count"]) + "\n"
            profile_details_text += "\n"

            stats = self.profile_details["stats"]

            if self.display_option == 0:
                profile_details_text += "Sorted By : LocalTime\n"
                stats.sort(key=lambda x: x["time_local"], reverse=True)
            elif self.display_option == 1:
                profile_details_text += "Sorted By : StackTime\n"
                stats.sort(key=lambda x: x["time_stack"], reverse=True)

            profile_details_text += "\n"
            profile_details_text += "   "
            profile_details_text += self.add_padding("nCalls", 10)
            profile_details_text += self.add_padding("inFunc", 10)
            profile_details_text += self.add_padding("inStack", 10)
            profile_details_text += "file:line(func)\n"

            for stat in stats:
                t_time = stat["time_local"]
                s_time = stat["time_stack"]
                if t_time > 0.0 or s_time > 0.0:
                    t_time_string = "{:0.3f}".format(t_time)
                    s_time_string = "{:0.3f}".format(s_time)

                    t_time_string = self.add_padding(t_time_string, 10)
                    s_time_string = self.add_padding(s_time_string, 10)
                    calls_string = self.add_padding(str(stat["calls"]), 10)

                    profile_details_text += "   "
                    profile_details_text += calls_string
                    profile_details_text += t_time_string
                    profile_details_text += s_time_string
                    profile_details_text += stat["func"] + "\n"

        else:
            profile_details_text = self.profile_details["source"]

        self.current_position = 0
        self.line_count = profile_details_text.count('\n')

        details_text_control = self.getControl(3010)
        details_text_control.setText(profile_details_text)

    def add_padding(self, value, target_len):
        text_len = len(value)
        to_add = target_len - text_len
        if to_add < 1:
            return value
        for x in range(0, to_add):
            value += " "
        return value


def view_profile_details(params):
    log.debug("VIEW_PROFILE_DETAILS")
    log.debug("profile file : {0}", params["file"])

    addon_dir = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo("profile"))
    profile_path = os.path.join(addon_dir, "profile", params["file"])

    stats_data = {}
    with open(profile_path) as json_file:
        stats_data = json.load(json_file)

    plugin_path = xbmcvfs.translatePath(os.path.join(xbmcaddon.Addon().getAddonInfo('path')))
    action_menu = ProfileDetailsDialog("ProfileDetailsDialog.xml", plugin_path, "default", "720p")
    action_menu.set_profile_details(stats_data)
    action_menu.doModal()


def list_available_profiles(params):

    handle = int(sys.argv[1])
    list_items = []

    addon_dir = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo("profile"))
    profile_path = os.path.join(addon_dir, "profile")
    dirs, files = xbmcvfs.listdir(profile_path)
    files.sort()

    for file in files:
        stats_data = None
        profile_file_name = os.path.join(profile_path, file)
        with open(profile_file_name) as json_file:
            stats_data = json.load(json_file)

        total_calls = stats_data["total_calls"]
        total_time = stats_data["total_time"]
        item_count = stats_data["item_count"]
        time_stamp = stats_data["time_stamp"]

        label = time_stamp + " : " + str(total_time) + " : " + str(total_calls) + " : " + str(item_count)

        list_item = xbmcgui.ListItem(label=label, offscreen=True)
        action_url = sys.argv[0] + "?mode=VIEW_PROFILE_DETAILS&file=" + file
        item_tupple = (action_url, list_item, True)
        list_items.append(item_tupple)

    # xbmcplugin.setContent(handle, 'artists')
    xbmcplugin.addDirectoryItems(handle, list_items)
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)


def remove_old_profiles(profile_path, keep=30):
    dirs, files = xbmcvfs.listdir(profile_path)
    file_count = len(files)
    log.debug("Performance profile file count : {0} target : {1}", file_count, keep)
    if file_count > keep:
        files.sort()
        to_remove = file_count - keep
        log.debug("Performance files removing : {0}", to_remove)
        for index in range(0, to_remove):
            full_path = os.path.join(profile_path, files[index])
            log.debug("Removing performance file : {0}", full_path)
            xbmcvfs.delete(full_path)


def get_profile_data(pr):
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s)

    # ps = ps.sort_stats('cumulative')
    # ps.print_stats()
    # ps.strip_dirs()
    # ps = ps.sort_stats('tottime')
    # ps.print_stats()

    ps.strip_dirs()
    ps.print_stats()
    pstring = s.getvalue()
    # log.debug("profile data :\n{0}", pstring)

    # pstring = 'ncalls' + pstring.split('ncalls')[-1]
    # pstring = '\n'.join([','.join(line.rstrip().split(None, 5)) for line in pstring.split('\n')])

    stats_data = {}
    stats_data["source"] = pstring
    time_stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    stats_data["time_stamp"] = time_stamp

    # extract stats info
    stats = []
    total_tokens = []
    data_started = False
    lines = pstring.split("\n")
    for index in range(0, len(lines)):
        line = lines[index].strip()
        if len(line) == 0:
            continue
        if index == 0:
            total_tokens = line.split(" ")
        elif line.startswith("ncalls"):
            data_started = True
        elif data_started:
            stats_tokens = line.split(None, 5)
            stats.append(stats_tokens)

    total_calls = 0
    if total_tokens.index("function") > -1:
        total_calls = total_tokens[total_tokens.index("function") - 1]
    total_time = 0.0
    if total_tokens.index("in") > -1:
        total_time = total_tokens[total_tokens.index("in") + 1]

    stats_data["total_calls"] = int(total_calls)
    stats_data["total_time"] = float(total_time)
    stats_data["stats"] = []
    for s in stats:
        calls = s[0].split("/")
        item = {
            "calls": int(calls[0]),
            "time_local": float(s[1]),
            "time_stack": float(s[3]),
            "func": s[5]
        }
        stats_data["stats"].append(item)

    return stats_data
