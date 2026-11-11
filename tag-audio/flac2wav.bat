@echo off
setlocal enabledelayedexpansion

rem 用法：把音频文件（flac/mp3/m4a/wav）直接拖到这个 bat 图标上
rem 输出：同目录下 同名 .wav，48kHz / 16bit / 双声道（pcm_s16le）

if "%~1"=="" (
  echo 请把音频文件拖到本文件图标上再松手。
  pause
  exit /b
)

set OK=0
set FAIL=0

:loop
if "%~1"=="" goto done

set "SRC=%~1"
set "DIR=%~dp1"
set "NAME=%~n1"
set "OUT=%DIR%%NAME%.wav"

echo.
echo ============================================
echo 处理: %~nx1

ffmpeg -hide_banner -loglevel error -y -i "%SRC%" -vn -acodec pcm_s16le -ar 48000 -ac 2 "%OUT%"
if errorlevel 1 (
  echo [失败] %~nx1
  set /a FAIL+=1
) else (
  echo [完成] %NAME%.wav
  set /a OK+=1
)

shift
goto loop

:done
echo.
echo ============================================
echo 成功: %OK% 个    失败: %FAIL% 个
echo 规格: 48kHz / 16bit / 双声道 WAV
echo ============================================
pause
