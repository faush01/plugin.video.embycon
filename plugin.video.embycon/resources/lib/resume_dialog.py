# Gnu General Public License - see LICENSE.TXT

from typing import cast
import xbmcgui

from .simple_logging import SimpleLogging
from .translation import string_load

log = SimpleLogging(__name__)


class ResumeDialog(xbmcgui.WindowXMLDialog):
    resumePlay: int = -1
    resumeTimeStamp: str = ""
    action_exitkeys_id = None

    def __init__(
        self,
        xmlFilename: str,
        scriptPath: str,
        defaultSkin: str = "default",
        defaultRes: str = "720p",
    ) -> None:
        xbmcgui.WindowXMLDialog.__init__(
            self, xmlFilename, scriptPath, defaultSkin, defaultRes
        )
        log.debug("ResumeDialog __init__")

    def onInit(self) -> None:
        self.action_exitkeys_id = [10, 13]
        button_control: xbmcgui.ControlButton = cast(
            xbmcgui.ControlButton, self.getControl(3010)
        )
        button_control.setLabel(self.resumeTimeStamp)
        button_control_02: xbmcgui.ControlButton = cast(
            xbmcgui.ControlButton, self.getControl(3011)
        )
        button_control_02.setLabel(string_load(30237))

    def onFocus(self, controlId: int) -> None:
        pass

    def onClick(self, controlId: int) -> None:
        if controlId == 3010:
            self.resumePlay = 0
            self.close()
        if controlId == 3011:
            self.resumePlay = 1
            self.close()

    def setResumeTime(self, timeStamp: str) -> None:
        self.resumeTimeStamp = timeStamp

    def getResumeAction(self) -> int:
        return self.resumePlay
