#ifndef BTP_GAME_H
#define BTP_GAME_H
#include "data/resources.h"
typedef enum { BTP_IDLE, BTP_UP, BTP_DOWN, BTP_LEFT, BTP_RIGHT } BtpAction;
typedef enum { BTP_CLEAR, BTP_WALL, BTP_EDGE } BtpBlock;
typedef struct {
    uint32_t tick;
    uint16_t x_half, y_half;
    uint8_t map_id, gate, facing, blocked;
} BtpState;
enum { BTP_STATE_BYTES = 24 };

void btp_start(BtpState *state);
void btp_tick(BtpState *state, const BtpMap *map, BtpAction action);
int btp_entrance(const BtpState *state, const BtpMap *map); /* index, or -1 */
void btp_state_encode(const BtpState *state, uint8_t output[BTP_STATE_BYTES]);
int btp_state_decode(const uint8_t *bytes, size_t length, const BtpMap *map, BtpState *state);
const char *btp_action_name(BtpAction action);
int btp_action_parse(const char *name, BtpAction *action);
#endif
