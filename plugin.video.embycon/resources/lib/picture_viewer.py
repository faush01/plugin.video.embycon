# Gnu General Public License - see LICENSE.TXT
from __future__ import annotations

from typing import cast
import xbmcgui

from .simple_logging import SimpleLogging

log = SimpleLogging(__name__)


class PictureViewer(xbmcgui.WindowXMLDialog):
    picture_url: str | None = None
    action_exitkeys_id: list[int] | None = None

    def __init__(
        self, xmlFilename: str, scriptPath: str, defaultSkin: str, defaultRes: str
    ) -> None:
        log.debug("PictureViewer: __init__")
        super().__init__(xmlFilename, scriptPath, defaultSkin, defaultRes)

    def onInit(self) -> None:
        log.debug("PictureViewer: onInit")
        self.action_exitkeys_id = [10, 13]

        picture_control: xbmcgui.ControlImage = cast(
            xbmcgui.ControlImage, self.getControl(3010)
        )

        if self.picture_url:
            picture_control.setImage(self.picture_url)
        # self.listControl.addItems(self.action_items)
        # self.setFocus(self.listControl)

        # bg_image = self.getControl(3010)
        # bg_image.setHeight(50 * len(self.action_items) + 20)

    def onFocus(self, controlId: int) -> None:
        pass

    def onClick(self, controlId: int) -> None:
        pass

    def setPicture(self, url: str) -> None:
        self.picture_url = url
