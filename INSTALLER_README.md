# Creating a Sortify Installer

This guide explains how to build a professional installer for Sortify using Inno Setup.

## Prerequisites

1. Install [Inno Setup](https://jrsoftware.org/isdl.php) (version 6 or newer recommended)
2. Make sure all Python dependencies are installed: `pip install -r requirements.txt`

## Building the Installer

### Option 1: Using the build_installer.bat script

1. Simply run the `build_installer.bat` script:
   ```
   build_installer.bat
   ```

   This will:
   - Build the Sortify application using PyInstaller
   - Create an installer directory if it doesn't exist
   - Build the installer using Inno Setup

2. The installer will be created in the `installer` directory as `Sortify_Setup.exe`

### Option 2: Manual process

1. First, build the application using PyInstaller:
   ```
   python build.py
   ```

2. Then, compile the Inno Setup script:
   - Open Inno Setup Compiler
   - Open the `Sortify.iss` file
   - Click on Build > Compile

3. The installer will be created in the `installer` directory

## Customizing the Installer

You can customize the installer by editing the `Sortify.iss` file:

- Change application metadata (name, version, publisher)
- Modify installation directory options
- Add additional files to be included in the installer
- Configure desktop shortcuts and start menu entries
- Add custom installation steps or registry entries

## Distributing the Installer

The final installer (`Sortify_Setup.exe`) can be distributed to users via:

- Direct download
- File sharing services
- USB drives

Users can then run the installer to install Sortify on their Windows systems with all necessary dependencies included.