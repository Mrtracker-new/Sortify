<div align="center">

# 📦 Creating a Sortify Installer

This guide explains how to build a professional installer for Sortify using Inno Setup.

<img src="resources/icons/app_icon.ico" alt="Sortify Icon" width="64"/>

</div>

> **Note**: Creating your own installer is useful for developers or users who want to customize the installation process. If you just want to install Sortify, download the pre-built installer from the [Releases](https://github.com/Mrtracker-new/Sortify/releases) page.

## 🔧 Prerequisites

<details open>
<summary><b>Required Software & Dependencies</b></summary>
<br>

1. **Inno Setup**
   - Download and install [Inno Setup](https://jrsoftware.org/isdl.php) (version 6 or newer recommended)
   - During installation, select the option to add Inno Setup to your PATH

2. **Python Environment**
   - Python 3.8 or newer installed and added to PATH
   - All dependencies installed: `pip install -r requirements.txt`
   - Virtual environment activated (if using one)

3. **Build Tools**
   - Windows: Microsoft Visual C++ Build Tools (for some Python packages)
   - Optional: UPX for executable compression (automatically used if available)

4. **Code Signing** (Optional but Recommended)
   - A valid code signing certificate if you want to sign the installer
   - SignTool.exe from the Windows SDK (if signing)

</details>

## 🚀 Building the Installer

<details open>
<summary><b>Option 1: Using the Automated Script (Recommended)</b></summary>
<br>

1. Simply run the `build_installer.bat` script from the command prompt or by double-clicking:
   ```batch
   build_installer.bat
   ```

   This automated script will:
   - Build the Sortify application using PyInstaller
   - Create an installer directory if it doesn't exist
   - Build the installer using Inno Setup
   - Handle all necessary file copying and configuration

2. The installer will be created in the `installer` directory as `Sortify_Setup.exe`

> **Note**: If you encounter Windows Defender warnings during the build process, see [DEFENDER_SOLUTIONS.md](DEFENDER_SOLUTIONS.md) for solutions.

</details>

<details>
<summary><b>Option 2: Safe Build Process (For Security-Sensitive Environments)</b></summary>
<br>

If you're in a security-sensitive environment or experiencing issues with antivirus software, use the safe build process:

1. Run the `build_installer_safe.bat` script:
   ```batch
   build_installer_safe.bat
   ```

   This script uses modified build parameters that are less likely to trigger antivirus warnings.

</details>

<details>
<summary><b>Option 3: Manual Build Process (For Advanced Customization)</b></summary>
<br>

If you want more control over the build process or need to customize specific aspects:

1. First, build the application using PyInstaller:
   ```batch
   python build.py
   ```
   
   This creates the executable in the `dist` directory.

2. Then, compile the Inno Setup script:
   - Open Inno Setup Compiler
   - Open the `Sortify.iss` file
   - Review and modify settings if needed
   - Click on Build > Compile

3. The installer will be created in the `installer` directory

> **Advanced**: You can modify `build.py` to customize PyInstaller options and `Sortify.iss` to customize the installer behavior.

</details>

### Build Process Details

<details>
<summary><b>What Happens During the Build</b></summary>
<br>

1. **PyInstaller Packaging**:
   - All Python code is compiled and packaged
   - Required libraries and dependencies are included
   - Resources (icons, etc.) are bundled
   - A standalone executable is created

2. **Inno Setup Compilation**:
   - The executable and supporting files are packaged into an installer
   - Start menu shortcuts are configured
   - Registry entries are set up (if needed)
   - Uninstaller is created

3. **Optional Signing**:
   - If code signing is configured, both the executable and installer are signed
   - This improves security and reduces false positive antivirus detections

</details>

## ⚙️ Customizing the Installer

<details>
<summary><b>Modifying the Inno Setup Script</b></summary>
<br>

You can customize the installer by editing the `Sortify.iss` file. Here are the most common customizations:

### Basic Information

```ini
; Find and modify these values at the top of the .iss file
#define MyAppName "Sortify"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Your Name or Organization"
#define MyAppURL "https://github.com/Mrtracker-new/Sortify"
```

### Installation Options

```ini
[Setup]
; Default installation directory
DefaultDirName={autopf}\{#MyAppName}

; Allow user to choose installation directory?
DisableDirPage=no

; Allow user to choose Start Menu folder?
DisableProgramGroupPage=yes

; Require administrator privileges?
PrivilegesRequired=admin
```

### Files to Include

```ini
[Files]
; Main executable
Source: "dist\Sortify\Sortify.exe"; DestDir: "{app}"; Flags: ignoreversion

; Add additional files as needed
Source: "path\to\additional\file"; DestDir: "{app}\subfolder"; Flags: ignoreversion
```

### Shortcuts

```ini
[Icons]
; Desktop shortcut
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

; Start Menu shortcut
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
```

### Custom Installation Steps

```ini
[Run]
; Run the application after installation
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

; Add additional post-installation steps
Filename: "{app}\additional_setup.exe"; Parameters: "/silent"; Flags: runhidden
```

### Registry Entries

```ini
[Registry]
; Add registry entries
Root: HKLM; Subkey: "SOFTWARE\{#MyAppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"
```

</details>

<details>
<summary><b>Advanced Customization</b></summary>
<br>

### Custom Installer Pages

You can add custom pages to the installer for additional options or information:

```ini
[Code]
procedure InitializeWizard;
begin
  // Create a custom page
  CreateCustomPage(wpWelcome, 'Custom Page Title', 'Custom page description');
end;
```

### Multilingual Support

Add support for multiple languages:

```ini
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
```

### Code Signing

To sign your installer (requires a code signing certificate):

```ini
[Setup]
SignTool=signtool sign /f "certificate.pfx" /p "password" /t http://timestamp.digicert.com $f
```

</details>

## 📦 Distributing the Installer

<details>
<summary><b>Distribution Methods</b></summary>
<br>

The final installer (`Sortify_Setup.exe`) can be distributed to users via:

### Online Distribution

- **GitHub Releases**: Upload the installer to your repository's Releases page
  - Create a new release with version tag
  - Add release notes describing changes
  - Upload the installer as an asset
  - Provide a direct download link

- **Website Download**: Host the installer on your website
  - Create a downloads page with clear instructions
  - Include system requirements
  - Provide checksums (SHA-256) for security verification

- **Cloud Storage**: Use services like Google Drive, Dropbox, or OneDrive
  - Create a shareable link
  - Set appropriate permissions (public or restricted)

### Offline Distribution

- **USB Drives**: Copy the installer to USB drives for physical distribution
  - Include a README file with installation instructions
  - Consider autorun functionality (though this may trigger security warnings)

- **Local Network**: Share via local network for organizational deployment
  - Place on a network share
  - Use Group Policy for automated deployment (in corporate environments)

</details>

<details>
<summary><b>Installation Instructions for End Users</b></summary>
<br>

Provide these instructions to your users:

1. Download the `Sortify_Setup.exe` installer
2. Right-click the installer and select "Run as administrator"
3. If Windows SmartScreen appears, click "More info" and then "Run anyway"
4. Follow the on-screen instructions to complete installation
5. Launch Sortify from the desktop shortcut or Start menu

> **Note**: All necessary dependencies are included in the installer. No additional software installation is required.

</details>

---

<div align="center">

**Need help?** [Open an issue](https://github.com/Mrtracker-new/Sortify/issues) on GitHub for assistance with building or distributing the installer.

</div>