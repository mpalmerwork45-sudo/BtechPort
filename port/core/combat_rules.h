#ifndef BTP_COMBAT_RULES_H
#define BTP_COMBAT_RULES_H
#include <stdint.h>
#include <stddef.h>

typedef struct {
    uint8_t loans[3][125], weapons[33][17], arcs[15], locations[46], clusters[93];
    uint8_t critical_start[8], critical_count[8];
    /* Four mech pose groups and fourteen personal-weapon groups; each row
       is a count followed by up to eight frames from original programs. */
    uint8_t poses[18][8][9], reaction[4], impact[3];
} BtpCombatData;
typedef struct {
    uint8_t record[125], x, y, direction, heat, pool, burning, cover;
    uint8_t infantry; /* record[0..16] is original C614 for labor robots. */
} BtpCombatUnit;
typedef struct { uint8_t hit, location, damage, destroyed, toppled; int16_t needed; } BtpShot;
typedef enum { BTP_COMBAT_NONE, BTP_COMBAT_CONTROL, BTP_COMBAT_MESSAGES, BTP_COMBAT_GRAPHICS,
    BTP_COMBAT_MENU, BTP_COMBAT_MOVE, BTP_COMBAT_WEAPONS, BTP_COMBAT_TARGET,
    BTP_COMBAT_SCAN, BTP_COMBAT_ROUND, BTP_COMBAT_NOTICE, BTP_COMBAT_KICK,
    BTP_COMBAT_REPLACE } BtpCombatPhase;
enum { BTP_COMBAT_UNITS = 7 };
typedef struct {
    BtpCombatUnit unit[BTP_COMBAT_UNITS];
    uint8_t phase, selected, messages, graphics, movement, goal_x, goal_y, goal_active;
    uint8_t cursor_x, cursor_y, weapon_selected, target_selected, scan_unit;
    uint8_t orders[11], step, delay, moved[BTP_COMBAT_UNITS], path_index[BTP_COMBAT_UNITS], walk[BTP_COMBAT_UNITS], notice, notice_return;
    uint8_t fled, won, last_weapon, last_event, plan_direction[BTP_COMBAT_UNITS], fallback[BTP_COMBAT_UNITS], enemy_movement;
    uint16_t round, fired;
    int8_t path[BTP_COMBAT_UNITS][12][2];
    BtpShot shot;
    uint8_t flash;
    uint8_t count, target_unit, kick_target, lost, last_attacker, last_target;
    uint8_t enemy_modes[BTP_COMBAT_UNITS-2], enemy_orders[BTP_COMBAT_UNITS-1][12];
    uint16_t enemy_fired[BTP_COMBAT_UNITS-1];
    uint8_t waypoint_count, waypoint_x[11], waypoint_y[11];
} BtpCombatState;
enum { BTP_COMBAT_SAVE_BYTES = 1536 };
enum { BTP_COMBAT_DATA_V1_BYTES = 4+375+561+15+46+93+16,
    BTP_COMBAT_DATA_BYTES = BTP_COMBAT_DATA_V1_BYTES+18*8*9+7 };
int btp_combat_data_decode(const uint8_t *bytes, size_t length, BtpCombatData *data);
unsigned btp_combat_die(uint8_t rng[3]);
unsigned btp_combat_dice(uint8_t rng[3]);
unsigned btp_combat_direction(int x, int y, int tx, int ty);
unsigned btp_combat_distance(int x, int y, int tx, int ty);
unsigned btp_combat_range(const BtpCombatData *data, unsigned weapon, int x, int y, int tx, int ty);
unsigned btp_combat_weapon(const BtpCombatUnit *unit, unsigned index);
unsigned btp_combat_weapon_count(const BtpCombatUnit *unit);
int btp_combat_points(const BtpCombatUnit *unit, unsigned movement);
void btp_combat_cool(BtpCombatUnit *unit, int movement, unsigned steps, unsigned terrain);
int btp_combat_critical(BtpCombatUnit *unit, const BtpCombatData *data, unsigned location, uint8_t rng[3]);
BtpShot btp_combat_shoot(BtpCombatUnit *attacker, BtpCombatUnit *target,
    const BtpCombatData *data, unsigned index, int movement, unsigned target_steps,
    unsigned skill, uint8_t rng[3]);
/* Mech index 11 is Kick; infantry index 0 uses its original personal weapon. */
BtpShot btp_combat_attack(BtpCombatUnit *attacker, BtpCombatUnit *target,
    const BtpCombatData *data, unsigned index, int movement, unsigned target_steps,
    unsigned skill, uint8_t rng[3]);
BtpShot btp_combat_attack_unit(BtpCombatUnit *attacker, BtpCombatUnit *target,
    const BtpCombatData *data, unsigned index, int movement, unsigned target_steps,
    unsigned skill, unsigned unit_id, uint8_t rng[3]);
int btp_combat_can_kick(const BtpCombatUnit *unit);
#endif
