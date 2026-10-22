# Larger authored campaigns — AI7b

**Delivered 2026-10-22, runtime 0.2.0.** Adventure v3 deliberately opts into
larger campaign budgets. Original CHI and adventure v1/v2 keep their existing
rules, limits and save layouts. Source projects and ordinary package directories
can both use v3.

| Collection | Adventure v1/v2 | Adventure v3 |
| --- | ---: | ---: |
| Local maps | 16 | 64 |
| Encounters | 16 | 64 |
| Event nodes | 256 | 1,024 |
| Objectives | 32 | 128 |
| Persistent variables | 32 | 128 |

## Using the larger limits

In the Construction Kit, open **Project → Campaign sources and build**, then
**Upgrade campaign limits**. This is an ordinary undoable draft edit; Save,
Build and Play use the same native validator. Keep a separate copy of the old
package if you want to continue its existing saves. The upgrade does not move,
overwrite or convert save files. Existing projects are never upgraded on open.

Automated authors use `{"op":"campaign.upgrade"}` in a normal revision-bound
command batch with `adventure` write scope. It changes the adventure header to
`btp-adventure-v3`, `schema_version: 3`, converting v1 character rows to stable
tile IDs first. It does not require a `SOURCE.json` conversion.

`python3 tools/author.py capabilities` reports the installed global maxima,
`runtime.format_limits` overrides for older formats, minimum runtime version,
save version and native structure sizes. `inspect PROJECT` reports the actual
limits for that project's format. An old validator refuses the upgrade; an old
player refuses a v3 package instead of truncating its definitions.

## Reproducible capacity campaign

```sh
python3 tools/campaign_capacity.py --output work/my-frontier-circuit --verify
python3 tools/game_editor.py work/my-frontier-circuit/source
./build/btech-port --project work/my-frontier-circuit/game
```

Choose a new output directory. The generator creates **20 contracts, 40 local
maps, two 512 × 512 tile jigsaw planets, 20 encounters, 403 events, 40 objectives
and 40 variables**. Each outpost has a survey/branch, ordinary combat,
once-only payment, repair/rearm/healing and onward travel. Retreat returns to
the outpost. It uses the independent example's owned presentation and units;
no original DOS assets are needed. `--contracts` accepts 1..32.

This is a capacity fixture with repeated contract structure and a weak guardian,
not a new balanced narrative campaign. `--verify` runs the actual player with
normal choice/computer-combat inputs and a save/reload checkpoint after every
battle. It never awards victories by editing game state. The source project is
built twice and its runtime bytes/digest must match. Artifacts, scenario and
reports are retained beside the packages. The user's Last Beacon is untouched.

