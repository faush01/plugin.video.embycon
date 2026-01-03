import sys
from typing import cast
import xbmcgui

from resources.lib.simple_logging import SimpleLogging

log = SimpleLogging("service")


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    list_item = cast(xbmcgui.ListItem, sys.listitem)  # type: ignore
    message = f"Clicked on ({list_item.getLabel()}) context menu item with ID ({list_item.getProperty('id')}) with action ({action})."
    log.debug("Context Menu Action: {0}", message)
    xbmcgui.Dialog().notification("Hello context items!", message)
