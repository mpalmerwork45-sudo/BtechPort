#ifndef BTP_GAME_H
#define BTP_GAME_H
#include "data/resources.h"
#include "core/script.h"
typedef enum { BTP_IDLE, BTP_UP, BTP_DOWN, BTP_LEFT, BTP_RIGHT, BTP_ACCEPT, BTP_CANCEL } BtpAction;
typedef enum { BTP_CLEAR, BTP_WALL, BTP_EDGE } BtpBlock;
typedef enum { BTP_EXPLORE, BTP_ENTRY, BTP_BUILDING, BTP_SCRIPT_FAULT } BtpMode;
typedef enum { BTP_TALK_NONE, BTP_TALK_EMPTY, BTP_TALK_MENU, BTP_TALK_REPLY } BtpTalkPhase;
typedef struct {
    uint8_t phase, selected, count, mask, room, actor;
} BtpTalkState;
typedef struct {
    uint32_t tick;
    uint16_t x_half, y_half;
    uint8_t map_id, gate, facing, blocked;
    uint8_t mode, entry_selected, entry_slot;
    uint8_t story_flags[BTP_STORY_BYTES]; /* D30C[0..22]; byte 22 countdown pacing is deferred */
    uint8_t story_checkpoint[BTP_STORY_BYTES], checkpoint_valid;
    BtpScriptState script;
    uint8_t npc_pairs[8][2]; /* D398/D399 at stride 26; no NPC travel simulation yet */
    uint8_t talk_result, recruitment; /* D33A and D339 */
    uint8_t checkpoint_talk_result, conversation_checkpoint;
    BtpTalkState talk;
} BtpState;
enum { BTP_STATE_BYTES = 160 };

void btp_start(BtpState *state);
void btp_tick(BtpState *state, const BtpMap *map, BtpAction action);
void btp_game_tick(BtpState *state, const BtpResources *resources, BtpAction action);
void btp_start_conversation_checkpoint(BtpState *state); /* Explicit controlled scenario */
int btp_game_text(const BtpState *state, const BtpResources *resources,
    uint8_t *output, size_t capacity, size_t *length);
int btp_entrance(const BtpState *state, const BtpMap *map); /* index, or -1 */
void btp_state_encode(const BtpState *state, uint8_t output[BTP_STATE_BYTES]);
int btp_state_decode(const uint8_t *bytes, size_t length, const BtpMap *map,
    const BtpBld *script, BtpState *state);
const char *btp_mode_name(unsigned mode);
const char *btp_action_name(BtpAction action);
int btp_action_parse(const char *name, BtpAction *action);
#endif
