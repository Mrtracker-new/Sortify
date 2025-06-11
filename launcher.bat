@echo off
cd "%~dp0"
if exist "%~dp0\python312.dll" (
    start "" "%~dp0\python.exe" "%~dp0\main.py"
) else (
    echo Error: Python DLL not found in the expected location.
    echo Please reinstall the application.
    pause
)