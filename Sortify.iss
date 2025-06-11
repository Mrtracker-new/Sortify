#define MyAppName "Sortify"
#define MyAppVersion "1.0"
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
OutputDir=installer
OutputBaseFilename=Sortify_Setup
SetupIconFile=resources\icons\app_icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; Add uninstall information to Add/Remove Programs
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
; Improve Windows Defender detection by adding more metadata
VersionInfoCompany={#MyAppPublisher}
VersionInfoCopyright="Copyright (C) 2024 {#MyAppPublisher}"
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
Source: "dist\Sortify.exe\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Ensure critical Python DLLs are copied to the root directory
Source: "dist\Sortify.exe\_internal\python*.dll"; DestDir: "{app}"; Flags: ignoreversion
; Create a batch file launcher as a fallback
Source: "launcher.bat"; DestDir: "{app}"; Flags: ignoreversion

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startmenuicon
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

; Uncomment the following section when you have a code signing certificate
; [Code]
; // This section enables code signing for the installer
; // You'll need to obtain a code signing certificate and configure these settings
; // SignTool=signtool.exe sign /f "$f" /p mypassword /t http://timestamp.digicert.com $f