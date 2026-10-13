#ifndef BTP_NPC_H
#define BTP_NPC_H
#include "core/game.h"
enum { BTP_NPC_FRAME_TICKS = 4, BTP_NPC_BAD_MAP = 1, BTP_NPC_BAD_CONTEXT = 2 };
/* Primary instruction/state evidence: docs/M2_NPC_EVIDENCE.md. */
uint8_t btp_rng_next(uint8_t state[3]);
void btp_npc_init(BtpState *state, const BtpMap *map);
void btp_npc_enter(BtpState *state, const BtpMap *map);
void btp_npc_advance(BtpState *state, const BtpMap *map);
void btp_npc_frame(BtpState *state, const BtpMap *map);
void btp_npc_tick(BtpState *state, const BtpMap *map);
int btp_npc_valid(const BtpState *state, const BtpMap *map);
#endif
