PS4 Profile Studio @VERSION@
=============================

Portable build - no installation and no Python required.

HOW TO RUN
----------
1. Extract this whole ZIP to a folder (right-click > Extract All).
   Do not run the .exe from inside the ZIP.
2. Open the extracted "PS4 Profile Studio" folder.
3. Double-click "PS4 Profile Studio.exe".

Windows may show "Windows protected your PC" because the app is not
code-signed. Click "More info" > "Run anyway".

REQUIREMENTS
------------
- Windows 10 or 11, 64-bit
- A PS4 on the same network running GoldHEN with its FTP server enabled
  (default port 2121)

DATA
----
The list of consoles you have connected to (with their names) and profile
backups are stored next to the executable, so the whole folder stays portable.
If that folder is read-only (for example under Program Files), the app uses
%APPDATA%\PS4ProfileStudio instead.

NOTES
-----
- version.json on the console is never uploaded or modified.
- Custom profile names only appear on activated profiles. For offline
  activation use Apollo Save Tool > "Activate Offline Account".
- Avatar changes work on any profile.

LICENSE
-------
MIT. Bundled third-party components are listed in THIRD-PARTY-NOTICES.txt.
Full documentation: https://github.com/omarfx83/ps4-profile-studio
