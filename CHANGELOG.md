# Changelog

All notable changes to PS4 Profile Studio are recorded here.

## [1.0.1] - 2026-11-12

### Added

- **Emoji picker.** The **Symbols…** panel now has two tabs: the PS4 symbols
  and a curated set of **371 emoji** in 8 categories (Smileys & people,
  Animals & nature, Food & drink, Travel & places, Activities, Objects,
  Symbols, Flags), each with an **All** group. Emoji are drawn as live text —
  no bundled artwork — and clicking one inserts a standard Unicode character
  into the name field.
- **Size hints for multi-part emoji.** A small number in the corner of a tile
  shows how many of the 16 name slots that emoji uses: flags and skin tones
  (👍🏽) take 2, joined families (👨‍👩‍👧) take 5. The tooltip spells it out.
- **Skin tone picker.** A row of swatches above the emoji grid applies a tone
  to every emoji that has one, so 👍 can be 👍🏻 👍🏼 👍🏽 👍🏾 or 👍🏿 instead
  of getting whichever tone happened to be in the list.
- **Character counter.** The Profile panel shows how many of the 16 characters
  a name uses, and turns amber when the name is full.
- **Flags are labelled with their country code** (JP, US, GB) in the picker.
  Windows' emoji font has no flag artwork, so this is what Windows draws for a
  flag character anyway; the console shows the real flag.

### Fixed

- **The symbol picker only lists symbols the console can actually draw.**
  Every character in the set was checked on a real PS4: **149 render** as
  icons and **126** (all in the `EFxx` private-use range) appear as a `?` box.
  The dead entries are no longer offered, so picking a symbol can no longer
  produce a broken name.
- **The name field stopped at 8 emoji instead of 16.** The text box counted
  UTF-16 code units while the console counts characters, so emoji were counted
  twice. The field now accepts a full 16-character name, emoji included.
- **Clicks in the picker looked dead when the name was full.** They were being
  rejected by the 16-character limit, with only a line of small text at the
  bottom of the Profile panel to say so. The picker now shows a message where
  you are looking, and the new counter shows the limit before you hit it.
- **Backspace deleted half an emoji.** A toned emoji (👋🏽) is several
  characters, so deleting walked through the tone first and left a plain hand
  behind. Backspace and Delete now remove a whole emoji — flag, tone or joined
  family — in one press.
- **Emoji the system font cannot draw are no longer listed.** The picker only
  offers characters your Windows emoji font really renders, so no tile (and no
  inserted name) shows a `?` box.
- **SHARE and OPTIONS icons** now show the words the console really draws
  instead of a volume and a list icon.

### Changed

- Symbol counts in the app description and documentation: 275 → 149.
- Picker tiles are drawn as rounded cards, with the category switch above the
  category list.

## [1.0.0] - 2026-11-10

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
  with a symbol picker of **275 symbols** across 7 categories, inserting the
  character straight into the name field.
- **Portable Windows build** — extract the ZIP and run
  `PS4 Profile Studio.exe`; no Python and no installation required.
- **`build.ps1`** — produces
  `release\PS4-Profile-Studio-<version>-win64.zip`, its SHA-256 checksum and
  the release notes.

### Changed

- The top bar holds the **Device** list of saved consoles plus the live
  connection state.
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
