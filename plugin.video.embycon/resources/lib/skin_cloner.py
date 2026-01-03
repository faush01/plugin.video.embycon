# Gnu General Public License - see LICENSE.TXT
from __future__ import annotations

import os

import xbmc
import xbmcgui
import xbmcvfs

from .jsonrpc import JsonRpc, get_value, set_value
from .simple_logging import SimpleLogging

log = SimpleLogging(__name__)


def check_skin_installed() -> None:
    params = {"addonid": "skin.estuary_embycon", "properties": ["version", "enabled"]}
    result = JsonRpc("Addons.GetAddonDetails").execute(params)
    log.debug("EmbyCon Skin Details: {0}", result)

    installed = result.get("result") is not None

    if not installed:
        clone_default_skin()


def clone_default_skin() -> None:
    xbmc.executebuiltin("Dialog.Close(all,true)")
    xbmc.executebuiltin("ActivateWindow(Home)")

    message = []
    message.append(
        "Once cloned you can switch between skins in the Kodi interface settings."
    )
    message.append("Do you want to continue?")
    response = xbmcgui.Dialog().yesno("Clone Estuary Skin?", "\n".join(message))

    if not response:
        return

    if not clone_skin():
        return

    set_skin_settings()
    update_kodi_settings()

    current_skin = get_value("lookandfeel.skin")
    log.debug("Current Skin : {0}", current_skin)
    if current_skin == "skin.estuary_embycon":
        return

    message = []
    message.append("To switch to the new EmbyCon skin, go to:")
    message.append("Settings -> Interface -> Skin -> Choose Skin")
    message.append("and select 'Estuary EmbyCon' from the list.")
    xbmcgui.Dialog().ok("EmbyCon Skin Cloner", "\n".join(message))

    xbmc.executebuiltin("Dialog.Close(all,true)")
    xbmc.executebuiltin("ActivateWindow(interfacesettings)")

    # switch to the new skin
    # response = xbmcgui.Dialog().yesno("EmbyCon Skin Cloner",
    #                                  "Do you want to switch to the new cloned skin?")
    # if not response:
    #    return

    # log.debug("SkinCloner : Current Skin : " + get_value("lookandfeel.skin"))
    # set_result = set_value("lookandfeel.skin", "skin.estuary_embycon")
    # log.debug("Save Setting : lookandfeel.skin : {0}", set_result)
    # log.debug("SkinCloner : Current Skin : " + get_value("lookandfeel.skin"))

    # xbmc.executebuiltin("ActivateWindow(Home)")
    # xbmc.executebuiltin("SetFocus(9000, 0, absolute)")
    # xbmc.executebuiltin("ReloadSkin()")


def walk_path(root_path: str, relative_path: str, all_files: list[str]) -> None:
    files = xbmcvfs.listdir(root_path)
    found_paths = files[0]
    found_files = files[1]

    for item in found_files:
        rel_path = os.path.join(relative_path, item)
        all_files.append(rel_path)

    for item in found_paths:
        new_path = os.path.join(root_path, item)
        rel_path = os.path.join(relative_path, item)
        all_files.append(rel_path)
        walk_path(new_path, rel_path, all_files)


