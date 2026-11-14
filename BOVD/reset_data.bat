@echo off
REM Deletes the local database and keys so the demo data is re-created on next start.
cd /d "%~dp0"
echo This deletes data\db (all local health data, keys, black box). 
set /p ok=Type YES to continue: 
if /i not "%ok%"=="YES" exit /b 0
rmdir /s /q data\db
echo Done. Run start.bat to re-create the demo crew.
pause
