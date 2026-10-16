#ifndef BTP_EFFECTS_H
#define BTP_EFFECTS_H
#include "core/game.h"
enum { BTP_EFFECT_START, BTP_EFFECT_FIRE_SOUND, BTP_EFFECT_ATTACK,
    BTP_EFFECT_HIT_SOUND, BTP_EFFECT_IMPACT, BTP_EFFECT_DEATH_SOUND, BTP_EFFECT_LEGACY=6 };
unsigned btp_effects_sound(unsigned weapon);
unsigned btp_effects_fire_sound(unsigned weapon,int visible);
int btp_combat_visible(int x,int y,int infantry,int focus_x,int focus_y);
void btp_effects_tick(BtpState *state, const BtpResources *resources);
void btp_effects_begin_round(BtpState *state);
void btp_effects_shot(BtpState *state, unsigned actor, unsigned target, unsigned weapon);
void btp_effects_crush(BtpState *state, unsigned actor, unsigned target);
unsigned btp_effects_length(const BtpCombatEffect *effect, const BtpCombatData *data);
const BtpCombatEffect *btp_effects_pending_death(const BtpState *state, unsigned target);
const BtpCombatEffect *btp_effects_death(const BtpState *state, unsigned target);
int btp_effects_valid(const BtpState *state);
#endif
