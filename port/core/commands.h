#ifndef BTP_COMMANDS_H
#define BTP_COMMANDS_H
#include "core/game.h"

/* Small operations already needed by the original game. Future event/Lua
   bindings can use these without receiving writable raw state or DOS offsets.
   Each call completes within one tick; callers own UI and continuation. */
int btp_party_has_person(const BtpState *state, unsigned identity);
int btp_party_has_skill(const BtpState *state, unsigned skill, unsigned minimum);
int btp_try_spend_credits(BtpState *state, uint32_t amount);
int btp_grant_credits(BtpState *state,uint32_t amount);
int btp_recruit_person(BtpState *state,const uint8_t person[17]);
#endif
