#ifndef BTP_COMBAT_H
#define BTP_COMBAT_H
#include "core/game.h"

int btp_combat_los(const BtpMap *map, unsigned gate, int x, int y, int tx, int ty);
void btp_combat_plan(const BtpMap *map, unsigned gate, const BtpCombatUnit *unit,
    const BtpCombatUnit *other, int tx, int ty, unsigned movement, int computer,
    int8_t steps[12][2]);
unsigned btp_combat_cover(const BtpMap *map, const BtpCombatUnit *unit, unsigned *terrain);
unsigned btp_combat_id(const BtpCombatState *combat, unsigned unit);
unsigned btp_combat_target(const BtpCombatState *combat, unsigned id);
void btp_combat_ignite(BtpState *state, const BtpCombatUnit *target);
int btp_combat_waypoint(BtpCombatState *combat, unsigned x, unsigned y, unsigned movement);
void btp_combat_route(const BtpMap *map, unsigned gate, const BtpCombatState *combat, int8_t steps[12][2]);
void btp_combat_begin(BtpState *state, const BtpResources *resources);
void btp_combat_tick(BtpState *state, const BtpResources *resources, BtpAction action);
/* Controlled original-turn comparisons retain the original moving target.
   Ordinary training uses the stationary shell requested by the user. */
void btp_combat_tick_reference(BtpState *state, const BtpResources *resources, BtpAction action);
int btp_combat_valid(const BtpState *state);
void btp_combat_encode(const BtpCombatState *combat, uint8_t bytes[BTP_COMBAT_SAVE_BYTES]);
int btp_combat_decode(const uint8_t bytes[BTP_COMBAT_SAVE_BYTES], BtpCombatState *combat);
#endif
