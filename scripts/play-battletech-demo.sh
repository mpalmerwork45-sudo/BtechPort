#!/bin/sh
# Use explicit dependency paths and a separate save namespace for this scenario.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
mkdir -p "$root/work"
exec "$root/build/btech-port" --project "$root/examples/battletech-demo" \
  --data "$root/Original DOS" --dialogue-data "$root/work/talk-data.bin" \
  --combat-data "$root/work/combat-data.bin" --world-data "$root/work/world-data.bin" \
  --save-file "$root/work/battletech-demo.btp" "$@"
