#ifndef BTP_GAME_H
#define BTP_GAME_H
#include "data/resources.h"
#include "core/script.h"
typedef enum { BTP_IDLE, BTP_UP, BTP_DOWN, BTP_LEFT, BTP_RIGHT, BTP_ACCEPT, BTP_CANCEL,
    BTP_DIGIT_0, BTP_DIGIT_1, BTP_DIGIT_2, BTP_DIGIT_3, BTP_DIGIT_4,
    BTP_DIGIT_5, BTP_DIGIT_6, BTP_DIGIT_7, BTP_DIGIT_8, BTP_DIGIT_9, BTP_CLEAR_INPUT,
    BTP_UP_LEFT, BTP_UP_RIGHT, BTP_DOWN_LEFT, BTP_DOWN_RIGHT } BtpAction;
typedef enum { BTP_CLEAR, BTP_WALL, BTP_EDGE } BtpBlock;
typedef enum { BTP_EXPLORE, BTP_ENTRY, BTP_BUILDING, BTP_SCRIPT_FAULT, BTP_QUIZ, BTP_MISSION, BTP_ACTIONS, BTP_ENCOUNTER } BtpMode;
typedef enum { BTP_TALK_NONE, BTP_TALK_EMPTY, BTP_TALK_MENU, BTP_TALK_REPLY } BtpTalkPhase;
typedef struct {
    uint8_t phase, selected, count, mask, room, actor;
} BtpTalkState;
typedef struct { uint16_t x, y; uint8_t direction; } BtpNpc;
typedef struct {
    uint8_t enabled, phase, clock, rng[3], bias, fault, loop_timer, allowance_pending;
    uint16_t search;
    BtpNpc actor[8];
} BtpNpcState;
typedef enum { BTP_BANK_NONE, BTP_BANK_MENU, BTP_BANK_AMOUNT, BTP_BANK_MESSAGE } BtpBankPhase;
typedef enum { BTP_BANK_TRADED, BTP_BANK_NO_CASH, BTP_BANK_NO_STOCK,
    BTP_BANK_NOT_OWNED, BTP_BANK_ZERO } BtpBankOutcome;
typedef struct {
    uint8_t phase, company, outcome, clamped;
    uint32_t available, amount;
    char input[8]; /* Original accepts at most seven decimal digits. */
} BtpBankState;
typedef enum { BTP_SCHOOL_NONE, BTP_SCHOOL_PRICES, BTP_SCHOOL_TRANSCRIPT } BtpSchoolPhase;
typedef enum { BTP_SCHOOL_TRAINED, BTP_SCHOOL_NO_FUNDS, BTP_SCHOOL_MASTERED } BtpSchoolOutcome;
typedef struct { uint8_t phase, course, before, outcome; } BtpSchoolState;
typedef enum { BTP_QUIZ_NONE, BTP_QUIZ_INTRO, BTP_QUIZ_QUESTION, BTP_QUIZ_FAILED } BtpQuizPhase;
typedef struct { uint8_t phase, selected, round, point, failed; uint16_t used; } BtpQuizState;
typedef enum { BTP_MISSION_NONE, BTP_MISSION_DRIVE, BTP_MISSION_WARNING,
    BTP_MISSION_CORNER, BTP_MISSION_RESULT, BTP_MISSION_SNICKER,
    BTP_MISSION_PICKUP } BtpMissionPhase;
