@echo off
REM Runs the test suite + standard-library coverage report (Windows).
cd /d "%~dp0"
set "PY=py -3"
where py >nul 2>nul || set "PY=python"
%PY% -m pip install --disable-pip-version-check -q pytest >nul 2>nul
%PY% scripts\coverage_lite.py
pause
