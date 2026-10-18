#include "core/art_actions.h"
#include "core/events.h"
#include "core/effects.h"
#include "data/project.h"
unsigned btp_unit_image(const BtpResources *r,const uint8_t m[125])
{
    if (!r->project || (m[124]!=192 && m[124]!=193)) return BTP_ART_NONE;
    const BtpDefinitions *d=&r->project->definitions;
    return m[123]<d->mech_count ? d->presentations[d->mechs[m[123]].presentation].graphic : BTP_ART_NONE;
}
unsigned btp_person_image(const BtpResources *r,unsigned person)
{
    const BtpAdventure *a=btp_adventure(r);
    return a && person<a->person_count ? a->people[person].graphic : BTP_ART_NONE;
}
unsigned btp_actor_image(const BtpResources *r,const BtpState *s,unsigned actor)
{
    if (actor>=s->combat.count) return BTP_ART_NONE;
    const BtpCombatUnit *u=&s->combat.unit[actor];
    if (!u->infantry) return btp_unit_image(r,u->record);
    const BtpAdventure *a=btp_adventure(r);if (!a) return BTP_ART_NONE;
    unsigned id=s->combat.ids[actor];
    if (id>=4 && id<12) return btp_person_image(r,s->event.people[id-4]);
    /* Enemy infantry identity is encounter ordinal, not the reusable actor
       identity byte (different templates may intentionally share it). */
    if (id>=16 && s->event.node<a->node_count && a->nodes[s->event.node].op==BTP_EVENT_BATTLE) {
        const BtpSceneBattle *b=&a->battles[a->nodes[s->event.node].argument];unsigned ordinal=16;
        for (unsigned i=0;i<b->count;++i) if (b->enemies[i].infantry && ordinal++==id)
            return btp_person_image(r,b->enemies[i].definition);
    }
    return BTP_ART_NONE;
}
unsigned btp_actor_action(const BtpState *s,unsigned actor,unsigned *elapsed)
{
    *elapsed=s->tick;
    if (s->effects.count && s->combat.graphics) {
        const BtpCombatEffect *e=&s->effects.shots[0];unsigned stage=s->effects.stage;
        if (actor==e->target && stage==BTP_EFFECT_RETIRE_SOUND && e->dead) {
            *elapsed=s->effects.age;return BTP_ANIM_DESTRUCTION;
        }
        if (actor==e->target && e->hit && stage==BTP_EFFECT_IMPACT_HOLD) {
            *elapsed=s->effects.age;return BTP_ANIM_DAMAGE;
        }
        if (actor==e->actor && stage>=BTP_EFFECT_POSES && stage!=BTP_EFFECT_PENDING) {
            *elapsed=stage==BTP_EFFECT_POSES ? s->effects.age : 255;return BTP_ANIM_FIRE;
        }
    }
    if (s->combat.phase==BTP_COMBAT_ROUND && !s->effects.count && s->combat.moved[actor])
        return s->combat.plans[actor].movement==2 ? BTP_ANIM_JUMP : BTP_ANIM_WALK;
    return BTP_ANIM_IDLE;
}
unsigned btp_action_duration(const BtpResources *r,const BtpState *s,unsigned actor,unsigned action)
{
    if (!r->project) return 0;
    const BtpArtTrack *t=btp_art_track(&r->project->graphics,btp_actor_image(r,s,actor),action);
    if (!t) return 0;
    unsigned d=t->directions==1 ? 0 : s->combat.unit[actor].direction&7u,n=0;
    for (unsigned i=0;i<t->count[d];++i) n+=t->ticks[d][i];
    return n;
}
unsigned btp_action_sound(const BtpResources *r,const BtpState *s,unsigned actor,unsigned action,unsigned fallback)
{
    if (!r->project) return fallback;
    const BtpArtTrack *t=btp_art_track(&r->project->graphics,btp_actor_image(r,s,actor),action);
    return t && t->sound ? t->sound : fallback;
}
