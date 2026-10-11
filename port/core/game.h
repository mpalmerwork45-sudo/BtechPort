#ifndef BTP_GAME_H
#define BTP_GAME_H
#include "data/resources.h"
#include "core/script.h"
typedef enum { BTP_IDLE, BTP_UP, BTP_DOWN, BTP_LEFT, BTP_RIGHT, BTP_ACCEPT, BTP_CANCEL } BtpAction;
typedef enum { BTP_CLEAR, BTP_WALL, BTP_EDGE } BtpBlock;
typedef enum { BTP_EXPLORE, BTP_ENTRY, BTP_BUILDING, BTP_SCRIPT_FAULT } BtpMode;
typedef struct {
    uint32_t tick;
    uint16_t x_half, y_half;
    uint8_t map_id, gate, facing, blocked;
    uint8_t mode, entry_selected, entry_slot;
    uint8_t story_flags[16]; /* original D30C[0..15] projection; meanings provisional */
    BtpScriptState script;
} BtpState;
enum { BTP_STATE_BYTES = 64 };

void btp_start(BtpState *state);
void btp_tick(BtpState *state, const BtpMap *map, BtpAction action);
void btp_game_tick(BtpState *state, const BtpResources *resources, BtpAction action);
int btp_entrance(const BtpState *state, const BtpMap *map); /* index, or -1 */
void btp_state_encode(const BtpState *state, uint8_t output[BTP_STATE_BYTES]);
int btp_state_decode(const uint8_t *bytes, size_t length, const BtpMap *map,
    const BtpBld *script, BtpState *state);
const char *btp_mode_name(unsigned mode);
const char *btp_action_name(BtpAction action);
int btp_action_parse(const char *name, BtpAction *action);
#endif
