$KODIPATH = "c:\tools\Kodi21"
$REPOROOT = git rev-parse --show-toplevel

# Remove existing plugin directory
if (Test-Path "$KODIPATH\addons\plugin.video.embycon") {
    Remove-Item -Path "$KODIPATH\addons\plugin.video.embycon" -Recurse -Force
}

# Create the plugin directory
New-Item -Path "$KODIPATH\addons\plugin.video.embycon" -ItemType Directory -Force | Out-Null

# Copy individual files
Copy-Item -Path "$REPOROOT\addon.xml" -Destination "$KODIPATH\addons\plugin.video.embycon\" -Force
Copy-Item -Path "$REPOROOT\default.py" -Destination "$KODIPATH\addons\plugin.video.embycon\" -Force
Copy-Item -Path "$REPOROOT\fanart.jpg" -Destination "$KODIPATH\addons\plugin.video.embycon\" -Force -ErrorAction SilentlyContinue
Copy-Item -Path "$REPOROOT\icon.png" -Destination "$KODIPATH\addons\plugin.video.embycon\" -Force -ErrorAction SilentlyContinue
# Copy-Item -Path "$REPOROOT\kodi.png" -Destination "$KODIPATH\addons\plugin.video.embycon\" -Force
Copy-Item -Path "$REPOROOT\service.py" -Destination "$KODIPATH\addons\plugin.video.embycon\" -Force

# Copy resources directory recursively
Copy-Item -Path "$REPOROOT\resources" -Destination "$KODIPATH\addons\plugin.video.embycon\resources" -Recurse -Force

# Change to Kodi directory and launch Kodi in portable mode
#Set-Location "$KODIPATH"
Start-Process "$KODIPATH\kodi.exe" -ArgumentList "-p"
