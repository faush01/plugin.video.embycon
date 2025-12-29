# Gnu General Public License - see LICENSE.TXT
from __future__ import annotations

from typing import List, Any
from dataclasses import dataclass
import json
from collections import defaultdict
import threading
import hashlib
import os
import pickle
import time

from .downloadutils import DownloadUtils
from .simple_logging import SimpleLogging
from .item_functions import GuiOptions, extract_item_info
from .kodi_utils import HomeWindow
from .translation import string_load
from .tracking import timer
from .filelock import FileLock
from .data_models import (
    DataSet,
    Item,
    MediaStream,
    MediaSource,
    Studio,
    GenreItem,
    UserData,
    TagItem,
    ImageTags,
)

import xbmc
import xbmcaddon
import xbmcvfs
import xbmcgui


log = SimpleLogging(__name__)


# --- Custom Data Loader ---
def process_json_data(json_raw_data: str) -> DataSet:
    """Load and parse the JSON data file into nested dataclasses."""

    log.info("loading emby data in dataclasses")

    def parse_media_source(ms: dict) -> MediaSource:
        if "MediaStreams" in ms:
            ms["MediaStreams"] = [MediaStream(**s) for s in ms["MediaStreams"]]
        return MediaSource(**ms)

    def parse_item(item: dict) -> Item:
        if "MediaSources" in item:
            item["MediaSources"] = [
                parse_media_source(ms) for ms in item["MediaSources"]
            ]
        if "Studios" in item:
            item["Studios"] = [Studio(**st) for st in item["Studios"]]
        if "GenreItems" in item:
            item["GenreItems"] = [GenreItem(**gi) for gi in item["GenreItems"]]
        if "UserData" in item:
            item["UserData"] = UserData(**(item["UserData"]))
        if "MediaStreams" in item:
            item["MediaStreams"] = [MediaStream(**ms) for ms in item["MediaStreams"]]
        if "TagItems" in item:
            item["TagItems"] = [TagItem(**ti) for ti in item["TagItems"]]
        if "ImageTags" in item:
            item["ImageTags"] = ImageTags(**(item["ImageTags"]))
        return Item(**item)

    raw_json = json.loads(json_raw_data)
    if raw_json is None or not isinstance(raw_json, dict) or "Items" not in raw_json:
        log.debug("JSON data does not contain 'Items' key")
        return DataSet(Items=[])

    items = [parse_item(i) for i in raw_json["Items"]]
    del raw_json
    new_dataset = DataSet(Items=items)

    log.info("process_json_data : {0}", new_dataset)

    m = hashlib.md5()
    m.update(json_raw_data.encode("utf-8"))
    file_name = m.hexdigest()
    file_name = os.path.join("C:\\Temp\\test_pickle_files", file_name + ".pickle")
    with open(file_name, "wb") as handle:
        pickle.dump(new_dataset, handle, protocol=pickle.HIGHEST_PROTOCOL)

    # loaded_data = None
    # with open(file_name, 'rb') as handle:
    #    loaded_data = pickle.load(handle)
    # log.info("process_json_data reloaded : {0}", loaded_data)

    return new_dataset


@dataclass
class GetItemsResult:
    """Result from get_items containing cache file path, items, total count, and cache thread."""

    cache_file: str
    item_list: List[Any]
    total_records: int
    cache_thread: CacheManagerThread | None


class CacheItem:
    def __init__(self) -> None:
        self.item_list: List[Any] | None = None
        self.item_list_hash: str | None = None
        self.date_saved: float | None = None
        self.date_last_used: float | None = None
        self.last_action: str | None = None
        self.items_url: str | None = None
        self.file_path: str
        self.user_id: str | None = None
        self.total_records: int | None = None


