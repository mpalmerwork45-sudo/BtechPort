#include "core/effects.h"
#include "core/audio.h"
#include "core/animation.h"
#include "core/combat.h"
#include <string.h>
_Static_assert(sizeof(BtpCombatEffect)==13,"Effect encoding contains byte fields only");
_Static_assert(sizeof(BtpBattleText)==10,"Battle text encoding contains byte fields only");
static unsigned name_id(const BtpState *s,unsigned actor)
{
    const BtpCombatUnit *u=&s->combat.unit[actor];
    if (u->infantry) return u->record[0]<10 ? u->record[0] : 0u;
    unsigned pilot=u->record[121];
    return s->party.enabled && pilot<8 && s->party.people[pilot][0]<10 ? s->party.people[pilot][0] : 0u;
}
static BtpBattleText report(const BtpState *s,unsigned actor,unsigned target,unsigned weapon)
{
    const BtpCombatState *c=&s->combat;
    return (BtpBattleText){1,(uint8_t)btp_combat_id(c,actor),(uint8_t)btp_combat_id(c,target),
        (uint8_t)name_id(s,actor),(uint8_t)name_id(s,target),(uint8_t)weapon,c->shot.hit,c->shot.location,
        c->shot.criticals,(uint8_t)(s->campaign.encounter==4 && s->yard.rental && !s->story_flags[35] && btp_combat_id(c,target)==13)};
}
unsigned btp_effects_sound(unsigned w)
{
    return w<3 ? 13u : w==3 ? 5u : w<=6 ? 11u : w<=8 ? 6u :
        w==9 || (w>=19 && w<=23) ? 3u : w==10 || w==11 || (w>=25 && w<=31) ? 1u :
        w==12 || w==13 ? 9u : w>=15 && w<=18 ? 2u : 0u;
}
unsigned btp_effects_fire_sound(unsigned w,int visible)
{
    /* 12E8:1680..169A skips beam playback when both units are off screen.
       Physical, ballistic and missile sounds precede that visibility test. */
    return !visible && (w==12 || w==13 || (w>=15 && w<=18)) ? 0u : btp_effects_sound(w);
}
static int visible(const BtpCombatEffect *e,const BtpState *s)
{
    const BtpCombatState *c=&s->combat;
    const BtpCombatUnit *focus=&c->unit[c->active_unit];
    const BtpCombatEffect *death=btp_effects_death(s,c->active_unit);
    unsigned x=death ? death->tx : focus->x,y=death ? death->ty : focus->y;
    /* Match 0000:0E4B's distinct infantry and mech drawing anchors. */
    int ax=(e->base==254 ? 208 : 200)+((int)e->x-(int)x)*8;
    int ay=(e->base==254 ? 96 : 80)+((int)e->y-(int)y)*8;
    int tx=(e->target_base==254 ? 208 : 200)+((int)e->tx-(int)x)*8;
    int ty=(e->target_base==254 ? 96 : 80)+((int)e->ty-(int)y)*8;
    /* Use the renderer's clipped viewport. Exact DOS visibility margins
       at the border remain approximate until their full pixel comparison. */
    return (ax+24>104 && ax<320 && ay+24>0 && ay<200) || (tx+24>104 && tx<320 && ty+24>0 && ty<200);
}
const BtpCombatEffect *btp_effects_death(const BtpState *s,unsigned target)
{
    for (unsigned i=0;i<s->effects.count;++i)
        if (s->effects.shots[i].dead && s->effects.shots[i].target==target) return &s->effects.shots[i];
    return NULL;
}

