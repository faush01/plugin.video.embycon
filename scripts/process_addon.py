import xml.etree.ElementTree as ET
import subprocess
from shutil import copy2, copytree, rmtree
import os
import sys
import zipfile


def ignore_files(path, item_list):
    file_list = [
        # "skin.estuary",
    ]
    return file_list


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

copytree(addon_path, os.path.join(package_path, addon_id), ignore=ignore_files)

zip_name = addon_id + "-" + version + ".zip"

# Create zip file using Python's zipfile library
zip_file_path = os.path.join(package_path, zip_name)
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
