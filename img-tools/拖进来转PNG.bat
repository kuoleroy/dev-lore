@echo off
setlocal
rem 用法：把 .webp 文件或整个文件夹拖到本文件图标上
rem 输出：同目录下 同名 .png（保留透明通道，无损）

set "PY=C:/Users/admin/miniconda3/envs/aligner/python.exe"
if not exist "%PY%" set "PY=python"

if "%~1"=="" (
  echo 请把 webp 文件或文件夹拖到本文件图标上再松手。
  pause
  exit /b
)

"%PY%" "%~dp0webp2png.py" %*

echo.
pause