class DataManager:
    def __init__(self) -> None:
        # log.debug("DataManager __init__")
        pass

    @timer
    def get_content_dataset(self, url: str) -> DataSet:
        json_data = DownloadUtils().download_url(url)
        dataset_data: DataSet = process_json_data(json_data)
        return dataset_data

    @staticmethod
    def load_json_data(json_data: str) -> dict:
        return json.loads(json_data, object_hook=lambda d: defaultdict(lambda: None, d))

    @timer
    def get_content(self, url: str | None) -> dict:
        if not url:
            raise ValueError("URL cannot be None or empty")
        du = DownloadUtils()
        du.set_host_domain()
        json_data = du.download_url(url)
        return self.load_json_data(json_data)

    def get_cache_filename(self, url: str) -> str:
        download_utils = DownloadUtils()
        addon_dir = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo("profile"))
        user_id = download_utils.get_user_id()
        server = download_utils.get_server()
        m = hashlib.md5()
        line = user_id + "|" + str(server) + "|" + url
        m.update(line.encode("utf-8"))
        url_hash = m.hexdigest()
        cache_path = os.path.join(addon_dir, "cache")
        xbmcvfs.mkdirs(cache_path)
        return os.path.join(cache_path, "cache_" + url_hash + ".pickle")

    @timer
    def get_items(
        self, url: str, gui_options: GuiOptions, use_cache: bool = False
    ) -> GetItemsResult:
        home_window = HomeWindow()
        log.debug("last_content_url : use_cache={0} url={1}", use_cache, url)
        home_window.set_property("last_content_url", url)

        download_utils = DownloadUtils()
        user_id = download_utils.get_user_id()
        cache_file = self.get_cache_filename(url)

        item_list = None
        total_records = 0
        baseline_name = None
        cache_thread = CacheManagerThread()
        cache_thread.gui_options = gui_options

        home_window.set_property(cache_file, "true")

        clear_cache = home_window.get_property("skip_cache_for_" + url)
        if clear_cache and os.path.isfile(cache_file):
            log.debug("Clearing cache data and loading new data")
            home_window.clear_property("skip_cache_for_" + url)
            with FileLock(cache_file, timeout=5):
                xbmcvfs.delete(cache_file)

        # try to load the list item data from the cache
        if os.path.isfile(cache_file) and use_cache:
            log.debug("Loading url data from cached pickle data")

            with FileLock(cache_file, timeout=5):
                with open(cache_file, "rb") as handle:
                    try:
                        cache_item = pickle.load(handle)
                        cache_thread.cached_item = cache_item
                        item_list = cache_item.item_list
                        total_records = cache_item.total_records
                    except Exception as err:
                        log.error("Pickle Data Load Failed : {0}", err)
                        item_list = None

        # we need to load the list item data form the server
        if item_list is None or len(item_list) == 0:
            log.debug("Loading url data from server")

            results = self.get_content(url)

            if results is None:
                results = []

            if isinstance(results, dict):
                total_records = results.get("TotalRecordCount", 0)

            if isinstance(results, dict) and results.get("Items") is not None:
                baseline_name = results.get("BaselineItemName")
                results = results.get("Items", [])
            elif (
                isinstance(results, list)
                and len(results) > 0
                and results[0].get("Items") is not None
            ):
                baseline_name = results[0].get("BaselineItemName")
                results = results[0].get("Items")

            item_list = []
            for item in results:
                item_data = extract_item_info(
                    item, gui_options, download_utils=download_utils
                )
                item_data.baseline_itemname = baseline_name
                item_list.append(item_data)

            cache_item = CacheItem()
            cache_item.item_list = item_list
            cache_item.file_path = cache_file
            cache_item.items_url = url
            cache_item.user_id = user_id
            cache_item.last_action = "fresh_data"
            cache_item.date_saved = time.time()
            cache_item.date_last_used = time.time()
            cache_item.total_records = total_records

            cache_thread.cached_item = cache_item
            # copy.deepcopy(item_list)

        if not use_cache:
            cache_thread = None

        return GetItemsResult(
            cache_file=cache_file,
            item_list=item_list,
            total_records=total_records,
            cache_thread=cache_thread,
        )


