#ifndef BTP_COMBAT_RULES_H
#define BTP_COMBAT_RULES_H
#include <stdint.h>
#include <stddef.h>

typedef struct {
    uint8_t loans[3][125], weapons[33][17], arcs[15], locations[46], clusters[93];
    uint8_t critical_start[8], critical_count[8];
} BtpCombatData;
typedef struct {
    uint8_t record[125], x, y, direction, heat, pool, burning, cover;
} BtpCombatUnit;
typedef struct { uint8_t hit, location, damage, destroyed, toppled; int16_t needed; } BtpShot;
typedef enum { BTP_COMBAT_NONE, BTP_COMBAT_CONTROL, BTP_COMBAT_MESSAGES, BTP_COMBAT_GRAPHICS,
    BTP_COMBAT_MENU, BTP_COMBAT_MOVE, BTP_COMBAT_WEAPONS, BTP_COMBAT_TARGET,
    BTP_COMBAT_SCAN, BTP_COMBAT_ROUND, BTP_COMBAT_NOTICE } BtpCombatPhase;
typedef struct {
    BtpCombatUnit unit[2];
    uint8_t phase, selected, messages, graphics, movement, goal_x, goal_y, goal_active;
    uint8_t cursor_x, cursor_y, weapon_selected, target_selected, scan_unit;
    uint8_t orders[11], step, delay, moved[2], path_index[2], walk[2], notice, notice_return;
    uint8_t fled, won, last_weapon, last_event, plan_direction[2], fallback[2], enemy_movement;
    uint16_t round, fired;
    int8_t path[2][12][2];
    BtpShot shot;
} BtpCombatState;
enum { BTP_COMBAT_SAVE_BYTES = 384 };
enum { BTP_COMBAT_DATA_BYTES = 4+375+561+15+46+93+16 };
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
#endif
