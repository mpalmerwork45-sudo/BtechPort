# Updated building artwork

The Updated broker has a new, static portrait of a slick, slightly sleazy male
salesman, following the owner's Jon Hamm / Don Draper suggestion. It was
generated with **Codex's built-in image generation tool** on 2026-10-16.
The original mechanic and weapons-shop portraits supplied local style
references for the 1980s anime/EGA appearance. Those reference images are not
included in this directory or in Git. Seven additional portraits follow the
same style: a veteran instructor, lounge bartender, jailkeeper, inventor,
cinema attendant, clinician and ComStar Adept. These also use the built-in
image generation tool; their exact prompts are in
[building-prompts.json](building-prompts.json).

Every portrait has a selected `<name>-master.png`, an exact **88×88** indexed
`<name>.png` preview, and a single-frame `<name>.anm` (**3,954 bytes**). The
portraits use 12–14 colors from the game's display palette.

| Building | File stem | Original building ID |
|---|---|---|
| Starport 'Mech Broker | `broker` | 26 (added) |
| Training Center | `training` | 0 |
| Lounge | `lounge` | 7 |
| Prison | `prison` | 13 |
| Inventor's hut | `inventor` | 21 |
| Cinema | `cinema` | 16 |
| Hospital | `hospital` | 9 |
| ComStar | `comstar` | 2 |

Broker files and its original prompt:

- [broker-master.png](broker-master.png): selected generated master.
- [broker.png](broker.png): the exact **88×88**, 12-color in-game image.
- [broker.anm](broker.anm): the same image in the game's native ANM format,
  one frame, 3,954 bytes.
- [broker-prompt.md](broker-prompt.md): the final generation prompt and provenance.

The portraits are newly generated expansion artwork, not recovered CHI assets.
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

Substitute any file stem from the table to rebuild or replace that portrait.

The exporter uses nearest-neighbor reduction and maps pixels to the actual
portrait palette without dithering. Stored index 1 is black, 5 is bright blue,
and 9 is dark blue; treating ANM indices as ordinary EGA would change the colors.
`--resample box` is also available for masters that benefit from area averaging.
Non-square or transparent inputs are rejected so cropping/background choices
remain explicit. The PNG preview and ANM encode exactly the same pixels.

Updated loads these eight optional `art/<name>.anm` files relative to the
selected **roster JSON file**. Replacing one changes the corresponding building
on the next launch, without rebuilding C, changing mech definitions, or
migrating saves. Each missing file falls back independently to the original
presentation (the mechanic for the broker). An existing but malformed file
rejects the entire edition switch with a named diagnostic, preserving the
previously loaded content. Choosing Original clears all optional portraits.
The 0.2.0 roster fingerprint remains **751321522**, Updated saves remain v43,
and Original saves remain v40. Original O*.ANM files are never replaced.

The renderer displays the last ANM frame as a **static** portrait in the
88×88 building panel. Explicit original BLD animations and their held frames
take priority, preserving the cinema films and other story scenes. Training
quizzes and Katrina's Citadel portrait retain their original presentation.
The eight assignments above are a bounded filename convention; a general
building manifest/editor and animated custom characters remain future work.

## Verification

**VERIFIED:** the independent Python ANM reader reproduces every exported
four-bit pixel. Actual building visits compare every portrait crop byte-for-byte
with its PNG, exercising the C decoder and renderer palette. The new seven
buildings also compare every pixel outside the portrait with Original, round-trip
held saves, and continue their real BLD scripts with identical state changes.
All ten cinema animation IDs and the training quiz retain Original rendering.
Content tests cover each missing-art fallback, malformed-art rollback, unchanged
roster identity, and switching back to Original.

The bounded window check visits all seven buildings and verifies their exact
portraits, F5/F9 and the restored full frame on a private display:

```sh
python3 tools/native_smoke.py --building-art-only
python3 tools/native_smoke.py --windows --building-art-only
```

See [the milestone verification](../../../docs/M5A_ROSTER_SLICE.md) for recorded
results. These checks establish the integration; the portraits are authored
interpretations of the buildings, not original-game fidelity claims.

The menu follows the original building presentation: descriptive prose at
the top, `Will you:` and consecutive eight-pixel Buy/Sell/Leave rows. Stock and
sale lists use the same row spacing. Credits, bay occupancy and model details
occupy the lower left panel. Scrolling, confirmations, purchases, sales and
held saves retain their existing behavior. The portrait and dialogue are
**authored expansion content**, not claims of original-game fidelity.
