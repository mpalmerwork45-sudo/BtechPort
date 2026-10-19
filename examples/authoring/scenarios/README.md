# Relay Contract gameplay scenarios

These recorded routes use ordinary game input. The computer fights the real
combat simulation; `hold` ends turns without attacking until natural defeat,
and `retreat` selects the normal combat menu command.

From the repository root, with original resources/caches prepared:

```sh
python3 tools/author.py suite examples/relay-contract --file examples/authoring/scenarios/relay.suite.json --output work/relay-suite-01 --data 'Original DOS' --dialogue-data work/talk-data.bin --combat-data work/combat-data.bin --world-data work/world-data.bin
```

Use a new output directory each time. The suite runs eight cases / ten new games:

| Case | What is exercised |
| --- | --- |
| victory | Three seeds; computer combat; save/reload during battle; payment once across repeat visits; ending |
| decline | Decline the contract; objective remains inactive |
| cancel | Cancel the contract choice |
| door-cancel | Save at the building-entry question, decline entry, save again |
| encounter-decline | Decline combat, return to town without completing the objective |
| retreat | Real Flee command; contract remains open; return route and save/reload |
| defeat | Natural combat loss under hold orders; failure text, return to town and save/reload |
| unaffordable | **Controlled fixture:** same game with starting credits set to zero by a validated command batch; win normally, decline unaffordable repairs, then receive the contract reward |

The low-funds case is a private validated copy. Reports identify it as
`validated_fixture` with its source revision and command-file hash. All other
cases start ordinary new games. No scenario command changes flags, teleports
the party or awards a battle outcome.

To rerun just affected cases:

```sh
python3 tools/author.py suite examples/relay-contract --file examples/authoring/scenarios/relay.suite.json --case retreat --case defeat --output work/relay-failure-routes-01 --data 'Original DOS' --dialogue-data work/talk-data.bin --combat-data work/combat-data.bin --world-data work/world-data.bin
```

The report retains exact staged content, input replay, named states, observed
events/branches, screenshots, save files and per-battle summaries. Seeded
reproduction uses the recorded `scenario.json`; the input list alone does not
configure the initial seed. Seeds encode the three RNG bytes in little-endian
order; `11223583` preserves the ordinary initial bytes `31,66,171`.

Combat figures describe only these cases/seeds/policies. Armour, structure and
ammunition reductions include destruction. Owned mech counts include occupied
inventory bays; a parked/destroyed record can be unavailable for deployment.

Regenerate these JSON inputs with `python3 tools/make_authoring_scenarios.py`.