def clone_skin() -> bool:
    log.debug("Cloning Estuary Skin")

    ver = xbmc.getInfoLabel("System.BuildVersion")[:2]
    log.debug("Major Kodi Version: {0}", ver)

    # get embycon path
    kodi_home_path = xbmcvfs.translatePath("special://home")
    embycon_path = os.path.join(kodi_home_path, "addons", "plugin.video.embycon")

    # check if we have custom files for this version
    custom_source = (
        os.path.join(embycon_path, "resources", "skins", "skin.estuary", ver) + os.sep
    )
    if not xbmcvfs.exists(custom_source):
        log.debug("No custom skin files for Kodi version: {0}", ver)
        xbmcgui.Dialog().ok(
            "EmbyCon Skin Cloner",
            "No custom skin files available for Kodi version: {0}".format(ver),
        )
        return False

    kodi_path = xbmcvfs.translatePath("special://xbmc")
    kodi_skin_source = os.path.join(kodi_path, "addons", "skin.estuary")
    log.debug("Kodi Skin Source: {0}", kodi_skin_source)

    pdialog = xbmcgui.DialogProgress()
    pdialog.create("EmbyCon Skin Cloner", "")

    all_files = []
    walk_path(kodi_skin_source, "", all_files)
    for found in all_files:
        log.debug("Found Path: {0}", found)

    kodi_skin_destination = os.path.join(
        kodi_home_path, "addons", "skin.estuary_embycon"
    )
    log.debug("Kodi Skin Destination: {0}", kodi_skin_destination)

    # copy all skin files (clone)
    count = 0
    total = len(all_files)
    for skin_file in all_files:
        percentage_done = int(float(count) / float(total) * 100.0)
        pdialog.update(percentage_done, "%s" % skin_file)

        source = os.path.join(kodi_skin_source, skin_file)
        destination = os.path.join(kodi_skin_destination, skin_file)
        xbmcvfs.copy(source, destination)

        count += 1

    # alter skin addon.xml
    addon_xml_path = os.path.join(kodi_skin_destination, "addon.xml")
    log.debug("Addon XML file path : {0}", addon_xml_path)
    with open(addon_xml_path, "r", encoding="utf-8") as addon_file:
        addon_xml_data = addon_file.read()

    addon_xml_data = addon_xml_data.replace(
        'id="skin.estuary"', 'id="skin.estuary_embycon"'
    )
    addon_xml_data = addon_xml_data.replace('name="Estuary"', 'name="Estuary EmbyCon"')

    # log.debug("{0}", addon_xml_data)

    # save the edited version of addon.xml
    with open(addon_xml_path, "w", encoding="utf-8") as addon_file:
        addon_file.write(addon_xml_data)

    # copy modified skin files
    file_list = [
        "Home.xml",
        "Includes_Home.xml",
        "DialogVideoInfo.xml",
        "DialogSeekBar.xml",
        "VideoOSD.xml",
    ]

    for file_name in file_list:
        source = os.path.join(
            embycon_path, "resources", "skins", "skin.estuary", ver, "xml", file_name
        )
        if xbmcvfs.exists(source):
            destination = os.path.join(kodi_skin_destination, "xml", file_name)
            log.debug(
                "Copying modified skin files : source:{0} destination:{1}",
                source,
                destination,
            )
            xbmcvfs.copy(source, destination)
        else:
            log.debug(
                "Copying modified skin files : source:{0} !Skipping, source not available!",
                source,
            )

    xbmc.executebuiltin("UpdateLocalAddons")

    pdialog.close()
    del pdialog

    # enable the new skin
    params = {"addonid": "skin.estuary_embycon", "enabled": True}
    result = JsonRpc("Addons.SetAddonEnabled").execute(params)
    log.debug("Addons.SetAddonEnabled : {0}", result)

    return True


def update_kodi_settings() -> None:
    log.debug("Settings Kodi Settings")

    # set_value("screensaver.mode", "script.screensaver.logoff")
    # set_value("videoplayer.seekdelay", 0)
    set_value("filelists.showparentdiritems", False)
    set_value("filelists.showaddsourcebuttons", False)
    set_value("myvideos.extractchapterthumbs", False)
    set_value("myvideos.extractflags", False)
    # set_value("myvideos.selectaction", 3)
    set_value("myvideos.extractthumb", False)


def set_skin_settings() -> None:
    log.debug("Settings Skin Settings")

    xbmc.executebuiltin("Skin.SetBool(HomeMenuNoPicturesButton)")
    xbmc.executebuiltin("Skin.SetBool(HomeMenuNoMusicButton)")
    xbmc.executebuiltin("Skin.SetBool(HomeMenuNoVideosButton)")
    xbmc.executebuiltin("Skin.SetBool(HomeMenuNoFavButton)")
    xbmc.executebuiltin("Skin.SetBool(HomeMenuNoTVButton)")
    xbmc.executebuiltin("Skin.SetBool(HomeMenuNoWeatherButton)")
    xbmc.executebuiltin("Skin.SetBool(HomeMenuNoMusicVideoButton)")
    xbmc.executebuiltin("Skin.SetBool(HomeMenuNoRadioButton)")
    xbmc.executebuiltin("Skin.SetBool(no_slide_animations)")
    xbmc.executebuiltin("Skin.SetBool(HomeMenuNoMovieButton)")
    xbmc.executebuiltin("Skin.SetBool(HomeMenuNoTVShowButton)")
    xbmc.executebuiltin("Skin.SetBool(HomeMenuNoGamesButton)")
    xbmc.executebuiltin("Skin.Reset(HomeMenuNoProgramsButton)")
