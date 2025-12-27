# Gnu General Public License - see LICENSE.TXT
from __future__ import annotations

from typing import List, Optional, cast

import xbmcgui

from .simple_logging import SimpleLogging
from .auto_close import ActionAutoClose


log = SimpleLogging(__name__)


class ActionMenu(xbmcgui.WindowXMLDialog):
    selected_action: xbmcgui.ListItem | None = None
    action_items: Optional[List[str | xbmcgui.ListItem]] = None
    auto_close_thread: Optional[ActionAutoClose] = None
    listControl: Optional[xbmcgui.ControlList] = None
    action_exitkeys_id: Optional[List[int]] = None

    def __init__(
        self,
        xmlFilename: str,
        scriptPath: str,
        defaultSkin: str = "Default",
        defaultRes: str = "720p",
    ) -> None:
        log.debug("ActionMenu: __init__")
        super().__init__(xmlFilename, scriptPath, defaultSkin, defaultRes)
        self.auto_close_thread = ActionAutoClose(self)
        self.auto_close_thread.start()

    def onInit(self) -> None:
        log.debug("ActionMenu: onInit")
        self.action_exitkeys_id = [10, 13]

        self.listControl = cast(xbmcgui.ControlList, self.getControl(3000))
        if self.action_items:
            self.listControl.addItems(self.action_items)
        self.setFocus(self.listControl)

        # bg_image = self.getControl(3010)
        # bg_image.setHeight(50 * len(self.action_items) + 20)

    def onFocus(self, controlId: int) -> None:
        pass

    def onAction(self, action: xbmcgui.Action) -> None:
        if action.getId() == 10:  # ACTION_PREVIOUS_MENU
            if self.auto_close_thread:
                self.auto_close_thread.stop()
            self.close()
        elif action.getId() == 92:  # ACTION_NAV_BACK
            if self.auto_close_thread:
                self.auto_close_thread.stop()
            self.close()
        else:
            if self.auto_close_thread:
                self.auto_close_thread.set_last()
            log.debug("ActionMenu: onAction: {0}", action.getId())

    def onClick(self, controlId: int) -> None:
        if controlId == 3000:
            if self.listControl:
                self.selected_action = self.listControl.getSelectedItem()
            log.debug("ActionMenu: Selected Item: {0}", self.selected_action)
            if self.auto_close_thread:
                self.auto_close_thread.stop()
            self.close()

    def setActionItems(
        self, action_items: Optional[List[str | xbmcgui.ListItem]]
    ) -> None:
        self.action_items = action_items

    def getActionItem(self) -> Optional[xbmcgui.ListItem]:
        return self.selected_action
