#ifndef BTP_GAME_H
#define BTP_GAME_H
#include "data/resources.h"
#include "core/script.h"
typedef enum { BTP_IDLE, BTP_UP, BTP_DOWN, BTP_LEFT, BTP_RIGHT, BTP_ACCEPT, BTP_CANCEL,
    BTP_DIGIT_0, BTP_DIGIT_1, BTP_DIGIT_2, BTP_DIGIT_3, BTP_DIGIT_4,
    BTP_DIGIT_5, BTP_DIGIT_6, BTP_DIGIT_7, BTP_DIGIT_8, BTP_DIGIT_9, BTP_CLEAR_INPUT,
    BTP_UP_LEFT, BTP_UP_RIGHT, BTP_DOWN_LEFT, BTP_DOWN_RIGHT, BTP_OPEN_MENU, BTP_CREDIT_10000 } BtpAction;
typedef enum { BTP_CLEAR, BTP_WALL, BTP_EDGE, BTP_WATER } BtpBlock;
typedef enum { BTP_EXPLORE, BTP_ENTRY, BTP_BUILDING, BTP_SCRIPT_FAULT, BTP_QUIZ, BTP_MISSION, BTP_ACTIONS, BTP_ENCOUNTER, BTP_TITLE, BTP_GAME_OVER, BTP_LOGO, BTP_BEGIN, BTP_CACHE, BTP_ENDING, BTP_YARD, BTP_EVENT } BtpMode;
typedef enum { BTP_TALK_NONE, BTP_TALK_EMPTY, BTP_TALK_MENU, BTP_TALK_REPLY } BtpTalkPhase;
typedef struct {
    uint8_t phase, selected, count, mask, room, actor,reply;
} BtpTalkState;
typedef struct { uint16_t x, y; uint8_t direction; } BtpNpc;
typedef struct {
    uint8_t enabled, phase, rng[3], bias, fault, loop_timer, allowance_pending;
    uint16_t search, clock;
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
    BTP_MISSION_PICKUP, BTP_MISSION_RETURN } BtpMissionPhase;
typedef struct {
    uint8_t phase, corner, warned, idle, walk, direction;
    uint16_t elapsed;
    uint8_t assignment, rubble, rubble_under;
} BtpMissionState;
typedef struct {
    uint8_t active, kind, step, cycle, hold;
    uint16_t remaining, refresh_fraction;
} BtpCutsceneState;
/* Original D497 packs Y-sector/X-sector nibbles; x/y are half-tile offsets. */
typedef struct { uint8_t sprite, sector, x, y; } BtpTerrainMark;
typedef struct {
    uint8_t actor,target,group,direction,weapon,hit,dead,x,y,tx,ty,base,target_base;
} BtpCombatEffect;
/* Capture names/results when a shot resolves, before ejection or later shots
   change the records. Presentation consumes this alongside the saved effects. */
typedef struct { uint8_t active,actor,target,actor_name,target_name,weapon,hit,location,criticals,spectator,dead,authored,content_weapon; } BtpBattleText;
typedef struct { uint8_t active,name,mech[15],ejections; } BtpQuietReport;
typedef struct { uint8_t count,age,pending,stage,outtakes[24][2];BtpCombatEffect shots[24];BtpBattleText text[24],shown;BtpQuietReport quiet; } BtpEffectsState;
typedef struct {
    uint8_t invasion, owned, mech[125];
    uint8_t checkpoint_owned, checkpoint_mech[125];
    uint16_t world_x,world_y;
    uint8_t building, encounter_mask, encounter;
    uint16_t world_clock;
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
    uint8_t medical_kit,advanced_kit;
    uint16_t mech_x[4],mech_y[4];
} BtpPartyState;
typedef struct {
    uint8_t phase,action,mech,selected,kind,item,outcome;
    uint16_t amount;
    char input[8];
    /* 09B8 keeps an estimate separate from the repaired record. A weapon
       type can remain on that estimate after its first repair clears all
       matching critical slots. Preserve those original counts across saves. */
    uint8_t damaged[17];
    uint32_t quote_credits;
} BtpServiceState;
typedef struct {
    uint8_t active,countdown;
    uint16_t position,divisor,phase,irq_phase;
    uint32_t fraction;
    uint8_t sound_count,sounds[48];
    uint16_t event,sound_phase;
    uint32_t remaining,sound_fraction;
} BtpAudioState;
typedef struct { uint8_t count,kinds[24]; } BtpPresentationState;
typedef struct {
    uint16_t eject,cash;
    uint8_t phase,selected,pilot,unit,notice,applied,wrecks[24];
    /* 05AB:04F9 appends failed inspections until this pilot succeeds or
       exhausts the wrecks. Keep the visible sequence across native saves. */
    uint8_t attempts,inspected[16],models[16];
} BtpAftermathState;
enum { BTP_ORIGINAL_BYTES=3913 };
typedef struct { uint8_t valid,bytes[BTP_ORIGINAL_BYTES]; } BtpOriginalState;
typedef struct {
    uint8_t steps,sound,speed,outtakes,slot,io,notice,quit;
    uint16_t map_x,map_y;
    uint8_t from_intro,from_story;
    /* Zero retains old flat broker saves; 1..4 select a weight class. */
    uint8_t broker_class;
} BtpMenuState;
typedef struct {
    uint8_t active,phase,selected,terminal,notice,door,door_step,hall;
    uint8_t used[33],maproom[768];
} BtpCacheState;
/* Transient original event locals, made explicit so each popup/search can
   survive a native save. These byte fields have no compiler padding. */
