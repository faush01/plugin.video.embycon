from __future__ import annotations
import json
from typing import Any, TypedDict
import xbmc


class JsonRpcResponse(TypedDict):
    result: dict[str, Any]


class JsonRpc(object):
    id_ = 1
    jsonrpc = "2.0"

    def __init__(self, method: str) -> None:
        self.method = method

    def execute(self, params: dict[str, Any]) -> JsonRpcResponse:
        query: dict[str, Any] = {
            "jsonrpc": self.jsonrpc,
            "id": self.id_,
            "method": self.method,
        }
        if params:
            query["params"] = params

        return json.loads(xbmc.executeJSONRPC(json.dumps(query)))


def get_value(name: str) -> object:
    result = JsonRpc("Settings.getSettingValue").execute({"setting": name})
    return result["result"]["value"]


def set_value(name: str, value: object) -> JsonRpcResponse:
    params = {"setting": name, "value": value}
    return JsonRpc("Settings.setSettingValue").execute(params)
