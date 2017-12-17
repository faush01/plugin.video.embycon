
import traceback
import sys
import os
import httplib
import json

import xbmcgui
import xbmc

from simple_logging import SimpleLogging
from clientinfo import ClientInformation
from translation import i18n

log = SimpleLogging(__name__)

def catch_except(errors=(Exception, ), default_value=False):
    # Will wrap method with try/except and print parameters for easier debugging
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except errors as error:
                if not (hasattr(error, 'quiet') and error.quiet):
                    return_value = xbmcgui.Dialog().yesno(i18n('error'), i18n('embycon_error'), i18n('embycon_error_submit'))
                    if return_value:
                        log.debug("Sending Error Data")
                        try:
                            submit_error_data()
                        except Exception as error:
                            log.debug("Sending Error Data Failed: " + str(error))
                    raise
                return default_value
        return wrapper
    return decorator

def submit_error_data():

    error_type, error_short, error_stack = format_exception()

    data = {}
    data["event"] = "ErrorReport"
    data["error_stack"] = error_stack
    data["error_type"] = error_type
    data["error_short"] = error_short
    data["sys.argv"] = sys.argv
    data["kodi_version"] = xbmc.getInfoLabel("System.BuildVersion")
    data["addon_version"] = ClientInformation().getVersion()

    post_data = json.dumps(data)
    log.debug("ERROR_DATA: " + post_data)

    server = "allthedata.pythonanywhere.com"
    url_path = "/submit"
    conn = httplib.HTTPConnection(server, timeout=40)
    head = {}
    head["Content-Type"] = "application/json"
    conn.request(method="POST", url=url_path, body=post_data, headers=head)
    data = conn.getresponse()
    log.debug("Submit Responce Code: " + str(data.status))


def format_exception():

    stack = traceback.extract_stack()
    exc_type, exc_obj, exc_tb = sys.exc_info()
    stack_trace_data = traceback.format_tb(exc_tb)
    tb = traceback.extract_tb(exc_tb)
    full_tb = stack[:-1] + tb
    # log.error(str(full_tb))

    # get last stack frame
    latestStackFrame = None
    if (len(tb) > 0):
        latestStackFrame = tb[-1]
    # log.error(str(tb))

    fileStackTrace = ""
    try:
        # get files from stack
        stackFileList = []
        for frame in full_tb:
            # log.error(str(frame))
            frameFile = (os.path.split(frame[0])[1])[:-3]
            frameLine = frame[1]
            if (len(stackFileList) == 0 or stackFileList[-1][0] != frameFile):
                stackFileList.append([frameFile, [str(frameLine)]])
            else:
                file = stackFileList[-1][0]
                lines = stackFileList[-1][1]
                lines.append(str(frameLine))
                stackFileList[-1] = [file, lines]
        # log.error(str(stackFileList))

        for item in stackFileList:
            lines = ",".join(item[1])
            fileStackTrace += item[0] + "," + lines + ":"
        # log.error(str(fileStackTrace))
    except Exception as e:
        fileStackTrace = None
        log.error(e)

    errorType = "NA"
    errorFile = "NA"

    if latestStackFrame is not None:
        if fileStackTrace is None:
            fileStackTrace = os.path.split(latestStackFrame[0])[1] + ":" + str(latestStackFrame[1])

        codeLine = "NA"
        if (len(latestStackFrame) > 3 and latestStackFrame[3] != None):
            codeLine = latestStackFrame[3].strip()

        errorFile = "%s(%s)(%s)" % (fileStackTrace, exc_obj.message, codeLine)
        errorFile = errorFile[0:499]
        errorType = "%s" % (exc_type.__name__)
        # log.error(errorType + " - " + errorFile)

    del (exc_type, exc_obj, exc_tb)

    return errorType, errorFile, stack_trace_data