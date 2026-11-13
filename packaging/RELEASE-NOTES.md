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

## What's new in 1.0.1

### Added

- **Emoji picker.** The **Symbols…** panel now has two tabs: the PS4 symbols and
  a curated set of **371 emoji** in 8 categories (Smileys & people, Animals &
  nature, Food & drink, Travel & places, Activities, Objects, Symbols, Flags),
  each with an **All** group. Emoji are drawn as live text — no bundled artwork
  — and clicking one inserts a standard Unicode character into the name field.
- **Skin tone picker.** A row of swatches above the emoji grid applies a tone to
  every emoji that has one, so 👍 can be 👍🏻 👍🏼 👍🏽 👍🏾 or 👍🏿.
- **Size hints for multi-part emoji.** A small number in the corner of a tile
  shows how many of the 16 name slots that emoji uses: flags and skin tones
  (👍🏽) take 2, joined families (👨‍👩‍👧) take 5.
- **Character counter** beside the name, turning amber when the 16-character
  limit is reached.

### Fixed

- **The symbol picker only lists symbols the console can actually draw.** Every
  character in the set was checked on a real PS4: **149 render** as icons and
  **126** (all in the `EFxx` private-use range) appeared as a `?` box. The dead
  entries are no longer offered.
- **The name field stopped at 8 emoji instead of 16.** The text box counted
  UTF-16 code units while the console counts characters, so emoji were counted
  twice.
- **Clicks in the picker looked dead when the name was full.** They were being
  rejected by the 16-character limit with no visible feedback; the picker now
  says so, and the counter shows the limit before you reach it.
- **Backspace deleted half an emoji.** A toned emoji (👋🏽) is several
  characters, so deleting peeled the tone off and left a plain hand behind.
  Backspace and Delete now remove a whole emoji in one press.
- **The picker kept stealing the keyboard.** The caret now stays in the name
  field, so you can keep typing, deleting and clicking emoji without closing it.
  **Escape** closes the picker.
- **"Apply name" failed when the console dropped the FTP session.** It reported
  a failure until you pressed Refresh; the app now reconnects and retries by
  itself, and a dropped connection can no longer be mistaken for a profile
  without `online.json`.
- **SHARE and OPTIONS icons** now show the words the console really draws.
- **Flags are labelled with their country code** (JP, US, GB) in the picker.
  Windows has no flag artwork in any of its fonts, so a flag prints as those
  letters on the PC; the console draws the real flag.

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
- **Profile names** — edit the display name with a picker of 149 symbols and 371
  emoji, all verified to render on the console.
- **Portable** — settings and backups live next to the executable, with an
  `%APPDATA%\PS4ProfileStudio` fallback for read-only folders. Delete the folder
  to uninstall.

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
