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

The readable recipe source is `tools/make_authoring_recipe.py`. Running it
refreshes these recorded inputs; it does not rewrite a playable project.
`tools/author.py create` builds the actual package from those inputs.
