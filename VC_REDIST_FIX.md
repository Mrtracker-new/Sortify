# Visual C++ Redistributable Fix for Sortify

## Issue

When running the Sortify application on some systems, the following error occurs:

```
Failed to execute script 'spacy_hook' due to unhandled exception: 
DLL load failed while importing numpy_ops: The specified module could not be found.
```

This error occurs because the NumPy and thinc libraries require the Visual C++ Redistributable package to be installed on the system. Without this package, the DLLs cannot be loaded properly.

## Solution

The following changes have been made to fix this issue:

1. Added Visual C++ Redistributable 2015-2022 to the installer (using a local file):
   ```ini
   ; Include Visual C++ Redistributable 2015-2022 (required for NumPy DLLs)
   ; Changed from external URL to local file that must be downloaded separately
   Source: "redist\vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: ignoreversion deleteafterinstall
   ```

2. Added a function to check if the Visual C++ Redistributable is already installed:
   ```pascal
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
   ```

3. Added a step to install the Visual C++ Redistributable during installation if needed:
   ```ini
   ; Install Visual C++ Redistributable (required for NumPy DLLs) if needed
   Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/install /quiet /norestart"; StatusMsg: "Installing Visual C++ Redistributable (required for NumPy)..."; Flags: waituntilterminated; Check: VCRedistNeedsInstall
   ```

4. Created additional hook files to ensure all necessary DLLs are included:
   - `hook-thinc.backends.numpy_ops.py`: Specifically targets the numpy_ops module that was causing the error
   - `hook-numpy.core.py`: Ensures all NumPy core DLLs are included

## Building the Application

To build the application with these fixes:

1. Run the prepare_build.bat script to download the Visual C++ Redistributable:
   ```
   prepare_build.bat
   ```
   This script will:
   - Create the redist directory if it doesn't exist
   - Download the Visual C++ Redistributable if it's not already present

2. Create the installer:
   ```
   build_installer.bat
   ```
   The build_installer.bat script has been updated to:
   - Check for the Visual C++ Redistributable before proceeding
   - Run the PyInstaller build process
   - Create the Inno Setup installer

## Distribution

The installer (`Sortify_Setup.exe`) now includes the Visual C++ Redistributable package and will install it automatically if needed. This makes it much easier to distribute the application to other laptops, as users don't need to manually install any dependencies.

## Verification

After building, verify that the application runs correctly by:

1. Installing the application on a clean system
2. Running the application and checking that it starts without DLL errors
3. Testing the core functionality to ensure everything works as expected

## Additional Notes

If you still encounter DLL loading issues after these changes, you may need to:

1. Check if there are other dependencies missing on the target system
2. Ensure that the Visual C++ Redistributable was installed correctly
3. Try running the application as an administrator for the first time