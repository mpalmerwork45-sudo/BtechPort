#ifndef BTP_NPC_H
#define BTP_NPC_H
#include "core/game.h"
enum { BTP_OUTDOOR_PERIOD = 1100, BTP_OUTDOOR_TICK = 224,
       BTP_NPC_BAD_MAP = 1, BTP_NPC_BAD_CONTEXT = 2 };
/* Hundredths of a nominal 70 Hz retrace: eleven retraces per idle update,
   with a 32 ms host tick. Keys restart the original outdoor countdown. */
int btp_outdoor_due(uint16_t *clock, BtpAction action);
/* Primary instruction/state evidence: docs/M2_NPC_EVIDENCE.md. */
uint8_t btp_rng_next(uint8_t state[3]);
void btp_npc_init(BtpState *state, const BtpMap *map);
void btp_npc_enter(BtpState *state, const BtpMap *map);
void btp_npc_advance(BtpState *state, const BtpMap *map);
void btp_npc_frame(BtpState *state, const BtpMap *map);
void btp_npc_tick(BtpState *state, const BtpMap *map);
void btp_npc_input(BtpState *state, const BtpMap *map, BtpAction action);
int btp_npc_valid(const BtpState *state, const BtpMap *map);
#endif
