#ifndef BTP_EFFECTS_H
#define BTP_EFFECTS_H
#include "core/game.h"
enum { BTP_EFFECT_START, BTP_EFFECT_FIRE_SOUND, BTP_EFFECT_ATTACK,
    BTP_EFFECT_HIT_SOUND, BTP_EFFECT_IMPACT, BTP_EFFECT_DEATH_SOUND, BTP_EFFECT_LEGACY=6,
    /* Separate tags let old saved presentations finish with their old clock. */
    BTP_EFFECT_POSES, BTP_EFFECT_SHOT_SOUND, BTP_EFFECT_FLIGHT,
    BTP_EFFECT_BEAM_SOUND, BTP_EFFECT_STRIKE_SOUND, BTP_EFFECT_IMPACT_HOLD,
    BTP_EFFECT_RETIRE_SOUND, BTP_EFFECT_PENDING };
enum { BTP_EFFECT_TRAIL_POINTS=224 };
typedef struct { int16_t x,y;uint16_t sprite; } BtpEffectPoint;
typedef struct { unsigned kind,count;BtpEffectPoint points[BTP_EFFECT_TRAIL_POINTS]; } BtpEffectTrail;
unsigned btp_effects_trail_kind(unsigned weapon);
void btp_effects_trail(const BtpCombatEffect *effect,const BtpCombatData *data,int cx,int cy,BtpEffectTrail *trail);
unsigned btp_effects_beam_color(const BtpCombatEffect *effect,unsigned actor_id);
int btp_effects_pose(const BtpState *state,const BtpCombatData *data);
int btp_effects_reaction(const BtpState *state);
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
