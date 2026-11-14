@echo off
REM =====================================================================
REM  BOVD - one-click local start (Windows)
REM  Runs the Python server on http://127.0.0.1:8765 and opens the browser.
REM  Nothing leaves this computer. Hackathon prototype - not a medical device.
REM =====================================================================
chcp 65001 >nul
title BOVD
cd /d "%~dp0"

set "PY="
where py >nul 2>nul
if %errorlevel%==0 set "PY=py -3"
if defined PY goto checkver
where python >nul 2>nul
if %errorlevel%==0 set "PY=python"
if defined PY goto checkver
echo.
echo [X] Python 3.10+ was not found.
echo     Install it from https://www.python.org/downloads/  and tick "Add python.exe to PATH".
echo     Then double-click start.bat again.
pause
exit /b 1

:checkver
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if not %errorlevel%==0 (
  echo [X] Python 3.10 or newer is required. Found an older version or the Microsoft Store stub.
  pause
  exit /b 1
)

REM Optional: fast audited AES-GCM. If offline, the built-in pure-Python AES-256-GCM is used.
%PY% -c "import cryptography" >nul 2>nul
if not %errorlevel%==0 (
  echo [i] Trying to install optional package "cryptography" - faster encryption...
  %PY% -m pip install --disable-pip-version-check -q cryptography >nul 2>nul
  if not errorlevel 1 echo [OK] cryptography installed.
  if errorlevel 1 echo [i] Offline or pip unavailable - using built-in pure-Python AES-256-GCM. First start takes about 20 seconds.
)

REM Optional camera posture check: NOT installed here (large download, slows every start).
REM Run install_camera.bat once if you want automatic posture checks. Without it the app uses manual mode.
%PY% -c "import cv2, mediapipe" >nul 2>nul
if errorlevel 1 (
  echo [i] Camera posture check: manual mode. To enable automatic checks, run install_camera.bat once.
) else (
  if not exist "data\models\pose_landmarker_lite.task" %PY% scripts\fetch_models.py
)

echo.
echo  Starting BOVD ...  close this window or press Ctrl+C to stop.
echo  Demo users: astro1 / cmo1 / bhs1 / surgeon1 / research1   password: astra2026
echo.
%PY% -m astra.server
pause
