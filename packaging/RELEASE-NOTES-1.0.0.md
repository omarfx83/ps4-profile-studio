[![Support on Ko-fi](https://img.shields.io/badge/Ko--fi-Support_the_developer-FF5E5B?logo=kofi&logoColor=white)](https://ko-fi.com/omarfx83)

A portable Windows app for PS4 profiles: turn one image into the complete avatar
file set, send it to the console over GoldHEN FTP, and edit a profile's display
name with a built-in picker of PS4 symbols.

## Download

| File | Size |
|---|---|
| `PS4-Profile-Studio-1.0.0-win64.zip` | 47.9 MB |
| `PS4-Profile-Studio-1.0.0-win64.zip.sha256` | 102 bytes |

SHA-256 of the ZIP:

```
d5198fcc7790114f8647204635994635aa0bff7c6344652b60c9263d1cbb00ee
```

**No Python, no installation.** Extract the ZIP, open the `PS4 Profile Studio`
folder and run `PS4 Profile Studio.exe`. Windows may show "Windows protected
your PC" because the build is not code-signed — click **More info → Run anyway**.

## What's new in 1.0.0

First public release.

### Added

- **Avatar editor** — open a PNG/JPG (or drag & drop one), crop it with a
  movable/resizable square selection, and preview the result at 440 / 260 / 128
  / 64 px. Every preview is encoded to DXT5 and decoded back, so it shows the
  real compression result.
- **Nine alpha masks** — Square, Circle, Rounded, Squircle, Hexagon, Octagon,
  Star, Diamond and Heart, with the mask outline drawn over the crop square and
  a percentage-based padding control.
- **PS4 blue preview** — shows the avatar on a PS4-home-screen-style gradient,
  with a checkerboard alternative for checking transparency.
- **Export options** — optional `avatar.png`, optional `picture*.dds` /
  `picture.png` duplicates for offline-activated accounts, and copying
  `online.json` + `version.json` unchanged from a profile folder.
- **Direct upload to the console** — connects to GoldHEN's FTP server, lists
  every `0x…` profile folder with its thumbnail and name, and sends the avatar
  set to one user or to all of them.
- **Backup before overwrite** (on by default) — copies the existing avatar
  files plus `online.json` and `version.json` to `backups/<timestamp>/<0x…>/`
  first. If the backup fails, that user is skipped instead of overwritten.
- **Refresh console after send** — re-writes the user's existing `online.json`
  unchanged (or creates a minimal one) so the console re-reads the profile and
  the new avatar appears without signing out.
- **Saved consoles** — remembers up to 10 recently connected consoles, most
  recent first, each with an optional friendly name you can rename or forget
  from the top bar. Nothing is prefilled on a fresh install.
- **Profile tab** — edits a user's display name (`online.json` → `firstName`)
  with a symbol picker across 7 categories, inserting the character straight
  into the name field.
- **Portable Windows build** — extract the ZIP and run
  `PS4 Profile Studio.exe`; no Python and no installation required.

### Fixed

- Bundled fonts and symbol icons now resolve correctly in a packaged
  (PyInstaller) build.

## Notes

> **Using the symbol picker? Update to 1.0.1.** Version 1.0.0 lists 275 symbols,
> but the console only draws 149 of them — the other 126 appear as a `?` box.
> The picker was corrected in **1.0.1**, which also adds the emoji picker.

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
