# Overlay fonts

Font binaries are not versioned. Several faces in the library are commercially
licensed and may not be redistributed, and the Iosevka Nerd Font set alone is
about 65 MB. Install the files locally into this directory.

`fonts.js` declares the library; every entry's `file` value must resolve here or
the face falls back to the `Consolas, monospace` stack declared in `overlay.js`.

## Expected filenames

| Label | File | Source |
| --- | --- | --- |
| Isonorm Monospaced | `Isonorm Monospaced Regular.otf` | commercial |
| Isonorm | `Isonorm Regular.otf` | commercial |
| Isonorm MN | `Isonorm MN Regular.ttf` | commercial |
| Iosevka Mono Thin | `IosevkaTermNerdFontMono-Thin.ttf` | Nerd Fonts release, SIL OFL |
| Iosevka Mono ExtraLight | `IosevkaTermNerdFontMono-ExtraLight.ttf` | Nerd Fonts release, SIL OFL |
| Iosevka Mono Light | `IosevkaTermNerdFontMono-Light.ttf` | Nerd Fonts release, SIL OFL |
| Iosevka Mono Medium | `IosevkaTermNerdFontMono-Medium.ttf` | Nerd Fonts release, SIL OFL |
| Iosevka Light | `IosevkaTermNerdFont-Light.ttf` | Nerd Fonts release, SIL OFL |
| Blender Pro Book | `BlenderPro-Book.ttf` | commercial |
| Blender Pro Medium | `BlenderPro-Medium.otf` | commercial |
| Blender Pro Bold | `BlenderPro-Bold.ttf` | commercial |
| Helvetica Neue Md | `HelveticaNeueLTCom-Md.ttf` | commercial |
| Helvetica Neue Hv | `HelveticaNeueLTCom-Hv.ttf` | commercial |
| DIN Alternate Bold | `DIN Alternate Bold.ttf` | commercial |
| Arame Thin | `Arame Thin.ttf` | commercial |
| APK Systema | `APKSystema_Regular.otf` | commercial |
| kroeger 07_56 (pixel) | `kroe0756.ttf` | freeware |
| schoenecker 10_56 (pixel) | `SCHO1056.TTF` | freeware |
| 2DADEC A | `2DADEC_0_0.ttf` | webfont kit |
| 2DADEC B | `2DADEC_1_0.ttf` | webfont kit |
| Dosis | `Dosis-VariableFont_wght.ttf` | SIL OFL |

The default type stack uses Isonorm Monospaced for numerals and Iosevka Mono
Light for mini and micro text. Without those two the overlay still renders, but
metrics and tracking will not match reference captures.
