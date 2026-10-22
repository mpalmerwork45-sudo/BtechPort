# Independent save compatibility fixtures

`capacity-v49.btp`, `capacity-v50.btp` and `capacity-v51.btp` are actual BTG1
saves produced by the pre-AI7b Linux player built at `5219a1a` on 2026-10-22.
They use the independent Beacon presentation and authored unit definitions;
they contain no original DOS executable or extracted graphics/audio assets.

- v49: unmodified `examples/beacon-demo`, paused on its opening briefing.
- v50: `campaign_capacity.campaign(8, version=2)`, created from that example
  with package ID `capacity-8`, title `Capacity 8`, paused on the first briefing.
- v51: the same eight-contract recipe with package ID `capacity-hooks`, title
  `Capacity hooks`, plus one start hook, ID `capacity:start-hook`, for
  `capacity:c01-patrol-fight`, repeat `once`, event `capacity:end`.

`tests/test_campaign_capacity.py` reconstructs these packages, loads the real
saves, and requires identical bytes on resave. It also checks that a capacity
format upgrade refuses their old fingerprints and that migration declines
cross-format relabelling. Do not regenerate these using the new codec to make
a regression pass; they preserve evidence from the released implementation.
