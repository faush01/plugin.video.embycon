from __future__ import annotations
import xml.etree.ElementTree as ET
import subprocess
from shutil import copy2, copytree, rmtree
import os
import zipfile


def copy_specified_paths(
    src_root: str, dest_root: str, paths_to_copy: list[str]
) -> None:
    """Copy only the specified paths from src_root to dest_root."""
    for path in paths_to_copy:
        src_path = os.path.join(src_root, path)
        dest_path = os.path.join(dest_root, path)

        if not os.path.exists(src_path):
            continue

        # Create parent directory if needed
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)

        if os.path.isfile(src_path):
            copy2(src_path, dest_path)
        elif os.path.isdir(src_path):
            copytree(src_path, dest_path, dirs_exist_ok=True)


embycon_repo_path = "C:\\Development\\emby\\embycon_kodi_repo\\repo\\release\\"

git_result = subprocess.run(
    ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
)
repo_path = git_result.stdout.strip()
addon_path = os.path.join(repo_path, "plugin.video.embycon")

print("Git repo path: " + repo_path)
print("Addon path   : " + addon_path)

package_path = os.path.join(repo_path, "package")

tree = ET.parse(os.path.join(addon_path, "addon.xml"))
root = tree.getroot()
addon_id = root.attrib["id"]
version = root.attrib["version"]

ver_name = ""
if version.find("1.12") > -1 or version.find("1.11") > -1:
    ver_name = "v20_nexus"
elif version.find("1.10") > -1:
    ver_name = "v19_matrix"
else:
    ver_name = "v17_krypton"

package_path = os.path.join(package_path, ver_name)

print(package_path + " (" + version + ")")

try:
    rmtree(os.path.join(package_path, addon_id))
except FileNotFoundError:
    pass

# List of paths to copy (relative to addon_path)
paths_to_copy = [
    "addon.xml",
    "default.py",
    "service.py",
    "context.py",
    "icon.png",
    "fanart.jpg",
    "resources/__init__.py",
    "resources/settings.xml",
    "resources/language",
    "resources/lib",
    "resources/skins/default",
    "resources/skins/skin.estuary/21/xml",
]
copy_specified_paths(addon_path, os.path.join(package_path, addon_id), paths_to_copy)

zip_name = addon_id + "-" + version + ".zip"

# Create zip file using Python's zipfile library
zip_file_path = os.path.join(package_path, zip_name)

# Delete existing zip file if it exists
if os.path.exists(zip_file_path):
    os.remove(zip_file_path)

addon_folder = os.path.join(package_path, addon_id)
with zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED) as zipf:
    for root_dir, dirs, files in os.walk(addon_folder):
        for file in files:
            file_path = os.path.join(root_dir, file)
            arcname = os.path.relpath(file_path, package_path)
            zipf.write(file_path, arcname)

copy2(
    os.path.join(package_path, addon_id, "addon.xml"),
    os.path.join(package_path, "addon.xml"),
)

embycon_repo_path = os.path.join(embycon_repo_path, ver_name, "plugin.video.embycon")
copy2(
    os.path.join(package_path, "addon.xml"),
    os.path.join(embycon_repo_path, "addon.xml"),
)
copy2(os.path.join(package_path, zip_name), os.path.join(embycon_repo_path, zip_name))

try:
    rmtree(os.path.join(package_path, addon_id))
except FileNotFoundError as err:
    print(err)
