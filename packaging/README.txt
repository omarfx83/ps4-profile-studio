PS4 Profile Studio @VERSION@
=============================

Builds a PS4 profile avatar set from one image, sends it to the console over
GoldHEN FTP, and edits a profile's display name with a built-in picker of
149 PS4 symbols and 371 emoji.

Portable build - no installation and no Python required.

HOW TO RUN
----------
1. Extract this whole ZIP to a folder (right-click > Extract All).
   Do not run the .exe from inside the ZIP.
2. Open the extracted "PS4 Profile Studio" folder.
3. Double-click "PS4 Profile Studio.exe".

Windows may show "Windows protected your PC" because the app is not
code-signed. Click "More info" > "Run anyway".

QUICK START
-----------
1. Start GoldHEN on the PS4 and make sure its FTP server is enabled
   (default port 2121).
2. Run the app, enter the console's IP address, click Connect.
3. Avatar tab > Editor: open a photo, adjust the crop, Apply Crop.
4. Avatar tab > Send: pick a user, then Send avatar.
5. Profile tab: change a profile's display name with the symbol and emoji
   picker.

REQUIREMENTS
------------
- Windows 10 or 11, 64-bit
- A PS4 on the same network running GoldHEN, with its FTP server enabled
  (default port 2121). GoldHEN shows the console's IP on screen; the PS4
  also lists it under Settings > Network > View Connection Status.

DATA
----
The list of consoles you connect to (with their names) and the profile
backups are stored next to the executable, so the whole folder stays
portable. If that folder is read-only (for example under Program Files),
the app uses %APPDATA%\PS4ProfileStudio instead.

To uninstall, delete this folder.

NOTES
-----
- version.json on the console is never uploaded or modified.
- Custom profile names only appear on activated profiles. For offline
  activation use Apollo Save Tool > "Activate Offline Account".
- Avatar changes work on any profile.

SUPPORT
-------
Free and open source: no ads, no locked features. If this app saved you time,
you can leave a tip here:
https://ko-fi.com/omarfx83

LICENSE
-------
MIT. Bundled third-party components and their license texts are listed in
THIRD-PARTY-NOTICES.txt and shipped in the "licenses" folder.
Full documentation: https://github.com/omarfx83/ps4-profile-studio
