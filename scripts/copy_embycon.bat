set KODIPATH=c:\tools\Kodi20

del /F /Q /S %KODIPATH%\addons\plugin.video.embycon
rmdir /Q /S %KODIPATH%\addons\plugin.video.embycon

xcopy /Y addon.xml %KODIPATH%\addons\plugin.video.embycon\
xcopy /Y default.py %KODIPATH%\addons\plugin.video.embycon\
xcopy /Y fanart.jpg %KODIPATH%\addons\plugin.video.embycon\
xcopy /Y icon.png %KODIPATH%\addons\plugin.video.embycon\
rem xcopy /Y kodi.png %KODIPATH%\Kodi\addons\plugin.video.embycon\
xcopy /Y service.py %KODIPATH%\addons\plugin.video.embycon\

xcopy /E /Y resources %KODIPATH%\addons\plugin.video.embycon\resources\

cd "%KODIPATH%"
kodi.exe -p
