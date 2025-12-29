from __future__ import annotations
from typing import cast
import xbmcgui

from .simple_logging import SimpleLogging

log = SimpleLogging(__name__)


class BitrateDialog(xbmcgui.WindowXMLDialog):
    slider_control: xbmcgui.ControlSlider | None = None
    bitrate_label: xbmcgui.ControlLabel | None = None
    initial_bitrate_value: int = 0
    selected_transcode_value: int = 0

    def __init__(
        self,
        xml_filename: str,
        script_path: str,
        default_skin: str = "default",
        default_res: str = "720p",
    ) -> None:
        log.debug("BitrateDialog: __init__")
        super().__init__(xml_filename, script_path, default_skin, default_res)

    def onInit(self) -> None:
        log.debug("ActionMenu: onInit")
        self.action_exitkeys_id = [10, 13]

        self.slider_control = cast(xbmcgui.ControlSlider, self.getControl(3000))
        self.slider_control.setInt(self.initial_bitrate_value, 400, 100, 15000)

        self.bitrate_label = cast(xbmcgui.ControlLabel, self.getControl(3030))
        bitrate_label_string = str(self.slider_control.getInt()) + " Kbs"
        self.bitrate_label.setLabel(bitrate_label_string)

    def onFocus(self, controlId: int) -> None:
        pass

    def onAction(self, action: xbmcgui.Action) -> None:
        # log.debug("onAction: onAction: {0} {1}", action.getId(), self.slider_control.getInt())

        if self.bitrate_label and self.slider_control:
            bitrate_label_string = str(self.slider_control.getInt()) + " Kbs"
            self.bitrate_label.setLabel(bitrate_label_string)

        if action.getId() == 10:  # ACTION_PREVIOUS_MENU
            self.close()
        elif action.getId() == 92:  # ACTION_NAV_BACK
            self.close()
        elif action.getId() == 7:  # ENTER
            if self.slider_control:
                self.selected_transcode_value = self.slider_control.getInt()
            self.close()

    def onClick(self, controlId: int) -> None:
        if controlId == 3000:
            log.debug("ActionMenu: Selected Item: {0}", controlId)
            # self.close()
