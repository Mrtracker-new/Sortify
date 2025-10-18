@echo off
setlocal

:: Build with antivirus-friendly settings (--noupx)
echo Building Sortify with antivirus-friendly settings...
python build_tools\build.py

:: Check if PyInstaller build was successful
if not exist dist\Sortify.exe\Sortify.exe (
    echo ERROR: PyInstaller build failed. Sortify.exe not found.
    pause
    exit /b 1
)

:: Optional: Sign the PyInstaller executable if you have a code signing certificate
:: Uncomment and modify the following lines when you have a certificate
:: echo Signing Sortify.exe with code signing certificate...
:: "C:\Program Files (x86)\Windows Kits\10\bin\10.0.19041.0\x64\signtool.exe" sign /f "path\to\your\certificate.pfx" /p "your-password" /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 "dist\Sortify.exe\Sortify.exe"
:: if %ERRORLEVEL% neq 0 (
::    echo ERROR: Failed to sign Sortify.exe
::    pause
::    exit /b 1
:: )

echo Creating installer directory...
if not exist installer mkdir installer

echo Building installer with Inno Setup...
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" build_tools\Sortify.iss

if %ERRORLEVEL% neq 0 (
    echo ERROR: Inno Setup compilation failed.
    pause
    exit /b 1
)

:: Optional: Sign the installer if you have a code signing certificate
:: Uncomment and modify the following lines when you have a certificate
:: echo Signing Sortify_Setup.exe with code signing certificate...
:: "C:\Program Files (x86)\Windows Kits\10\bin\10.0.19041.0\x64\signtool.exe" sign /f "path\to\your\certificate.pfx" /p "your-password" /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 "installer\Sortify_Setup.exe"
:: if %ERRORLEVEL% neq 0 (
::    echo ERROR: Failed to sign installer
::    pause
::    exit /b 1
:: )

echo.
echo Installer created successfully! Check the installer directory.
echo.
echo NOTE: To prevent Windows Defender false positives, consider:
echo 1. Obtaining a code signing certificate and uncommenting the signing steps
echo 2. Submitting your installer to Microsoft for malware analysis at:
echo    https://www.microsoft.com/en-us/wdsi/filesubmission
echo.

pause
