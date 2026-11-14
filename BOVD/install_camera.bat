@echo off
REM =====================================================================
REM  BOVD - optional: enable automatic camera posture checks (run ONCE)
REM  Installs OpenCV + MediaPipe (about 100-150 MB) and downloads the pose model (~5 MB).
REM  The camera checks posture only; it never measures vital signs. Frames are never stored.
REM =====================================================================
chcp 65001 >nul
title BOVD - camera setup
cd /d "%~dp0"
set "PY="
where py >nul 2>nul
if %errorlevel%==0 set "PY=py -3"
if not defined PY set "PY=python"

%PY% -c "import sys; sys.exit(0 if (3, 9) <= sys.version_info[:2] <= (3, 12) else 1)" >nul 2>nul
if errorlevel 1 (
  echo [!] MediaPipe supports Python 3.9 to 3.12. Your Python version may not be supported.
  echo     BOVD still works in manual posture mode. Trying anyway...
)
echo [1/2] Installing opencv-python-headless and mediapipe (progress shown below) ...
%PY% -m pip install --disable-pip-version-check opencv-python-headless mediapipe
if errorlevel 1 (
  echo [X] Installation failed - BOVD keeps working in manual posture mode.
  pause
  exit /b 1
)
echo [2/2] Downloading the pose model ...
%PY% scripts\fetch_models.py
echo.
echo [OK] Done. Restart start.bat - the Posture check page will show tier "full".
pause
