"""
websocket - WebSocket client library for Python

Copyright (C) 2010 Hiroki Ohtani(liris)

    This library is free software; you can redistribute it and/or
    modify it under the terms of the GNU Lesser General Public
    License as published by the Free Software Foundation; either
    version 2.1 of the License, or (at your option) any later version.

    This library is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
    Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with this library; if not, write to the Free Software
    Foundation, Inc., 51 Franklin Street, Fifth Floor,
    Boston, MA  02110-1335  USA

"""
from ..simple_logging import SimpleLogging

log = SimpleLogging("web_socket_logging")

_traceEnabled = False


def enableTrace(traceable):
    global _traceEnabled
    _traceEnabled = traceable


def dump(title, message):
    if _traceEnabled:
        log.debug("--- {0} ---", title)
        log.debug("{0}", message)
        log.debug("-----------------------")


def error(msg):
    log.error("{0}", msg)


def warning(msg):
    log.info("{0}", msg)


def debug(msg):
    log.debug("{0}", msg)


def trace(msg):
    if _traceEnabled:
        log.debug("{0}", msg)


def isEnabledForError():
    return True


def isEnabledForDebug():
    return _traceEnabled
