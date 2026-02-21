#define MyAppName "Sortify"
#define MyAppVersion "2026.2.22"
#define MyAppPublisher "Rolan Lobo"
#define MyAppURL ""
#define MyAppExeName "Sortify.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application. Do not use the same AppId value in installers for other applications.
AppId={{8A7D8AE3-9F0D-4B2B-8D1C-F5A3C8E5D2A1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
; Uncomment the following line to run in non administrative install mode (install for current user only.)
;PrivilegesRequired=lowest
OutputDir=..\installer
OutputBaseFilename=Sortify_Setup
SetupIconFile=..\resources\icons\app_icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; Add uninstall information to Add/Remove Programs
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
; Improve Windows Defender detection by adding more metadata
VersionInfoCompany={#MyAppPublisher}
VersionInfoCopyright="Copyright (C) 2026 {#MyAppPublisher}"
VersionInfoDescription="Sortify - AI-powered file organization tool"
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startmenuicon"; Description: "Create a Start Menu shortcut"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Copy all files from the dist directory
Source: "..\dist\Sortify.exe\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Ensure critical Python DLLs are copied to the root directory
Source: "..\dist\Sortify.exe\_internal\python*.dll"; DestDir: "{app}"; Flags: ignoreversion
; Include Visual C++ Redistributable if present (download separately from https://aka.ms/vs/17/release/vc_redist.x64.exe)
; Uncomment the next line if you have downloaded vc_redist.x64.exe into a 'redist' folder:
; Source: "..\redist\vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: ignoreversion deleteafterinstall

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;

// Check if Visual C++ Redistributable is already installed
function VCRedistNeedsInstall: Boolean;
var
  Version: String;
  InstallVCRedist: Boolean;
begin
  // Check for VC++ 2015-2022 Redistributable (14.0)
  RegQueryStringValue(HKEY_LOCAL_MACHINE,
    'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64', 'Version', Version);
  
  // If Version is empty, we need to install the redistributable
  InstallVCRedist := (Version = '');
  
  // Also check the 32-bit registry view
  if InstallVCRedist then
  begin
    RegQueryStringValue(HKEY_LOCAL_MACHINE,
      'SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\x64', 'Version', Version);
    InstallVCRedist := (Version = '');
  end;
  
  Result := InstallVCRedist;
end;

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startmenuicon
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Install Visual C++ Redistributable (required for NumPy DLLs) if needed
; Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/install /quiet /norestart"; StatusMsg: "Installing Visual C++ Redistributable (required for NumPy)..."; Flags: waituntilterminated; Check: VCRedistNeedsInstall
; Launch the application after installation
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

; Uncomment the following section when you have a code signing certificate
; [Code]
; // This section enables code signing for the installer
; // You'll need to obtain a code signing certificate and configure these settings
; // SignTool=signtool.exe sign /f "$f" /p mypassword /t http://timestamp.digicert.com $f