class CacheManagerThread(threading.Thread):
    def __init__(self) -> None:
        threading.Thread.__init__(self)
        self.cached_item: CacheItem | None = None
        self.gui_options: GuiOptions

    @staticmethod
    def get_data_hash(items: list) -> str:
        m = hashlib.md5()
        for item in items:
            item_string = "%s_%s_%s_%s_%s_%s" % (
                item.name,
                item.play_count,
                item.favorite,
                item.resume_time,
                item.recursive_unplayed_items_count,
                item.etag,
            )
            item_string = item_string.encode("UTF-8")
            m.update(item_string)

        return m.hexdigest()

    def run(self) -> None:
        log.debug("CacheManagerThread : Started")
        # log.debug("CacheManagerThread : Cache Item : {0}", self.cached_item.__dict__)

        download_utils = DownloadUtils()
        is_fresh = False

        if self.cached_item is None:
            log.debug("CacheManagerThread : No cached item")
            return

        # if the data is fresh then just save it
        # if the data is to old do a reload
        if (
            self.cached_item.date_saved is not None
            and (time.time() - self.cached_item.date_saved) < 20
            and self.cached_item.last_action == "fresh_data"
        ):
            is_fresh = True

        if (
            is_fresh
            and self.cached_item.item_list is not None
            and len(self.cached_item.item_list) > 0
        ):
            log.debug(
                "CacheManagerThread : Data is still fresh, not reloading from server"
            )
            cached_hash = self.get_data_hash(self.cached_item.item_list)
            self.cached_item.item_list_hash = cached_hash
            self.cached_item.last_action = "cached_data"
            self.cached_item.date_saved = time.time()
            self.cached_item.date_last_used = time.time()

            with FileLock(self.cached_item.file_path, timeout=5):
                with open(str(self.cached_item.file_path), "wb") as handle:
                    pickle.dump(
                        self.cached_item, handle, protocol=pickle.HIGHEST_PROTOCOL
                    )

        else:
            log.debug("CacheManagerThread : Reloading to recheck data hashes")
            cached_hash = self.cached_item.item_list_hash
            log.debug("CacheManagerThread : Cache Hash : {0}", cached_hash)

            data_manager = DataManager()
            results = data_manager.get_content(self.cached_item.items_url)
            if results is None:
                results = []

            if isinstance(results, dict) and results.get("Items") is not None:
                results = results.get("Items", [])
            elif (
                isinstance(results, list)
                and len(results) > 0
                and results[0].get("Items") is not None
            ):
                results = results[0].get("Items")

            total_records = 0
            if isinstance(results, dict):
                total_records = results.get("TotalRecordCount", 0)

            loaded_items = []
            for item in results:
                item_data = extract_item_info(
                    item, self.gui_options, download_utils=download_utils
                )
                loaded_items.append(item_data)

            if loaded_items is None or len(loaded_items) == 0:
                log.debug(
                    "CacheManagerThread : loaded_items is None or Empty so not saving it"
                )
                return

            loaded_hash = self.get_data_hash(loaded_items)
            log.debug("CacheManagerThread : Loaded Hash : {0}", loaded_hash)

            # if they dont match then save the data and trigger a content reload
            if cached_hash != loaded_hash:
                log.debug(
                    "CacheManagerThread : Hashes different, saving new data and reloading container"
                )

                self.cached_item.item_list = loaded_items
                self.cached_item.item_list_hash = loaded_hash
                self.cached_item.last_action = "fresh_data"
                self.cached_item.date_saved = time.time()
                self.cached_item.date_last_used = time.time()
                self.cached_item.total_records = total_records

                with FileLock(self.cached_item.file_path, timeout=5):
                    with open(str(self.cached_item.file_path), "wb") as handle:
                        pickle.dump(
                            self.cached_item, handle, protocol=pickle.HIGHEST_PROTOCOL
                        )

                log.debug("CacheManagerThread : Sending container refresh")
                time.sleep(1)
                xbmc.executebuiltin("Container.Refresh")

            else:
                self.cached_item.date_last_used = time.time()
                with FileLock(self.cached_item.file_path, timeout=5):
                    with open(str(self.cached_item.file_path), "wb") as handle:
                        pickle.dump(
                            self.cached_item, handle, protocol=pickle.HIGHEST_PROTOCOL
                        )
                log.debug("CacheManagerThread : Updating last used date for cache data")

        log.debug("CacheManagerThread : Exited")


def clear_cached_server_data() -> None:
    log.debug("clear_cached_server_data() called")

    addon_dir = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo("profile"))
    cache_path = os.path.join(addon_dir, "cache")
    dirs, files = xbmcvfs.listdir(cache_path)

    del_count = 0
    for filename in files:
        if filename.endswith(".lock"):
            lock_file = os.path.join(cache_path, filename)
            log.debug("Deleteing lock File: {0}", lock_file)
            xbmcvfs.delete(lock_file)
        if filename.startswith("cache_") and filename.endswith(".pickle"):
            cache_file = os.path.join(cache_path, filename)
            log.debug("Deleteing CacheFile: {0}", cache_file)
            xbmcvfs.delete(cache_file)
            del_count += 1

    msg = string_load(30394) % del_count
    xbmcgui.Dialog().ok(string_load(30393), msg)


def clear_old_cache_data() -> None:
    log.debug("clear_old_cache_data() : called")

    addon_dir = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo("profile"))
    cache_path = os.path.join(addon_dir, "cache")
    dirs, files = xbmcvfs.listdir(cache_path)

    del_count = 0
    for filename in files:
        if filename.startswith("cache_") and filename.endswith(".pickle"):
            log.debug("clear_old_cache_data() : Checking CacheFile : {0}", filename)

            cache_item = None
            for x in range(0, 5):
                try:
                    data_file = os.path.join(cache_path, filename)
                    with FileLock(data_file, timeout=5):
                        with open(data_file, "rb") as handle:
                            cache_item = pickle.load(handle)
                    break
                except Exception as error:
                    log.debug("clear_old_cache_data() : Pickle load error : {0}", error)
                    cache_item = None
                    xbmc.sleep(1000)

            if cache_item is not None:
                item_last_used = -1
                if cache_item.date_last_used is not None:
                    item_last_used = time.time() - cache_item.date_last_used

                log.debug(
                    "clear_old_cache_data() : Cache item last used : {0} sec ago",
                    item_last_used,
                )
                if item_last_used == -1 or item_last_used > (3600 * 24 * 7):
                    log.debug(
                        "clear_old_cache_data() : Deleting cache item age : {0}",
                        item_last_used,
                    )
                    data_file = os.path.join(cache_path, filename)
                    with FileLock(data_file, timeout=5):
                        xbmcvfs.delete(data_file)
                    del_count += 1
            else:
                log.debug("clear_old_cache_data() : Deleting unloadable cache item")
                data_file = os.path.join(cache_path, filename)
                with FileLock(data_file, timeout=5):
                    xbmcvfs.delete(data_file)

    log.debug("clear_old_cache_data() : Cache items deleted : {0}", del_count)
