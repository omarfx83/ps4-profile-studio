# Changelog

All notable changes to PS4 Profile Studio are recorded here.

## [1.0.0] - 2026-11-10

First public release.

### Added

- **Avatar editor** — open a PNG/JPG (or drag & drop one), crop it with a
  movable/resizable square selection, and preview the result at 440 / 260 / 128
  / 64 px. The 440 preview is encoded to DXT5 and decoded back, so it shows the
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
  with a symbol picker of **275 symbols** across 7 categories, inserting the
  character straight into the name field.
- **Portable Windows build** — extract the ZIP and run
  `PS4 Profile Studio.exe`; no Python and no installation required.
- **`build.ps1`** — produces
  `release\PS4-Profile-Studio-<version>-win64.zip`, its SHA-256 checksum and
  the release notes.

### Changed

- The top bar replaces the IP field with a **Device** list of saved consoles;
  the live connection state is shown next to it.
- Settings and backups are stored next to the executable (portable), with a
  `%APPDATA%\PS4ProfileStudio` fallback when that folder is read-only.

### Fixed

- Bundled fonts and symbol icons now resolve correctly in a packaged
  (PyInstaller) build.

### Notes

- `version.json` on the console is **never** uploaded or modified.
- Custom profile names only appear on **activated** profiles. For offline
  activation use Apollo Save Tool → "Activate Offline Account". Avatar changes
  work on any profile.
