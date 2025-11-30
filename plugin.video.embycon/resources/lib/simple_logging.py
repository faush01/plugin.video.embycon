# Gnu General Public License - see LICENSE.TXT

import threading
import xbmc
import xbmcaddon


class SimpleLogging:
    _instances = {}
    _lock = threading.Lock()
    name = ""
    enable_logging = False

    def __new__(cls, name):
        if name not in cls._instances:
            with cls._lock:
                # Double-checked locking pattern
                if name not in cls._instances:
                    instance = super(SimpleLogging, cls).__new__(cls)
                    cls._instances[name] = instance
        return cls._instances[name]

    def __init__(self, name):
        # Only initialize once
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        settings = xbmcaddon.Addon()
        prefix = settings.getAddonInfo('name')
        self.name = prefix + '.' + name
        self.enable_logging = settings.getSetting('log_debug') == "true"
        self._initialized = True

        # params = {"setting": "debug.showloginfo"}
        # setting_result = json_rpc('Settings.getSettingValue').execute(params)
        # current_value = setting_result.get("result", None)
        # if current_value is not None:
        #     self.enable_logging = current_value.get("value", False)
        # xbmc.log("LOGGING_ENABLED %s : %s" % (self.name, str(self.enable_logging)), level=xbmc.LOGDEBUG)

    def __str__(self):
        return "LoggingEnabled: " + str(self.enable_logging)

    def info(self, fmt, *args):
        log_line = self.name + "|INFO|" + self.log_line(fmt, *args)
        xbmc.log(log_line, level=xbmc.LOGINFO)

    def error(self, fmt, *args):
        log_line = self.name + "|ERROR|" + self.log_line(fmt, *args)
        xbmc.log(log_line, level=xbmc.LOGERROR)

    def debug(self, fmt, *args):
        if self.enable_logging:
            log_line = self.name + "|DEBUG|" + self.log_line(fmt, *args)
            xbmc.log(log_line, level=xbmc.LOGINFO)

    @staticmethod
    def log_line(fmt, *args):
        new_args = []
        # convert any unicode to utf-8 strings
        for arg in args:
            new_args.append(arg)
            #if isinstance(arg, unicode):
            #    new_args.append(arg.encode("utf-8"))
            #else:
            #    new_args.append(arg)
        log_line = fmt.format(*new_args)
        return log_line
