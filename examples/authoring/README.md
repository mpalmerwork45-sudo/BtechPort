# Recorded command authoring examples

`relay-contract.commands.json` creates the separate Relay Contract game from
`../adventure-demo`, using the shared command interface. `units/` contains three
dependency-complete unit bundles exported from the existing BattleTech demo.
Their provenance documents travel with the imports; original game art is
referenced at runtime, not embedded in these unit bundles.

See the [author guide](../../docs/AI_AUTHORING_GUIDE.md) for the creation,
inspection, preview, GUI revision and playtest commands. The accompanying
scenario walks the normal mission route, fights, receives payment, verifies
that it cannot be collected twice, and checks save/reload along the way.

The [expanded scenario suite](scenarios/README.md) records victory seeds,
mid-combat save/reload, decline/cancel, retreat, natural defeat and an explicitly
validated low-funds fixture. It can rerun only selected affected cases.

For the complete discovery/repair workflow, run from the repository root:

```sh
python3 tools/authoring_demo.py --output work/my-authoring-lab
```

It creates a separate playable game under `work/my-authoring-lab/game`, imports
a searched Firefly with dependency/provenance records, creates an owned animated
barrier and exports labelled previews. It then breaks deployment, retains the
failure report, repairs it through commands and reruns the three victory seeds.
Original CHI resources/caches must be prepared; existing projects/libraries are
read-only inputs. Use a new output directory for each demonstration.

The readable recipe source is `tools/make_authoring_recipe.py`. Running it
refreshes these recorded inputs; it does not rewrite a playable project.
`tools/author.py create` builds the actual package from those inputs.
