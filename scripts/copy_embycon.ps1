$KODIPATH = "c:\tools\Kodi21"
$REPOROOT = git rev-parse --show-toplevel
$PLUGINROOT = "$REPOROOT\plugin.video.embycon"

# Remove existing plugin directory
if (Test-Path "$KODIPATH\addons\plugin.video.embycon") {
    Remove-Item -Path "$KODIPATH\addons\plugin.video.embycon" -Recurse -Force
}

# Create the plugin directory
New-Item -Path "$KODIPATH\addons\plugin.video.embycon" -ItemType Directory -Force | Out-Null

# Copy individual files
Copy-Item -Path "$PLUGINROOT\addon.xml" -Destination "$KODIPATH\addons\plugin.video.embycon\" -Force
Copy-Item -Path "$PLUGINROOT\default.py" -Destination "$KODIPATH\addons\plugin.video.embycon\" -Force
Copy-Item -Path "$PLUGINROOT\fanart.jpg" -Destination "$KODIPATH\addons\plugin.video.embycon\" -Force -ErrorAction SilentlyContinue
Copy-Item -Path "$PLUGINROOT\icon.png" -Destination "$KODIPATH\addons\plugin.video.embycon\" -Force -ErrorAction SilentlyContinue
# Copy-Item -Path "$PLUGINROOT\kodi.png" -Destination "$KODIPATH\addons\plugin.video.embycon\" -Force
Copy-Item -Path "$PLUGINROOT\service.py" -Destination "$KODIPATH\addons\plugin.video.embycon\" -Force

# Copy resources directory recursively
Copy-Item -Path "$PLUGINROOT\resources" -Destination "$KODIPATH\addons\plugin.video.embycon\resources" -Recurse -Force

# Change to Kodi directory and launch Kodi in portable mode
#Set-Location "$KODIPATH"
Start-Process "$KODIPATH\kodi.exe" -ArgumentList "-p"
