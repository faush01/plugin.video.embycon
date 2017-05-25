import xbmcgui


class HomeWindow():
    """
        xbmcgui.Window(10000) with add-on id prefixed to keys
    """
    def __init__(self):
        self.id_string = 'plugin.video.embycon-%s'
        self.window = xbmcgui.Window(10000)

    def getProperty(self, key):
        key = self.id_string % key
        value = self.window.getProperty(key)
        # log.debug('HomeWindow: getProperty |%s| -> |%s|' % (key, value))
        return value

    def setProperty(self, key, value):
        key = self.id_string % key
        # log.debug('HomeWindow: setProperty |%s| -> |%s|' % (key, value))
        self.window.setProperty(key, value)

    def clearProperty(self, key):
        key = self.id_string % key
        # log.debug('HomeWindow: clearProperty |%s|' % key)
        self.window.clearProperty(key)
