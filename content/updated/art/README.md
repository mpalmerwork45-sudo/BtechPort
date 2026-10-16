# Starport broker artwork

The Updated broker has a new, static portrait of a slick, slightly sleazy male
salesman, following the owner's Jon Hamm / Don Draper suggestion. It was
generated with **Codex's built-in image generation tool** on 2026-10-16.
The original mechanic and weapons-shop portraits supplied local style
references for the 1980s anime/EGA appearance. Those reference images are not
included in this directory or in Git.

Files:

- [broker-master.png](broker-master.png): selected generated master.
- [broker.png](broker.png): the exact **88×88**, 12-color in-game image.
- [broker.anm](broker.anm): the same image in the game's native ANM format,
  one frame, 3,954 bytes.
- [broker-prompt.md](broker-prompt.md): the final generation prompt and provenance.

The portrait is newly generated expansion artwork, not a recovered CHI asset.
These contributed files use the repository's [GPL-3.0-only license](../../../LICENSE)
to the extent copyright applies. They are separate from the MegaMek-derived
roster data's CC BY-NC-SA license. No rights to the original reference artwork
or BattleTech trademarks are granted.

## Rebuild or replace

Keep an opaque square master. The authoring tool requires Python 3 and Pillow;
the game itself only reads ANM and needs neither Pillow nor a PNG decoder.
From the repository root:

```sh
python3 tools/portrait_convert.py content/updated/art/broker-master.png \
  --output content/updated/art/broker.anm \
  --preview content/updated/art/broker.png
python3 -m unittest discover -s tests -p 'test_portrait.py'
```

The exporter uses nearest-neighbor reduction and maps pixels to the actual
portrait palette without dithering. Stored index 1 is black, 5 is bright blue,
and 9 is dark blue; treating ANM indices as ordinary EGA would change the colors.
`--resample box` is also available for masters that benefit from area averaging.
Non-square or transparent inputs are rejected so cropping/background choices
remain explicit. The PNG preview and ANM encode exactly the same pixels.

Updated loads `art/broker.anm` relative to the selected **roster JSON file**.
Replacing that file changes the broker on the next launch, without rebuilding
C, changing mech definitions, or migrating saves. Missing art falls back to the
original mechanic, allowing older/custom packs to keep working. An existing
but malformed file rejects the edition switch with a diagnostic, preserving
the previously loaded content. Choosing Original clears this optional art.
Original O*.ANM files are never replaced.

The broker displays the last ANM frame as a static portrait. General building
art assignments and animated custom characters remain future authoring work.

## Verification

**VERIFIED:** the independent Python ANM reader reproduces every exported
four-bit pixel, and a headless visit to the actual broker compares its 88×88
screen crop byte-for-byte with `broker.png`, exercising the C decoder and
renderer palette. Content tests cover missing-art fallback, malformed-art
rollback, unchanged roster identity, and switching back to Original.

The menu follows the original building presentation: descriptive prose at
the top, `Will you:` and consecutive eight-pixel Buy/Sell/Leave rows. Stock and
sale lists use the same row spacing. Credits, bay occupancy and model details
occupy the lower left panel. Scrolling, confirmations, purchases, sales and
held saves retain their existing behavior. The portrait and dialogue are
**authored expansion content**, not claims of original-game fidelity.
