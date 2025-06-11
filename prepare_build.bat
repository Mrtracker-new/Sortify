@echo off
echo Preparing build environment for Sortify...

:: Create redist directory if it doesn't exist
if not exist redist (
    echo Creating redist directory...
    mkdir redist
)

:: Download Visual C++ Redistributable if it doesn't exist
if not exist redist\vc_redist.x64.exe (
    echo Downloading Visual C++ Redistributable...
    powershell -Command "Invoke-WebRequest -Uri 'https://aka.ms/vs/17/release/vc_redist.x64.exe' -OutFile 'redist\vc_redist.x64.exe'"
    if %ERRORLEVEL% neq 0 (
        echo Failed to download Visual C++ Redistributable.
        echo Please download it manually from https://aka.ms/vs/17/release/vc_redist.x64.exe
        echo and place it in the redist directory.
        exit /b 1
    )
    echo Visual C++ Redistributable downloaded successfully.
) else (
    echo Visual C++ Redistributable already exists.
)

echo Build environment prepared successfully.
echo You can now run build_installer.bat to create the installer.