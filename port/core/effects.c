#include "core/effects.h"
#include "core/audio.h"
#include <string.h>
_Static_assert(sizeof(BtpCombatEffect)==13,"Effect encoding contains byte fields only");
unsigned btp_effects_sound(unsigned w)
{
    return w<3 ? 13u : w==3 ? 5u : w<=6 ? 11u : w<=8 ? 6u :
        w==9 || (w>=19 && w<=23) ? 3u : w==10 || w==11 || (w>=25 && w<=31) ? 1u :
        w==12 || w==13 ? 9u : w>=15 && w<=18 ? 2u : 0u;
}

unsigned btp_effects_length(const BtpCombatEffect *e, const BtpCombatData *d)
{
    unsigned pose=d->poses[e->group][e->direction][0];
    return 2u*(pose+(e->hit && e->weapon>=7 ? 3u : 0u));
}
void btp_effects_shot(BtpState *s,unsigned actor,unsigned target,unsigned weapon)
{
    BtpCombatState *c=&s->combat;BtpEffectsState *v=&s->effects;
    if (v->count>=24) return; /* At most one shot per unit in a microstep. */
    const BtpCombatUnit *a=&c->unit[actor],*t=&c->unit[target];
    unsigned alt=!a->infantry && a->record[0]!='L';
    unsigned group=a->infantry ? 4u+weapon : (weapon==32 ? 2u : 0u)+alt;
    unsigned direction=btp_combat_direction(a->x,a->y,t->x,t->y);
    if (direction>7) direction=a->direction;
    v->shots[v->count++]=(BtpCombatEffect){(uint8_t)actor,(uint8_t)target,(uint8_t)group,
        (uint8_t)direction,(uint8_t)weapon,c->shot.hit,c->shot.destroyed,a->x,a->y,t->x,t->y,
        (uint8_t)(a->infantry ? 254 : alt ? 146 : 0),
        (uint8_t)(t->infantry ? 254 : t->record[0]=='L' ? 0 : 146)};
}
void btp_effects_tick(BtpState *s,const BtpResources *r)
{
    BtpEffectsState *v=&s->effects;
    if (!v->count) return;
    const BtpCombatEffect *e=&v->shots[0];
    if (v->stage==BTP_EFFECT_START) {
        if (s->audio.sound_count) return;
        if (s->combat.graphics) btp_audio_effect(s,btp_effects_sound(e->weapon));
        v->stage=BTP_EFFECT_FIRE_SOUND;return;
    }
    if (s->audio.sound_count) return;
    if (v->stage==BTP_EFFECT_FIRE_SOUND) v->stage=BTP_EFFECT_ATTACK;
    if (v->stage==BTP_EFFECT_HIT_SOUND) v->stage=BTP_EFFECT_IMPACT;
    unsigned pose=2u*r->combat.poses[e->group][e->direction][0];
    if (v->stage==BTP_EFFECT_ATTACK && ++v->age>=pose) {
        if (e->hit) {
            if (s->combat.graphics) btp_audio_effect(s,4);
            v->stage=BTP_EFFECT_HIT_SOUND;return;
        }
    } else if (v->stage==BTP_EFFECT_IMPACT || v->stage==BTP_EFFECT_LEGACY) ++v->age;
    if (v->age<btp_effects_length(e,&r->combat)) return;
    for (unsigned i=0;i<2;++i) if (v->outtakes[0][i] && s->presentation.count<24)
        s->presentation.kinds[s->presentation.count++]=v->outtakes[0][i];
    unsigned legacy=v->stage==BTP_EFFECT_LEGACY;
    v->age=0;--v->count;
    memmove(v->shots,v->shots+1,v->count*sizeof v->shots[0]);
    memset(&v->shots[v->count],0,sizeof v->shots[0]);
    memmove(v->outtakes,v->outtakes+1,v->count*sizeof v->outtakes[0]);
    memset(v->outtakes[v->count],0,sizeof v->outtakes[0]);
    v->stage=(uint8_t)(v->count && legacy ? BTP_EFFECT_LEGACY : BTP_EFFECT_START);
}
int btp_effects_valid(const BtpState *s)
{
    const BtpEffectsState *v=&s->effects;
    if (v->count>24 || v->age>21 || v->pending>3 || v->stage>6 || v->stage==5 || (!v->count && (v->age || v->stage))) return 0;
    if (v->count && s->combat.phase!=BTP_COMBAT_ROUND) return 0;
    /* The saved boundary after the final outtake has no remaining frames;
       the following logical tick performs the pending outcome transition. */
    if (v->pending && (s->combat.phase!=BTP_COMBAT_ROUND || (v->pending!=3 && !s->combat.shot.destroyed))) return 0;
    for (unsigned i=0;i<24;++i) {
        for (unsigned j=0;j<2;++j) if (v->outtakes[i][j]>=BTP_ANM_COUNT || (i>=v->count && v->outtakes[i][j])) return 0;
        const BtpCombatEffect *e=&v->shots[i];
        if (i<v->count) {
            if (e->actor>=s->combat.count || e->target>=s->combat.count || e->group>=18 || e->direction>7 || e->weapon>32 ||
                e->hit>1 || e->dead>1 || e->x>127 || e->y>127 || e->tx>127 || e->ty>127 ||
                (e->base!=0 && e->base!=146 && e->base!=254) ||
                (e->target_base!=0 && e->target_base!=146 && e->target_base!=254)) return 0;
            if (e->base!=(e->group>=4 ? 254 : e->group&1u ? 146 : 0) || (e->dead && !e->hit)) return 0;
        } else {
            const uint8_t *p=(const uint8_t *)e;
            for (unsigned j=0;j<sizeof *e;++j) if (p[j]) return 0;
        }
    }
    return 1;
}
