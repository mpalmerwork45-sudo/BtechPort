#include "core/effects.h"
#include <string.h>
_Static_assert(sizeof(BtpCombatEffect)==13,"Effect encoding contains byte fields only");

unsigned btp_effects_length(const BtpCombatEffect *e, const BtpCombatData *d)
{
    unsigned pose=d->poses[e->group][e->direction][0];
    return 2u*(pose+(e->hit && e->weapon>=7 ? 3u : 0u));
}
void btp_effects_shot(BtpState *s,unsigned actor,unsigned target,unsigned weapon)
{
    BtpCombatState *c=&s->combat;BtpEffectsState *v=&s->effects;
    if (v->count>=7) return; /* A microstep has at most seven active units. */
    const BtpCombatUnit *a=&c->unit[actor],*t=&c->unit[target];
    unsigned alt=!a->infantry && actor==0 && s->story_flags[2]!=0;
    unsigned group=a->infantry ? 4u+weapon : (weapon==32 ? 2u : 0u)+alt;
    unsigned direction=btp_combat_direction(a->x,a->y,t->x,t->y);
    if (direction>7) direction=a->direction;
    v->shots[v->count++]=(BtpCombatEffect){(uint8_t)actor,(uint8_t)target,(uint8_t)group,
        (uint8_t)direction,(uint8_t)weapon,c->shot.hit,c->shot.destroyed,a->x,a->y,t->x,t->y,
        (uint8_t)(a->infantry ? 254 : alt ? 146 : 0),
        (uint8_t)(t->infantry ? 254 : target==0 && s->story_flags[2] ? 146 : 0)};
}
void btp_effects_tick(BtpState *s,const BtpResources *r)
{
    BtpEffectsState *v=&s->effects;
    if (!v->count) return;
    if (++v->age<btp_effects_length(&v->shots[0],&r->combat)) return;
    v->age=0;--v->count;
    memmove(v->shots,v->shots+1,v->count*sizeof v->shots[0]);
    memset(&v->shots[v->count],0,sizeof v->shots[0]);
}
int btp_effects_valid(const BtpState *s)
{
    const BtpEffectsState *v=&s->effects;
    if (v->count>7 || v->age>21 || v->pending>2 || (!v->count && v->age)) return 0;
    if (v->count && s->combat.phase!=BTP_COMBAT_ROUND) return 0;
    if (v->pending && (s->combat.phase!=BTP_COMBAT_ROUND || !v->count)) return 0;
    for (unsigned i=0;i<7;++i) {
        const BtpCombatEffect *e=&v->shots[i];
        if (i<v->count) {
            if (e->actor>=s->combat.count || e->target>=s->combat.count || e->group>=18 || e->direction>7 || e->weapon>32 ||
                e->hit>1 || e->dead>1 || e->x>125 || e->y>127 || e->tx>125 || e->ty>127 ||
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
