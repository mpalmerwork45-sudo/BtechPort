#ifndef BTP_EFFECTS_H
#define BTP_EFFECTS_H
#include "core/game.h"
void btp_effects_tick(BtpState *state, const BtpResources *resources);
void btp_effects_shot(BtpState *state, unsigned actor, unsigned target, unsigned weapon);
unsigned btp_effects_length(const BtpCombatEffect *effect, const BtpCombatData *data);
int btp_effects_valid(const BtpState *state);
#endif