typedef struct {
    uint8_t phase, corner, warned, idle, walk, direction;
    uint16_t elapsed;
    uint8_t assignment, rubble, rubble_under;
} BtpMissionState;
typedef struct {
    uint8_t active, kind, step, cycle, hold;
    uint16_t remaining, refresh_fraction;
} BtpCutsceneState;
typedef struct { uint8_t sprite, map, x, y; } BtpTerrainMark;
typedef struct {
    uint8_t actor,target,group,direction,weapon,hit,dead,x,y,tx,ty,base,target_base;
} BtpCombatEffect;
typedef struct { uint8_t count,age,pending;BtpCombatEffect shots[7]; } BtpEffectsState;
typedef struct {
    uint8_t invasion, owned, mech[125];
    uint8_t checkpoint_owned, checkpoint_mech[125];
    uint16_t world_x,world_y;
    uint8_t building, world_clock, encounter_mask, encounter;
    uint8_t mounted, mech_walk, mech_direction;
    uint8_t ui, selected, member;
    uint16_t mech_x,mech_y;
    uint16_t battle_x,battle_y,return_x,return_y;
    uint8_t return_map;
} BtpCampaignState;
typedef struct {
    uint8_t enabled,next_id, people[8][17], mech_types[4], mechs[3][125];
    uint16_t x[8],y[8];
    uint8_t walk[8],direction[8], selected,giver,item,phase;
} BtpPartyState;
typedef struct {
    uint8_t phase,action,mech,selected,kind,item,outcome;
    uint16_t amount;
    char input[8];
} BtpServiceState;
typedef struct {
    uint32_t tick;
    uint16_t x_half, y_half;
    uint8_t map_id, gate, facing, blocked;
    uint8_t mode, entry_selected, entry_slot;
    uint8_t story_flags[BTP_STORY_BYTES]; /* sparse window defined in script.h */
    uint8_t story_checkpoint[BTP_STORY_BYTES], checkpoint_valid;
    BtpScriptState script;
    uint8_t npc_pairs[8][2]; /* D398/D399 at stride 26 */
    BtpNpcState npc;
    uint8_t talk_result, recruitment; /* D33A and D339 */
    uint8_t checkpoint_talk_result, conversation_checkpoint;
    BtpTalkState talk;
    uint32_t credits, checkpoint_credits;
    uint16_t allowance_cap;
    uint8_t weapon, armor, armor_points;
    uint8_t checkpoint_weapon, checkpoint_armor, checkpoint_armor_points;
    uint32_t investments[3], checkpoint_investments[3];
    BtpBankState bank;
    uint8_t skills[3], checkpoint_skills[3]; /* Original C618[0..2], ranks 0..4. */
    BtpSchoolState school;
    uint8_t player_walk, npc_walk[8]; /* Human frames 16..31, stored minus 16. */
    uint8_t entry_action;
    uint16_t checkpoint_allowance_cap;
    BtpQuizState quiz;
    BtpMissionState mission;
    uint8_t mech_skills[2], checkpoint_mech_skills[2]; /* Original C61B/C61C. */
    BtpCutsceneState cutscene;
    BtpCombatState combat;
    uint8_t technician, apprentice, checkpoint_technician, checkpoint_apprentice;
    /* Original D457/D497/D4D7/D517 ring: visual map marks, not terrain tiles. */
    BtpTerrainMark terrain_marks[64];
    uint8_t terrain_next;
    BtpEffectsState effects;
    BtpCampaignState campaign;
    BtpPartyState party,party_checkpoint;
    BtpServiceState service;
} BtpState;
enum { BTP_STATE_BYTES = 16384 };

void btp_start(BtpState *state);
void btp_tick(BtpState *state, const BtpMap *map, BtpAction action);
void btp_game_tick(BtpState *state, const BtpResources *resources, BtpAction action);
void btp_start_conversation_checkpoint(BtpState *state); /* Explicit controlled scenario */
void btp_start_shop_conversation_checkpoint(BtpState *state, const BtpResources *resources, unsigned slot);
int btp_game_text(const BtpState *state, const BtpResources *resources,
    uint8_t *output, size_t capacity, size_t *length);
int btp_entrance(const BtpState *state, const BtpMap *map); /* index, or -1 */
const BtpBld *btp_building_bld(const BtpResources *resources, unsigned slot);
const BtpMap *btp_active_map(const BtpResources *resources,const BtpState *state);
unsigned btp_building_kind(const BtpResources *resources,const BtpState *state);
const BtpBld *btp_state_bld(const BtpResources *resources,const BtpState *state);
void btp_state_encode(const BtpState *state, uint8_t output[BTP_STATE_BYTES]);
int btp_state_decode(const uint8_t *bytes, size_t length, const BtpMap *map,
    const BtpBld *script, BtpState *state);
const char *btp_mode_name(unsigned mode);
const char *btp_action_name(BtpAction action);
int btp_action_parse(const char *name, BtpAction *action);
int btp_action_moves(BtpAction action);
int btp_action_dx(BtpAction action);
int btp_action_dy(BtpAction action);
#endif
