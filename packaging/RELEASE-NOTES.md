[![Support on Ko-fi](https://img.shields.io/badge/Ko--fi-Support_the_developer-FF5E5B?logo=kofi&logoColor=white)](https://ko-fi.com/omarfx83)

A portable Windows app for PS4 profiles: turn one image into the complete avatar
file set, send it to the console over GoldHEN FTP, and edit a profile's display
name with a picker of 149 PS4 symbols and 371 emoji.

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

## What's new in @VERSION@

@CHANGELOG@

## Notes

- `version.json` on the console is never uploaded or modified.
- Custom profile names only show on **activated** profiles. For offline
  activation use Apollo Save Tool → "Activate Offline Account". Avatar changes
  work on any profile.

## Requirements

- Windows 10 or 11, 64-bit
- A PS4 on the same network running GoldHEN with its FTP server enabled
  (default port 2121). The console must be reachable from the PC.

Full documentation: https://github.com/omarfx83/ps4-profile-studio
Full changelog: https://github.com/omarfx83/ps4-profile-studio/blob/main/CHANGELOG.md