typedef struct {
    uint8_t travel[10];
    uint8_t invasion_event,invasion_popup,invasion_end;
} BtpLateState;
typedef struct {
    uint8_t active,phase,timer,idle,checked,attempts,selected,slot,rental,variant,alarm;
    uint8_t ids[7],membership[8],types[4],mechs[4][125];
    uint8_t gate_count,gates[16][3]; /* normalized x, y, replacement tile */
} BtpYardState;
/* A continuation is a node identity within the fingerprinted package, never
   a C/Lua stack. A tick commits an effect and advances before any save pause. */
typedef struct {
    uint16_t node,map,return_map,origin_map;
    uint8_t enabled,phase,selected,page,origin_entry;
    uint16_t explore_offset;
    uint8_t explore_width,explore_height,planet;
    uint8_t flags[64],done[32],people[8];
} BtpEventState;
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
    BtpAudioState audio;
    BtpMenuState menu;
    BtpPresentationState presentation;
    BtpOriginalState original;
    BtpAftermathState aftermath;
    uint8_t explored[2048]; /* Original CB0C: 128 rows, sixteen MSB-first bytes. */
    BtpCacheState cache;
    BtpLateState late;
    BtpYardState yard;
    uint8_t disk_origin; /* Parent building while VIEWDISK runs as a child story. */
    uint8_t spy_discovered; /* Original transient word 374A, saved explicitly. */
    /* Authored combat policy travels with the campaign and held orders.
       Zero is Legacy, including every save predating this field. */
    uint8_t combat_profile;
    uint32_t combat_fingerprint;
    uint8_t project; /* Requires the package-bound save envelope, including before owning a custom mech. */
    BtpEventState event;
} BtpState;
enum { BTP_STATE_BYTES = 20480 };

void btp_start(BtpState *state);
const BtpCombatProfile *btp_active_combat_profile(const BtpState *state,const BtpResources *resources);
int btp_set_combat_profile(BtpState *state,const BtpResources *resources,unsigned enhanced);
void btp_game_building(BtpState *state,const BtpResources *resources,unsigned kind);
void btp_tick(BtpState *state, const BtpMap *map, BtpAction action);
void btp_game_tick(BtpState *state, const BtpResources *resources, BtpAction action);
void btp_game_tick_audio(BtpState *state, const BtpResources *resources, BtpAction action, int16_t *samples);
void btp_start_conversation_checkpoint(BtpState *state); /* Explicit controlled scenario */
void btp_start_shop_conversation_checkpoint(BtpState *state, const BtpResources *resources, unsigned slot);
int btp_game_text(const BtpState *state, const BtpResources *resources,
    uint8_t *output, size_t capacity, size_t *length);
int btp_entrance(const BtpState *state, const BtpMap *map); /* index, or -1 */
const BtpBld *btp_building_bld(const BtpResources *resources, unsigned slot);
const BtpMap *btp_active_map(const BtpResources *resources,const BtpState *state);
unsigned btp_building_kind(const BtpResources *resources,const BtpState *state);
const BtpBld *btp_state_bld(const BtpResources *resources,const BtpState *state);
/* state_codec.c preserves the original-profile payload and historic migrations. */
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