unsigned btp_effects_length(const BtpCombatEffect *e, const BtpCombatData *d)
{
    unsigned pose=d->poses[e->group][e->direction][0];
    return 2u*(pose+(e->hit && e->weapon>=7 ? 3u : 0u));
}
const BtpCombatEffect *btp_effects_pending_death(const BtpState *s,unsigned target)
{
    /* Numeric attacks finish the entire microstep before presentation. Keep
       a destroyed unit's captured sprite/position until its own death event,
       rather than exposing a later attack's wreck during an earlier shot. The
       existing saved effect record holds everything needed for restoration. */
    for (unsigned i=0;i<s->effects.count;++i) {
        const BtpCombatEffect *e=&s->effects.shots[i];
        if (e->dead && e->target==target && (i || s->effects.stage<BTP_EFFECT_DEATH_SOUND)) return e;
    }
    return NULL;
}
void btp_effects_shot(BtpState *s,unsigned actor,unsigned target,unsigned weapon)
{
    BtpCombatState *c=&s->combat;BtpEffectsState *v=&s->effects;
    if (v->count>=24) return; /* At most one shot per unit in a microstep. */
    const BtpCombatUnit *a=&c->unit[actor],*t=&c->unit[target];
    unsigned friends=c->friends ? c->friends : 1u;
    unsigned alt=!a->infantry && btp_mech_sprite_base(a->record[0],actor>=friends)!=0;
    unsigned group=a->infantry ? 4u+weapon : (weapon==32 ? 2u : 0u)+alt;
    unsigned direction=btp_combat_direction(a->x,a->y,t->x,t->y);
    if (direction>7) direction=a->direction;
    v->text[v->count]=report(s,actor,target,weapon);
    v->shots[v->count++]=(BtpCombatEffect){(uint8_t)actor,(uint8_t)target,(uint8_t)group,
        (uint8_t)direction,(uint8_t)weapon,c->shot.hit,c->shot.destroyed,a->x,a->y,t->x,t->y,
        (uint8_t)(a->infantry ? 254 : alt ? 146 : 0),
        (uint8_t)(t->infantry ? 254 : t->record[0]=='s' ? 16 : btp_mech_sprite_base(t->record[0],target>=friends))};
}
void btp_effects_crush(BtpState *s,unsigned actor,unsigned target)
{
    /* 0E31:19FC..1A93 plays effect 18 before marking a trampled soldier.
       Weapon 33 is the saved presentation discriminator, not a gun order. */
    BtpCombatState *c=&s->combat;BtpEffectsState *v=&s->effects;
    if (v->count>=24) return;
    const BtpCombatUnit *a=&c->unit[actor],*t=&c->unit[target];
    unsigned alt=btp_mech_sprite_base(a->record[0],actor>=(c->friends ? c->friends : 1u))!=0;
    v->text[v->count]=report(s,actor,target,33);
    v->text[v->count].hit=1;v->text[v->count].location=v->text[v->count].criticals=0;
    v->shots[v->count++]=(BtpCombatEffect){(uint8_t)actor,(uint8_t)target,(uint8_t)alt,
        a->direction,33,1,1,a->x,a->y,t->x,t->y,(uint8_t)(alt ? 146 : 0),254};
}
void btp_effects_tick(BtpState *s,const BtpResources *r)
{
    BtpEffectsState *v=&s->effects;
    if (!v->count) return;
    const BtpCombatEffect *e=&v->shots[0];
    if (v->stage==BTP_EFFECT_START) {
        if (s->audio.sound_count) return;
        if (e->weapon==33) btp_audio_effect(s,18);
        else if (s->combat.graphics) btp_audio_effect(s,btp_effects_fire_sound(e->weapon,visible(e,s)));
        v->stage=BTP_EFFECT_FIRE_SOUND;return;
    }
    if (s->audio.sound_count) return;
    if (e->weapon==33 && v->stage==BTP_EFFECT_FIRE_SOUND) { v->stage=BTP_EFFECT_DEATH_SOUND;return; }
    if (v->stage==BTP_EFFECT_FIRE_SOUND) v->stage=BTP_EFFECT_ATTACK;
    if (v->stage==BTP_EFFECT_HIT_SOUND) v->stage=BTP_EFFECT_IMPACT;
    unsigned pose=2u*r->combat.poses[e->group][e->direction][0];
    if (v->stage==BTP_EFFECT_ATTACK && ++v->age>=pose) {
        if (e->hit) {
            if (s->combat.graphics) btp_audio_effect(s,4);
            v->stage=BTP_EFFECT_HIT_SOUND;return;
        }
    } else if (v->stage==BTP_EFFECT_IMPACT || v->stage==BTP_EFFECT_LEGACY) ++v->age;
    if (e->weapon!=33 && v->age<btp_effects_length(e,&r->combat)) return;
    if (e->dead && e->target_base!=254 && v->stage!=BTP_EFFECT_DEATH_SOUND && v->stage!=BTP_EFFECT_LEGACY) {
        /* 12E8:1C76 plays sound 8 for a wreck. The rented arena target's
           branch uses sound 7 before its two alarm messages instead. Wait
           for this clip before any outtake or outcome can advance. Humans
           take 1B7F's corpse branch and skip the wreck/sound-8 branch. */
        btp_audio_effect(s,s->campaign.encounter==4 && btp_combat_id(&s->combat,e->target)==13 ? 7u : 8u);
        v->stage=BTP_EFFECT_DEATH_SOUND;return;
    }
    for (unsigned i=0;i<2;++i) if (v->outtakes[0][i] && s->presentation.count<24)
        s->presentation.kinds[s->presentation.count++]=v->outtakes[0][i];
    unsigned legacy=v->stage==BTP_EFFECT_LEGACY;
    v->shown=v->text[0];
    v->age=0;--v->count;
    memmove(v->shots,v->shots+1,v->count*sizeof v->shots[0]);
    memset(&v->shots[v->count],0,sizeof v->shots[0]);
    memmove(v->outtakes,v->outtakes+1,v->count*sizeof v->outtakes[0]);
    memset(v->outtakes[v->count],0,sizeof v->outtakes[0]);
    memmove(v->text,v->text+1,v->count*sizeof v->text[0]);
    memset(&v->text[v->count],0,sizeof v->text[0]);
    v->stage=(uint8_t)(v->count && legacy ? BTP_EFFECT_LEGACY : BTP_EFFECT_START);
}
int btp_effects_valid(const BtpState *s)
{
    const BtpEffectsState *v=&s->effects;
    if (v->count>24 || v->age>22 || v->pending>3 || v->stage>6 || (!v->count && (v->age || v->stage))) return 0;
    if (v->count && s->combat.phase!=BTP_COMBAT_ROUND) return 0;
    for (unsigned i=0;i<25;++i) {
        const BtpBattleText *t=i<24 ? &v->text[i] : &v->shown;
        if (t->active>1 || t->actor>=24 || t->target>=24 || t->actor_name>=10 || t->target_name>=10 ||
            t->weapon>33 || t->hit>1 || t->location>35 || t->criticals>8 || t->spectator>1) return 0;
        if (!t->active || (i<24 && i>=v->count)) {
            const uint8_t *p=(const uint8_t *)t;
            for (unsigned k=0;k<sizeof *t;++k) if (p[k]) return 0;
        }
    }
    /* The saved boundary after the final outtake has no remaining frames;
       the following logical tick performs the pending outcome transition. */
    if (v->pending && (s->combat.phase!=BTP_COMBAT_ROUND || (v->pending!=3 && !s->combat.shot.destroyed))) return 0;
    for (unsigned i=0;i<24;++i) {
        for (unsigned j=0;j<2;++j) if (v->outtakes[i][j]>=BTP_ANM_COUNT || (i>=v->count && v->outtakes[i][j])) return 0;
        const BtpCombatEffect *e=&v->shots[i];
        if (i<v->count) {
            if (e->actor>=s->combat.count || e->target>=s->combat.count || e->group>=18 || e->direction>7 || e->weapon>33 ||
                e->hit>1 || e->dead>1 || (!s->campaign.invasion && (e->x>127 || e->y>127 || e->tx>127 || e->ty>127)) ||
                (e->base!=0 && e->base!=146 && e->base!=254) ||
                (e->target_base!=0 && e->target_base!=16 && e->target_base!=146 && e->target_base!=254)) return 0;
            if (e->base!=(e->group>=4 ? 254 : e->group&1u ? 146 : 0) || (e->dead && !e->hit)) return 0;
            if (e->weapon==33 && (e->group>1 || !e->dead || e->target_base!=254 || s->combat.unit[e->actor].infantry)) return 0;
        } else {
            const uint8_t *p=(const uint8_t *)e;
            for (unsigned j=0;j<sizeof *e;++j) if (p[j]) return 0;
        }
    }
    return 1;
}
