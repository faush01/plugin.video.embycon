import xml.etree.ElementTree as ET
import subprocess
from shutil import copy2, copytree, rmtree
import os
import sys


def ignore_files(path, item_list):
	file_list = [
		"skin.estuary",
		]
	return file_list


embycon_repo_path = "C:\\Development\\emby\\embycon_kodi_repo\\repo\\release\\"
zip_path = "c:\\Program Files\\7-Zip\\7z.exe"

git_result = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
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
if version.find("1.11") > -1:
	ver_name = "v20_nexus"
elif version.find("1.10") > -1:
	ver_name = "v19_matrix"
else:
	ver_name = "v17_krypton"

package_path = os.path.join(package_path, ver_name)

print (package_path + " (" + version + ")")

try:
	rmtree(os.path.join(package_path, addon_id))
except FileNotFoundError:
	pass

copytree(addon_path, os.path.join(package_path, addon_id), ignore=ignore_files)

zip_name = addon_id + "-" + version + ".zip"

os.chdir(package_path)
cmd_7zip = [zip_path, "a", zip_name, addon_id]
sp = subprocess.Popen(cmd_7zip, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
sp.wait()
os.chdir("..\\..")

copy2(os.path.join(package_path, addon_id, "addon.xml"), os.path.join(package_path, "addon.xml"))

embycon_repo_path = os.path.join(embycon_repo_path, ver_name, "plugin.video.embycon")
copy2(os.path.join(package_path, "addon.xml"), os.path.join(embycon_repo_path, "addon.xml"))
copy2(os.path.join(package_path, zip_name), os.path.join(embycon_repo_path, zip_name))

try:
	rmtree(os.path.join(package_path, addon_id))
except FileNotFoundError:
	pass
