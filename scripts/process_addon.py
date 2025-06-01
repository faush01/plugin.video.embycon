import xml.etree.ElementTree as ET
import subprocess
from shutil import copy2, copytree, rmtree
import os
import sys

package_path = "package"

def ignore_files(path, item_list):
	return [".idea", ".git", ".gitignore", "scripts", "venv", "package"]

repo_path = "C:\\Development\\GitHub\\embycon_kodi_repo\\repo\\release\\"
zip_path = "c:\\Program Files\\7-Zip\\7z.exe"

addon_path = sys.argv[1]

tree = ET.parse(addon_path + "\\addon.xml")
root = tree.getroot()
id = root.attrib["id"]
version = root.attrib["version"]

ver_name = ""
if version.find("1.11") > -1:
	ver_name = "v20_nexus"
elif version.find("1.10") > -1:
	ver_name = "v19_matrix"
else:
	ver_name = "v17_krypton"

package_path = package_path + "\\" + ver_name

print (package_path + " (" + version + ")")

try:
	rmtree(package_path + "\\" + id)
except FileNotFoundError as err:
	pass
	
copytree(addon_path, package_path + "\\" + id, ignore=ignore_files)

zip_name = id + "-" + version + ".zip"

os.chdir(package_path)
cmd_7zip = [zip_path, "a", zip_name, id]
sp = subprocess.Popen(cmd_7zip, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
sp.wait()
os.chdir("..\\..")

copy2(package_path + "\\" + id + "\\addon.xml", package_path + "\\addon.xml")

repo_path = repo_path + ver_name + "\\plugin.video.embycon\\"
copy2(package_path + "\\addon.xml", repo_path + "addon.xml")
copy2(package_path + "\\" + zip_name, repo_path + zip_name)

try:
	rmtree(package_path + "\\" + id)
except FileNotFoundError as err:
	pass

