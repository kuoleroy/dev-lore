@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
set count=0

for %%F in (*.mp4 *.mkv *.mov *.avi *.webm *.flv *.ts *.m4v) do (
    ffmpeg -y -i "%%F" -c:v copy -an "%%~nF.noaudio.mp4" 2>nul
    if exist "%%~nF.noaudio.mp4" (
        set /a count+=1
    )
)

echo Done: %count% files
pause