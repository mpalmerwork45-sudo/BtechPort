#ifndef BTP_UNIT_DATA_H
#define BTP_UNIT_DATA_H
#include "core/combat_rules.h"

/* These identities select original templates, not party slots or display-name
   initials. Custom definition IDs can later map to the same lookup boundary. */
typedef enum {
    BTP_MECH_LOAN, BTP_MECH_JENNER, BTP_MECH_COMMANDO, BTP_MECH_ENCOUNTER,
    BTP_MECH_ARENA, BTP_MECH_SPECTATOR, BTP_MECH_URBANMECH
} BtpMechTemplate;
const uint8_t *btp_mech_template(const BtpCombatData *data, BtpMechTemplate kind, unsigned index);

/* An immutable view of the original weapon definition. Damage/projectiles
   retain their original personal-weapon flag encoding; combat owns the dice
   and scaling rules. The eleven-byte name is not necessarily terminated. */
typedef struct {
    const uint8_t *name;
    unsigned damage, projectiles, heat, near_range, medium_range, far_range, skill;
} BtpWeaponDefinition;
BtpWeaponDefinition btp_weapon_definition(const BtpCombatData *data, unsigned index);
BtpWeaponDefinition btp_unit_weapon_definition(const BtpCombatData *data,const BtpCombatUnit *unit,unsigned mount);
unsigned btp_combat_mount_range(const BtpCombatData *data,const BtpCombatProfile *profile,
    const BtpCombatUnit *actor,const BtpCombatUnit *target,unsigned mount,unsigned *minimum);

unsigned btp_mech_walk_points(const uint8_t record[125]);
unsigned btp_mech_jump_points(const uint8_t record[125]);
unsigned btp_vehicle_kind(const uint8_t record[125]); /* 0 mech, 1 tracks, 2 wheels, 3 hover */
int btp_vehicle_terrain(unsigned kind,unsigned terrain);
const char *btp_vehicle_location(unsigned record_location);
unsigned btp_mech_sprite_base(unsigned tag, int enemy);
unsigned btp_mech_record_sprite(const uint8_t record[125],int enemy);
unsigned btp_mech_refit_index(const uint8_t record[125]); /* 8 means no model recipe. */
unsigned btp_mech_refit_price(const BtpCombatData *data, unsigned recipe);
int btp_mech_apply_refit(const BtpCombatData *data, uint8_t record[125], unsigned recipe);
#endif
