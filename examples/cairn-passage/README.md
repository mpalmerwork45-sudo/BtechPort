# BattleTech - Cairn Passage

A small authored defence-and-escort demonstration for AI6b/AI6c. Uses the
original CHI runtime art supplied separately by the player, CHI-adapted unit
definitions, and original editable construction/vehicle artwork.

From the repository root:

```sh
./build/btech-port --project examples/cairn-passage --data "Original DOS"
./BtechPort
```

In the launcher, select Cairn Passage, then Open editor to edit the mission.
Choose defence or escort at the briefing. Defence holds the relay vehicle for
five rounds against two raider waves, with an allied Galleon guard. Success
offers the escort immediately. Escort protects an engine-controlled Skulker
along the road to the northeast landing pad; a reserve ambush enters on round
three. Loss of the protected carrier or retreat fails the current contract.
The Phoenix Hawk and Trebuchet remain player controlled or use normal computer
combat. Both contracts together pay 7,000 C-bills.

Mission state in the editor exposes groups, actor waypoints, timers and hooks.
Construction styles include all roof/face parts, all sixteen road connections,
and zero-story walls. Their compiled tiles work in the ordinary player.

Regenerate into a new directory with:

```sh
python3 tools/combat_mission_demo.py --output work/cairn-copy
python3 tools/author.py suite examples/cairn-passage --file examples/authoring/cairn/suite.json --output work/cairn-check
```

The suite covers bounded seeds, success, retreat, transport loss, the combined
contract and save/reload checkpoints. It does not establish general AI balance
or guarantee that arbitrary waypoint layouts are reachable. See
[combat mission semantics](../../docs/COMBAT_MISSIONS.md) and the accompanying
source/credit documents for unit attribution. `creation.commands.json` records
the authoring batch against the generator's initialized template revision.
