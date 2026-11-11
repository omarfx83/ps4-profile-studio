A portable Windows app for PS4 profile avatars: turn one image into the complete
avatar file set, send it to the console over GoldHEN FTP, and edit a profile's
display name with a symbol picker.

## Download

| File | Size |
|---|---|
| `PS4-Profile-Studio-@VERSION@-win64.zip` | @SIZE@ MB |
| `PS4-Profile-Studio-@VERSION@-win64.zip.sha256` | @SHA_SIZE@ bytes |

SHA-256 of the ZIP:

```
@SHA256@
```

**No Python, no installation.** Extract the ZIP, open the `PS4 Profile Studio`
folder and run `PS4 Profile Studio.exe`. Windows may show "Windows protected
your PC" because the build is not code-signed — click **More info → Run anyway**.

## Highlights

- **Avatar editor** — crop with a square selection, preview at 440/260/128/64 px
  (every tile is decoded from the real DXT5 output), nine alpha masks, padding
  control, and a PS4-blue preview.
- **One-click upload** — connects to GoldHEN's FTP server, lists every profile
  on the console with its thumbnail and name, and sends the avatar set to one
  user or to all of them.
- **Backup before overwrite** — the existing profile files are copied to
  `backups/<timestamp>/<0x…>/` first; if the backup fails, that user is skipped.
- **Saved consoles** — remembers up to 10 consoles with friendly names you can
  rename, most recent first.
- **Profile names** — edit the display name with a picker of 275 symbols.
- **Portable** — settings and backups live next to the executable, with an
  `%APPDATA%\PS4ProfileStudio` fallback for read-only folders.

## Notes

- `version.json` on the console is never uploaded or modified.
- Custom profile names only show on **activated** profiles. For offline
  activation use Apollo Save Tool → "Activate Offline Account". Avatar changes
  work on any profile.

## Requirements

- Windows 10 or 11, 64-bit
- A PS4 on the same network running GoldHEN with its FTP server enabled
  (default port 2121)

Full documentation: https://github.com/omarfx83/ps4-profile-studio
