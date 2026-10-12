#ifndef BTP_EFFECTS_H
#define BTP_EFFECTS_H
#include "core/game.h"
enum { BTP_EFFECT_START, BTP_EFFECT_FIRE_SOUND, BTP_EFFECT_ATTACK,
    BTP_EFFECT_HIT_SOUND, BTP_EFFECT_IMPACT, BTP_EFFECT_DEATH_SOUND, BTP_EFFECT_LEGACY=6 };
unsigned btp_effects_sound(unsigned weapon);
unsigned btp_effects_fire_sound(unsigned weapon,int visible);
void btp_effects_tick(BtpState *state, const BtpResources *resources);
void btp_effects_shot(BtpState *state, unsigned actor, unsigned target, unsigned weapon);
unsigned btp_effects_length(const BtpCombatEffect *effect, const BtpCombatData *data);
int btp_effects_valid(const BtpState *state);
#endif
