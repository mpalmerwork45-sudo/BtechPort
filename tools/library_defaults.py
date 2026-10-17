"""One-time sprite defaults for shipped library blueprints, never game saves."""
import copy

# Temporary silhouettes requested by the author. These describe leg geometry,
# not tonnage, weapon type, faction or which sprite a cached CHI record used.
REVERSE_JOINTED = {'locust', 'jenner', 'cicada', 'catapult', 'marauder',
                  'stalker', 'flea', 'firefly', 'cataphract', 'thug', 'king crab'}
DEFAULTS_VERSION = 1


def apply_sprite_defaults(bundle):
    value = copy.deepcopy(bundle)
    if value['kind'] == 'Vehicles':
        return value
    if value['provenance'].get('sprite_defaults', 0) >= DEFAULTS_VERSION:
        return value
    if value['kind'] == 'Mechs':
        unit = value['content']['mechs'][0]
        current = next(p for p in value['content']['presentations'] if p['id'] == unit['presentation'])
        # An author's painted/chosen owned sprite takes precedence. Existing
        # stats, loadouts, prices and IDs are retained during this migration.
        if current['source'] != 'package:art':
            name = unit['name'].casefold()
            reverse = any(name == n or name.startswith(n + ' ') for n in REVERSE_JOINTED)
            source = 'chi:locust' if reverse else 'chi:red-stinger'
            value['content']['presentations'] = [dict(id=source, source=source)]
            unit['presentation'] = source
    elif value['kind'] == 'Infantry':
        if not any(b['slot'] == 'npc' for b in value['graphics']['bindings']):
            value['infantry_source'] = 'chi:infantry'
    value['provenance']['sprite_defaults'] = DEFAULTS_VERSION
    return value
