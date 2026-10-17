# Last Beacon

For the BattleTech setting, established 'Mechs and original-game presentation,
play **[BattleTech: Last Beacon](../battletech-demo/README.md)**. This version is
retained as the asset-free engine/editor template.

A small, independently authored demonstration game for BtechPort. All text,
pixels, font, tones and unit definitions are supplied in this directory.
No original game, extracted cache or external asset pack is required.

From the repository root after building:

```sh
./build/btp-project validate examples/beacon-demo
./build/btech-port --project examples/beacon-demo --save-file work/beacon-game.btp
```

Or copy this entire directory alongside the player and use its new location
with `--project`. A Windows player also needs its matching SDL2/runtime DLLs.
Use a writable `--save-file` path when running from a read-only installation.

You are Rowan, a walker pilot in Grayhaven. Talk to Mira outside the Relay
Office or enter the office and recruit her. The Walker Exchange sells another
walker, but a purchase is optional. Travel east to the silent relay, approach
the mast, defeat its malfunctioning guardian, and return to the Relay Office
for payment and the ending. Computer combat is available; choose Yes at the
first battle prompt, then accept the message and graphics settings.

Arrows/numpad travel and choose; Enter/Space selects; Escape cancels. Space on
the map opens settings, allocation, inspection, six save slots and the overhead
map. F4 shows the map, F5/F9 save/restore, Ctrl+Shift+Escape exits.

Edit through the shared desktop tool:

```sh
python3 tools/game_editor.py examples/beacon-demo
```

Use New project to create your own copy before making changes. Maps / events
opens the painting, placement and event forms. The full workflow, build without
original files, Lua API, bounds and verification are in
[the implementation guide](../../docs/M5_INDEPENDENT_GAME_EDITOR.md).

The game and its assets are GPL-3.0-only; see [LICENSE.md](LICENSE.md) and
[CREDITS.md](CREDITS.md). `tools/make_beacon_demo.py` reproduces the shipped
demonstration files; running it overwrites this example, so retain your own
projects elsewhere. No demonstration asset is extracted from the DOS game.
