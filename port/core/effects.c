#include "core/battle_mission.h"
#include "core/effects.h"
#include "core/art_actions.h"
#include "core/audio.h"
#include "core/animation.h"
#include "core/combat.h"
#include "core/world.h"
#include <stdlib.h>
#include <string.h>
_Static_assert(sizeof(BtpCombatEffect)==13,"Effect encoding contains byte fields only");
_Static_assert(sizeof(BtpBattleText)==13,"Battle text encoding contains byte fields only");
_Static_assert(sizeof(BtpQuietReport)==18,"Quiet header encoding contains byte fields only");
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
        c->shot.criticals,(uint8_t)(s->campaign.encounter==4 && s->yard.rental && !s->story_flags[35] && btp_combat_id(c,target)==13),c->shot.destroyed,0,0};
}
void btp_effects_begin_round(BtpState *s)
{
    s->effects.shown=(BtpBattleText){0};s->effects.quiet=(BtpQuietReport){0};
    if (s->combat.messages) return;
    /* Quiet retirement appends to the command header's existing cursor.
       Keep its original name/model before a casualty clears record[0]. */
    unsigned active=s->combat.active_unit;
    BtpQuietReport *q=&s->effects.quiet;q->active=1;q->name=(uint8_t)name_id(s,active);
    if (!s->combat.unit[active].infantry) memcpy(q->mech,s->combat.unit[active].record,15);
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
int btp_combat_visible(int x,int y,int infantry,int focus_x,int focus_y)
{
    /* 0000:0E4B admits humans by their anchor, and mechs across a two-cell
       wider left/bottom margin. This flag also gates beam sound playback. */
    int dx=x-focus_x,dy=y-focus_y;
    return dx>=(infantry ? -13 : -15) && dx<=13 && dy>=-12 && dy<=(infantry ? 12 : 14);
}
static void effect_focus(const BtpState *s,int *x,int *y)
{
    const BtpCombatState *c=&s->combat;
    const BtpCombatUnit *focus=&c->unit[c->active_unit];
    const BtpCombatEffect *death=btp_effects_death(s,c->active_unit);
    *x=death ? death->tx : focus->x;*y=death ? death->ty : focus->y;
}
static int visible(const BtpCombatEffect *e,const BtpState *s)
{
    int x,y;effect_focus(s,&x,&y);
    return btp_combat_visible(e->x,e->y,e->base==254,x,y) ||
        btp_combat_visible(e->tx,e->ty,e->target_base==254,x,y);
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
unsigned btp_effects_trail_kind(unsigned w)
{
    return w==10 || w==11 || (w>=25 && w<=31) ? 1u :
        w==12 || w==13 ? 2u : w>=15 && w<=18 ? 3u : 0u;
}
unsigned btp_effects_beam_color(const BtpCombatEffect *e,unsigned actor_id)
{
    /* VGA branches at 12E8:15D1/1608: personal energy weapons are yellow/
       green, vehicle lasers red/magenta. These are original palette indices. */
    return btp_effects_trail_kind(e->weapon)==2 ? actor_id>=16 ? 10u : 14u : actor_id>=12 ? 5u : 12u;
}
void btp_effects_trail(const BtpCombatEffect *e,const BtpCombatData *d,int cx,int cy,BtpEffectTrail *trail)
{
    *trail=(BtpEffectTrail){.kind=btp_effects_trail_kind(e->weapon)};
    if (!trail->kind || e->direction>7) return;
    /* 0E31:1DF8 / 12E8:16A8 use eight-pixel world anchors, independently
       of the sprite's top-left corner. Beams offset their muzzle by family;
       missiles start at the anchor and advance four pixels per draw. */
    int x=208+8*((int)e->x-cx),y=96+8*((int)e->y-cy);
    int tx=208+8*((int)e->tx-cx),ty=96+8*((int)e->ty-cy)-(e->target_base==254 ? 0 : 8);
    int stride=trail->kind==1 ? 4 : 1;
    if (stride==1) {
        unsigned family=e->base==254 ? 2u : e->base==146 ? 1u : 0u;
        x+=d->muzzle[family][0][e->direction];y+=d->muzzle[family][1][e->direction];
        tx+=3;ty+=3;
    }
    int dx=abs(tx-x),dy=abs(ty-y);
    if (dx<=8 && dy<=8) return; /* Original close-range branch draws no trail. */
    int sx=(tx>x)-(tx<x),sy=(ty>y)-(ty<y),major=dx>dy ? dx : dy;
    int minor=dx>dy ? dy : dx,error=major/2;
    /* Independent integer line rasterization. Keeping the full offscreen
       ordinal preserves the original missile program phase when it enters
       the viewport. Only visible samples consume native presentation ticks. */
    for (unsigned ordinal=0;ordinal<2048 && (x!=tx || y!=ty);++ordinal) {
        if (x>=104 && x<320 && y>=0 && y<200 && trail->count<BTP_EFFECT_TRAIL_POINTS) {
            unsigned sprite=trail->kind==1 ? 104u+d->missile[e->direction][ordinal%6u] : 0;
            trail->points[trail->count++]=(BtpEffectPoint){(int16_t)x,(int16_t)y,(uint16_t)sprite};
        }
        if (dx>dy) { if (x!=tx) x+=sx*stride; }
        else if (y!=ty) y+=sy*stride;
        error-=minor;
        if (error<0) {
            if (dx>dy) { if (y!=ty) y+=sy*stride; }
            else if (x!=tx) x+=sx*stride;
            error+=major;
        }
    }
}
int btp_effects_pose(const BtpState *s,const BtpCombatData *d)
{
    const BtpEffectsState *v=&s->effects;
    if (!s->combat.graphics || !v->count || v->shots[0].weapon==33 || v->stage==BTP_EFFECT_PENDING) return -1;
    const BtpCombatEffect *e=&v->shots[0];unsigned n=d->poses[e->group][e->direction][0];
    if (!n) return -1;
    if (v->stage>=BTP_EFFECT_POSES) {
        unsigned frame=v->stage==BTP_EFFECT_POSES ? (unsigned)v->age*224u/500u : n-1;
        return (int)(frame<n ? frame : n-1);
    }
    return v->stage>=BTP_EFFECT_ATTACK && v->age/2u<n ? (int)(v->age/2u) : -1;
}
int btp_effects_reaction(const BtpState *s)
{
    if (!s->effects.count) return 0;
    const BtpCombatEffect *e=&s->effects.shots[0];
    return e->hit && e->target_base==254 &&
        (s->effects.stage<BTP_EFFECT_POSES || btp_effects_trail_kind(e->weapon)!=1);
}
const BtpCombatEffect *btp_effects_pending_death(const BtpState *s,unsigned target)
{
    /* Numeric attacks finish the entire microstep before presentation. Keep
       a destroyed unit's captured sprite/position until its own death event,
       rather than exposing a later attack's wreck during an earlier shot. The
       existing saved effect record holds everything needed for restoration. */
    for (unsigned i=0;i<s->effects.count;++i) {
        const BtpCombatEffect *e=&s->effects.shots[i];
        if (e->dead && e->target==target && (i || (s->effects.stage>=BTP_EFFECT_POSES ?
            s->effects.stage!=BTP_EFFECT_RETIRE_SOUND : s->effects.stage<BTP_EFFECT_DEATH_SOUND))) return e;
    }
    return NULL;
}
void btp_effects_shot(BtpState *s,unsigned actor,unsigned target,unsigned weapon)
{
    BtpCombatState *c=&s->combat;BtpEffectsState *v=&s->effects;
    if (v->count>=24) return; /* At most one shot per unit in a microstep. */
    if (!v->count) { v->stage=BTP_EFFECT_PENDING;v->age=0; }
    const BtpCombatUnit *a=&c->unit[actor],*t=&c->unit[target];
    unsigned friends=c->friends ? c->friends : 1u;
    unsigned alt=!a->infantry && btp_mech_record_sprite(a->record,s->battle_mission.active ? btp_battle_side(s,NULL,actor)==BTP_SIDE_HOSTILE : actor>=friends)!=0;
    unsigned group=a->infantry ? 4u+weapon : (weapon==32 ? 2u : 0u)+alt;
    unsigned direction=btp_combat_direction(a->x,a->y,t->x,t->y);
    if (direction>7) direction=a->direction;
    v->text[v->count]=report(s,actor,target,weapon);
    v->shots[v->count++]=(BtpCombatEffect){(uint8_t)actor,(uint8_t)target,(uint8_t)group,
        (uint8_t)direction,(uint8_t)weapon,c->shot.hit,c->shot.destroyed,a->x,a->y,t->x,t->y,
        (uint8_t)(a->infantry ? 254 : alt ? 146 : 0),
        (uint8_t)(t->infantry ? 254 : t->record[0]=='s' ? 16 : btp_mech_record_sprite(t->record,s->battle_mission.active ? btp_battle_side(s,NULL,target)==BTP_SIDE_HOSTILE : target>=friends))};
}
void btp_effects_crush(BtpState *s,unsigned actor,unsigned target)
{
    /* 0E31:19FC..1A93 plays effect 18 before marking a trampled soldier.
       Weapon 33 is the saved presentation discriminator, not a gun order. */
    BtpCombatState *c=&s->combat;BtpEffectsState *v=&s->effects;
    if (v->count>=24) return;
    if (!v->count) { v->stage=BTP_EFFECT_PENDING;v->age=0; }
    const BtpCombatUnit *a=&c->unit[actor],*t=&c->unit[target];
    unsigned alt=btp_mech_record_sprite(a->record,s->battle_mission.active ? btp_battle_side(s,NULL,actor)==BTP_SIDE_HOSTILE : actor>=(c->friends ? c->friends : 1u))!=0;
    v->text[v->count]=report(s,actor,target,33);
    v->text[v->count].hit=1;v->text[v->count].location=v->text[v->count].criticals=0;
    v->text[v->count].dead=1;
    v->shots[v->count++]=(BtpCombatEffect){(uint8_t)actor,(uint8_t)target,(uint8_t)alt,
        a->direction,33,1,1,a->x,a->y,t->x,t->y,(uint8_t)(alt ? 146 : 0),254};
}
static void redraw_marks(BtpState *s)
{
    int x,y;effect_focus(s,&x,&y);
    int ox=s->campaign.encounter || s->campaign.invasion ? s->campaign.battle_x : 1536;
    int oy=s->campaign.encounter || s->campaign.invasion ? s->campaign.battle_y : 1536;
    btp_world_animate_marks(s,ox+x,oy+y);
}
static void complete_effect(BtpState *s)
{
    BtpEffectsState *v=&s->effects;const BtpCombatEffect *e=&v->shots[0];
    for (unsigned i=0;i<2;++i) if (v->outtakes[0][i] && s->presentation.count<24)
        s->presentation.kinds[s->presentation.count++]=v->outtakes[0][i];
    unsigned legacy=v->stage==BTP_EFFECT_LEGACY,modern=v->stage>=BTP_EFFECT_POSES;
    if (modern && s->combat.graphics && !e->hit) redraw_marks(s); /* 12E8:1ADD miss cleanup. */
    /* 12E8:0D76 pauses after each attack. Enemy crushing has a timed
       pause but skips speed five's key wait (0E31:1A21). */
    s->combat.delay=(uint8_t)(s->menu.speed==5 ? e->weapon!=33 : btp_combat_delay_ticks(s->menu.speed));
    if (v->quiet.active && !s->combat.messages && v->text[0].dead && v->text[0].target<4 && v->quiet.ejections<4)
        ++v->quiet.ejections;
    v->shown=v->text[0];v->age=0;--v->count;
    memmove(v->shots,v->shots+1,v->count*sizeof v->shots[0]);
    memset(&v->shots[v->count],0,sizeof v->shots[0]);
    memmove(v->outtakes,v->outtakes+1,v->count*sizeof v->outtakes[0]);
    memset(v->outtakes[v->count],0,sizeof v->outtakes[0]);
    memmove(v->text,v->text+1,v->count*sizeof v->text[0]);
    memset(&v->text[v->count],0,sizeof v->text[0]);
    v->stage=(uint8_t)(!v->count ? BTP_EFFECT_START : modern ? BTP_EFFECT_PENDING :
        legacy ? BTP_EFFECT_LEGACY : BTP_EFFECT_START);
}
/* v40-v43 held presentations retain their stage/age interpretation. A new
   queue uses the verified sequence below; old queued sounds never restart. */
static void legacy_tick(BtpState *s,const BtpResources *r)
{
    BtpEffectsState *v=&s->effects;
    if (!v->count) return;
    const BtpCombatEffect *e=&v->shots[0];
    if (v->stage==BTP_EFFECT_START) {
        if (s->audio.sound_count) return;
        if (!s->combat.graphics && e->weapon!=33) {
            /* 12E8:12DF jumps directly to casualty handling when graphics
               are disabled. Hidden firing/impact poses consume no time. */
            v->age=(uint8_t)btp_effects_length(e,&r->combat);v->stage=BTP_EFFECT_IMPACT;
        } else {
            if (e->weapon==33) btp_audio_effect(s,18);
            else btp_audio_effect(s,btp_action_sound(r,s,e->actor,BTP_ANIM_FIRE,btp_effects_fire_sound(e->weapon,visible(e,s))));
            v->stage=BTP_EFFECT_FIRE_SOUND;return;
        }
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
    } else if ((v->stage==BTP_EFFECT_IMPACT || v->stage==BTP_EFFECT_LEGACY) &&
        v->age<btp_effects_length(e,&r->combat)) ++v->age;
    if (e->weapon!=33 && v->age<btp_effects_length(e,&r->combat)) return;
    if (e->dead && e->target_base!=254 && v->stage!=BTP_EFFECT_DEATH_SOUND && v->stage!=BTP_EFFECT_LEGACY) {
        /* 12E8:1C76 plays sound 8 for a wreck. The rented arena target's
           branch uses sound 7 before its two alarm messages instead. Wait
           for this clip before any outtake or outcome can advance. Humans
           take 1B7F's corpse branch and skip the wreck/sound-8 branch. */
        btp_audio_effect(s,btp_action_sound(r,s,e->target,BTP_ANIM_DESTRUCTION,e->target_base==254 ? 0u : s->campaign.encounter==4 && btp_combat_id(&s->combat,e->target)==13 ? 7u : 8u));
        v->stage=BTP_EFFECT_DEATH_SOUND;return;
    }
    complete_effect(s);
}
static void strike_sound(BtpState *s,const BtpResources *r)
{
    if (s->effects.shots[0].hit) btp_audio_effect(s,btp_action_sound(r,s,s->effects.shots[0].target,BTP_ANIM_DAMAGE,4));
    s->effects.stage=BTP_EFFECT_STRIKE_SOUND;s->effects.age=0;
}
void btp_effects_tick(BtpState *s,const BtpResources *r)
{
    BtpEffectsState *v=&s->effects;
    if (!v->count || s->audio.sound_count) return;
    if (v->stage<BTP_EFFECT_POSES) { legacy_tick(s,r);return; }
    const BtpCombatEffect *e=&v->shots[0];
    /* Zero-duration transitions may share a host tick. Visible poses, missile
       samples, speaker clips and the final impact hold remain distinct. */
    for (unsigned transitions=0;transitions<6;++transitions) {
        if (s->audio.sound_count) return;
        switch (v->stage) {
        case BTP_EFFECT_PENDING:
            v->stage=BTP_EFFECT_POSES;
            if (s->combat.graphics && e->weapon!=33) {
                int x,y;effect_focus(s,&x,&y);
                if (btp_combat_visible(e->x,e->y,e->base==254,x,y)) { redraw_marks(s);return; }
            }
            break;
        case BTP_EFFECT_POSES: {
            if (e->weapon==33) {
                btp_audio_effect(s,18);v->stage=BTP_EFFECT_SHOT_SOUND;return;
            }
            if (!s->combat.graphics) { v->stage=BTP_EFFECT_RETIRE_SOUND;break; }
            unsigned poses=r->combat.poses[e->group][e->direction][0];
            /* 12E8:1503 requests five retraces after each firing pose.
               Accumulate the conversion so rounding does not grow per pose. */
            int x,y;effect_focus(s,&x,&y);
            int actor_visible=btp_combat_visible(e->x,e->y,e->base==254,x,y);
            unsigned previous=(unsigned)v->age*224u/500u;
            unsigned duration=btp_action_duration(r,s,e->actor,BTP_ANIM_FIRE);
            if (actor_visible && ++v->age<(duration ? duration : (poses*500u+223u)/224u)) {
                if ((unsigned)v->age*224u/500u!=previous) redraw_marks(s);
                return;
            }
            v->age=0;v->stage=BTP_EFFECT_SHOT_SOUND;
            if (btp_effects_trail_kind(e->weapon)<2)
                btp_audio_effect(s,btp_action_sound(r,s,e->actor,BTP_ANIM_FIRE,btp_effects_fire_sound(e->weapon,visible(e,s))));
            break;
        }
        case BTP_EFFECT_SHOT_SOUND:
            if (e->weapon==33) { v->stage=BTP_EFFECT_RETIRE_SOUND;break; }
            if (btp_effects_trail_kind(e->weapon)) {
                BtpEffectTrail trail;int x,y;effect_focus(s,&x,&y);
                btp_effects_trail(e,&r->combat,x,y,&trail);
                v->stage=BTP_EFFECT_FLIGHT;v->age=0;
                if (trail.count) { if (trail.kind==1) redraw_marks(s);return; }
                if (trail.kind>=2 && visible(e,s)) {
                    btp_audio_effect(s,btp_action_sound(r,s,e->actor,BTP_ANIM_FIRE,btp_effects_fire_sound(e->weapon,1)));v->stage=BTP_EFFECT_BEAM_SOUND;break;
                }
            }
            strike_sound(s,r);break;
        case BTP_EFFECT_FLIGHT: {
            BtpEffectTrail trail;int x,y;effect_focus(s,&x,&y);
            btp_effects_trail(e,&r->combat,x,y,&trail);
            if (trail.kind>=2) {
                btp_audio_effect(s,btp_action_sound(r,s,e->actor,BTP_ANIM_FIRE,btp_effects_fire_sound(e->weapon,visible(e,s))));
                v->stage=BTP_EFFECT_BEAM_SOUND;v->age=0;break;
            }
            if (++v->age<trail.count) { redraw_marks(s);return; }
            strike_sound(s,r);break;
        }
        case BTP_EFFECT_BEAM_SOUND: strike_sound(s,r);break;
        case BTP_EFFECT_STRIKE_SOUND:
            if (e->hit && e->weapon>=7) {
                int x,y;effect_focus(s,&x,&y);
                if (btp_combat_visible(e->tx,e->ty,e->target_base==254,x,y)) {
                    /* Original 1A78 draws all three impacts without waits,
                       then 1ABE holds the last for five retraces. At the host
                       display boundary only that final frame is retained. */
                    v->stage=BTP_EFFECT_IMPACT_HOLD;v->age=0;
                    redraw_marks(s);redraw_marks(s);redraw_marks(s);return;
                }
            }
            v->stage=BTP_EFFECT_RETIRE_SOUND;break;
        case BTP_EFFECT_IMPACT_HOLD:
            if (++v->age<(btp_action_duration(r,s,e->target,BTP_ANIM_DAMAGE) ? btp_action_duration(r,s,e->target,BTP_ANIM_DAMAGE) : 3u)) return;
            v->stage=BTP_EFFECT_RETIRE_SOUND;v->age=0;break;
        case BTP_EFFECT_RETIRE_SOUND:
            if (e->dead && ++v->age<btp_action_duration(r,s,e->target,BTP_ANIM_DESTRUCTION)) return;
            complete_effect(s);return;
        default:return;
        }
        /* A dead vehicle is retained until its own sound, rather than
           displaying later numeric damage during another queued attack. */
        if (v->stage==BTP_EFFECT_RETIRE_SOUND && e->dead && (e->target_base!=254 || btp_action_sound(r,s,e->target,BTP_ANIM_DESTRUCTION,0))) {
            btp_audio_effect(s,btp_action_sound(r,s,e->target,BTP_ANIM_DESTRUCTION,e->target_base==254 ? 0u : s->campaign.encounter==4 && btp_combat_id(&s->combat,e->target)==13 ? 7u : 8u));
            v->age=0;return;
        }
    }
}
int btp_effects_valid(const BtpState *s)
{
    const BtpEffectsState *v=&s->effects;
    const BtpQuietReport *q=&v->quiet;
    if (q->active>1 || q->name>=10 || q->ejections>4) return 0;
    if (!q->active) {
        const uint8_t *p=(const uint8_t *)q;for (unsigned i=0;i<sizeof *q;++i) if (p[i]) return 0;
    }
    for (unsigned i=0;i<15;++i) if (q->mech[i] && (q->mech[i]<32 || q->mech[i]>126)) return 0;
    if (v->count>24 || v->pending>3 || v->stage>BTP_EFFECT_PENDING || (!v->count && (v->age || v->stage))) return 0;
    if (v->stage<BTP_EFFECT_POSES ? v->age>22 : v->stage==BTP_EFFECT_POSES ? 0 :
        v->stage==BTP_EFFECT_FLIGHT ? v->age>55 : (v->stage==BTP_EFFECT_IMPACT_HOLD || v->stage==BTP_EFFECT_RETIRE_SOUND) ? 0 : v->age!=0) return 0;
    if (v->count && s->combat.phase!=BTP_COMBAT_ROUND) return 0;
    for (unsigned i=0;i<25;++i) {
        const BtpBattleText *t=i<24 ? &v->text[i] : &v->shown;
        if (t->active>1 || t->actor>=24 || t->target>=24 || t->actor_name>=10 || t->target_name>=10 ||
            t->weapon>33 || t->hit>1 || t->location>35 || t->criticals>8 || t->spectator>1 || t->dead>1 || (t->dead && !t->hit) ||
            t->authored>1 || (!t->authored && t->content_weapon) || (t->authored && !s->project)) return 0;
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
