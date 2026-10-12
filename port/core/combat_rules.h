#ifndef BTP_COMBAT_RULES_H
#define BTP_COMBAT_RULES_H
#include <stdint.h>
#include <stddef.h>
enum { BTP_SOUND_COUNT=18, BTP_SOUND_EVENTS=8192 };
typedef struct { uint32_t clocks; uint16_t divisor; uint8_t type,level; } BtpSpeakerEvent;

typedef struct {
    uint8_t loans[3][125], weapons[33][17], arcs[15], locations[46], clusters[93];
    uint8_t critical_start[8], critical_count[8];
    /* Four mech pose groups and fourteen personal-weapon groups; each row
       is a count followed by up to eight frames from original programs. */
    uint8_t poses[18][8][9], reaction[4], impact[3];
    uint8_t jenner[125];
    uint8_t commando[125], rex_skills[7], rex_x[8], rex_y[8];
    uint8_t encounter_weapons[22], encounter_mechs[3][125];
    uint16_t refit_prices[8];uint8_t ammo_prices[7], commando_armour[11];
    uint8_t building_portraits[26];
    uint16_t sound_calibration,sound_words[314],sound_count[BTP_SOUND_COUNT];
    BtpSpeakerEvent sound[BTP_SOUND_COUNT][BTP_SOUND_EVENTS];
    uint8_t medical[6][4];
    int8_t formation_x[8],formation_y[8],mech_formation_x[4],mech_formation_y[4];
    uint16_t medical_prices[8];
} BtpCombatData;
typedef struct {
    uint8_t record[125], x, y, direction, heat, pool, burning, cover;
    uint8_t infantry; /* record[0..16] is original C614 for labor robots. */
} BtpCombatUnit;
typedef struct { uint8_t hit, location, damage, destroyed, toppled; int16_t needed; } BtpShot;
typedef enum { BTP_COMBAT_NONE, BTP_COMBAT_CONTROL, BTP_COMBAT_MESSAGES, BTP_COMBAT_GRAPHICS,
    BTP_COMBAT_MENU, BTP_COMBAT_MOVE, BTP_COMBAT_WEAPONS, BTP_COMBAT_TARGET,
    BTP_COMBAT_SCAN, BTP_COMBAT_ROUND, BTP_COMBAT_NOTICE, BTP_COMBAT_KICK,
    BTP_COMBAT_REPLACE, BTP_COMBAT_PICK } BtpCombatPhase;
enum { BTP_COMBAT_UNITS = 24 };
typedef struct {
    uint8_t movement, x, y, active, count, wx[11], wy[11], orders[11], kick;
} BtpCombatPlan;
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
    uint8_t friends, active_unit, ids[BTP_COMBAT_UNITS];
    BtpCombatPlan plans[BTP_COMBAT_UNITS];
} BtpCombatState;
enum { BTP_COMBAT_LEGACY_BYTES=1536, BTP_COMBAT_SAVE_BYTES = 6144 };
enum { BTP_COMBAT_DATA_V1_BYTES = 4+375+561+15+46+93+16,
    BTP_COMBAT_DATA_V2_BYTES = BTP_COMBAT_DATA_V1_BYTES+18*8*9+7,
    BTP_COMBAT_DATA_V3_BYTES = BTP_COMBAT_DATA_V2_BYTES+125,
    BTP_COMBAT_DATA_V4_BYTES = BTP_COMBAT_DATA_V3_BYTES+125+7+16+22+375,
    BTP_COMBAT_DATA_V5_BYTES = BTP_COMBAT_DATA_V4_BYTES+16+7+11,
    BTP_COMBAT_DATA_V6_BYTES = BTP_COMBAT_DATA_V5_BYTES+26,
    BTP_COMBAT_DATA_V7_BYTES = BTP_COMBAT_DATA_V6_BYTES+630,
    BTP_COMBAT_DATA_BYTES = BTP_COMBAT_DATA_V7_BYTES+24+24+16 };
int btp_sound_programs(BtpCombatData *data);
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