The default run passes 142 scenario steps / 1,326 ticks, completes all 40
objectives, sets all 40 counters to one and finishes with 4,000 credits. Linux
and Windows under Wine produce identical final save bytes. See the dated
[verification record](TESTING.md#ai7b-measured-campaign-capacity--2026-10-22).

## What was audited

**VERIFIED in the declared fixtures:**

- The pre-change runtime accepts the eight-contract fixture (16 maps, 163
  events) and rejects the 20-contract fixture at map 17. Each expanded
  collection also has an independent old-format refusal test, a maximum test
  and a one-over-maximum refusal test.
- Map/event continuations and entrance targets already use 16-bit handles.
  The legacy map byte remains an adapter: authored maps 239+ use byte 255 and
  their independent scene handle. The maximum fixture exercises scene **319**
  (64 locals + 256 sectors), event **1023**, variable/objective **127**, journal
  page **128**, and encounter **63**. Two journal guards retaining the old
  32-page limit were found and corrected.
- Event once-only state grows from 256 to 1,024 bits. Saved counters/objectives
  grow from 32 to 128 entries. Region membership, combat groups and hooks keep
  their existing bit widths and budgets. No tactical unit/weapon handle widens.
- Large loader scratch arrays follow their declared bounds. Adventure/project
  data remain heap allocated. The live state gains only 580 bytes; there is no
  new multi-megabyte stack allocation.
- The world sector budget stays independent of local-map capacity. Discovery
  stays at 16,384 cells across worlds and separate interiors. V3 also allocates
  distinct discovery regions to local maps without planets, including maps at
  identical coordinates. Legacy discovery behavior is retained.
- Editor controls open, paint and save map 40; edit a late event; show the
  second planet; navigate a deliberate source error; repair, export/reopen and
  launch the edited source project. Native schema, GUI commands and AI capacity
  inspection agree on the format's limits.

## Save compatibility

Adventure v3 uses optional state **v52 (`BTPq`)** inside the existing strict
`BTG1` project envelope. The payload remains **20,480 bytes**, the project save
**20,640 bytes**. Its authored extension occupies reserved payload bytes
512..1535; earlier v18+ layouts require that area to be zero. The block has its
own version and optional combat-state flag, upper event bits, upper counters
and objectives. The released lower fields retain their exact offsets. Reserved
bytes, invalid states/counters and false downgrades are rejected.

Real pre-change v49/v50/v51 independent saves are committed under
`tests/fixtures/capacity-v*.btp`; tests reconstruct their exact packages, load
them and resave identical bytes. Locally preserved Original and Updated saves
also reload/resave identically. An old executable rejects a v52 payload, and
the current player refuses a save whose project digest belongs to another
format/content revision.

**V1/v2 → v3 save migration is deliberately refused.** The existing compatible
revision migration tool cannot safely reassign discovery or initialize added
mission state by changing only the fingerprint. Keep the old package for those
saves; start a new campaign in the upgraded copy. Ordinary compatible edits
within the same format retain the existing migration policy. Source formatting,
notes and module organization continue to preserve an unchanged compiled
package's save identity.

## Measurements and remaining bounds

Linux x86-64 measurements, release build, warm local filesystem; these are
observations on this host, not timing guarantees:

| Native allocation | Before | After |
| --- | ---: | ---: |
| `BtpAdventure` | 15,510,048 bytes | 19,221,792 bytes |
| `BtpProject` (includes adventure) | 25,501,880 bytes | 29,213,624 bytes |
| `BtpState` | 16,268 bytes | 16,848 bytes |
| `BtpResources` | 3,219,408 bytes | 3,219,408 bytes |

The added fixed campaign allocation is **3,711,744 bytes (3.54 MiB)**. All
loaded authored packages pay that bounded allocation, including v1/v2. Five
new-runtime validations of the eight-contract package took 14.2–14.6 ms with
26.3–26.8 MiB peak RSS; its pre-change validation took 13.7 ms / 22.9 MiB. The
20-contract package took 19.9–20.7 ms / 28.7–28.8 MiB. Loading, checkpointing and
rendering the simultaneous maximum fixture peaked at 49.7 MiB / 95 ms.

The GUI journey opened the 573-file source project and map view in 55 ms;
process peak RSS was 136.2 MiB. Its largest GUI heartbeat gap across edits,
source conversion/diagnostics/build preparation was 594 ms. Those occasional
synchronous document/view operations remain a performance follow-up; this
measurement does not promise frame-perfect interaction at every maximum.

Unchanged bounds include 64×64 tiles per local map, 16 entrances per map,
64 flags, 32 regions, 16 people, 16 shops, 16 combat groups, 32 combat hooks,
16 waypoints per actor and 12 nonparty units per encounter. Planets share
256 sectors / 1,048,576 tiles and the discovery budget; source modules share
4,096 files / 128 MiB. Adventure JSON still has its 16 MiB / 300,000-node
parser budget. The maximum fixture fits those aggregate budgets; arbitrary
additional overlays/patches must still fit them. Inspect capacity and validate
before growing content.

Native Windows Tk, arbitrary world-spanning route verification, general combat
balance and unlimited campaign generation remain **UNKNOWN**. The next milestone
is **AI8: a curated campaign demonstration, author recipes and packaged delivery**.
