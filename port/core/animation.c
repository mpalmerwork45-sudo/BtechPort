#include "core/animation.h"
#include "core/game.h"
#include "core/audio.h"
#include "core/npc.h"
#include "data/project.h"
int btp_outtake_roll(BtpState *s,unsigned kind,unsigned flags)
{
    /* 0000:4900..494D, including the special non-forced kind-16 branch. */
    static const unsigned masks[3]={3,15,63};
    unsigned draw=btp_rng_next(s->npc.rng);
    return !(draw&masks[s->menu.outtakes]) || flags==2 || kind==0 || kind==2 || kind==6 || (kind>7 && kind!=16);
}

unsigned btp_terrain_frame(unsigned tile, unsigned phase)
{
    static const uint8_t animated[10]={87,88,89,90,91,105,106,107,111,113};
    for (unsigned i=0;i<10;++i) if (tile==animated[i]) return 1u+3u*i+phase%3u;
    return 0;
}
uint8_t btp_walk_first(unsigned direction)
{
    static const uint8_t first[8] = {8,4,4,4,0,12,12,12};
    return first[direction & 7u];
}
uint8_t btp_walk_next(uint8_t frame, unsigned before, unsigned direction)
{
    unsigned first = btp_walk_first(direction);
    return (uint8_t)(first + (before == direction && (frame & ~3u) == first ? (frame+1u)%4 : 0));
}
unsigned btp_player_direction(unsigned facing)
{
    return facing == BTP_UP ? 0u : facing == BTP_UP_RIGHT ? 1u :
        facing == BTP_RIGHT ? 2u : facing == BTP_DOWN_RIGHT ? 3u :
        facing == BTP_DOWN_LEFT ? 5u : facing == BTP_LEFT ? 6u : facing == BTP_UP_LEFT ? 7u : 4u;
}
int btp_cutscene_begin(BtpState *s, const BtpResources *r, unsigned kind, unsigned active)
{
    int cinema=s && active==1 && s->mode==BTP_BUILDING && s->campaign.building==16 && kind<10;
    int invasion=s && active==4 && kind==2 && s->campaign.invasion && s->late.invasion_popup==3;
    int yard=s && kind==0 && s->yard.active && (active==5 || active==6 || active==7);
    if (!s || !r || s->cutscene.active || kind>=BTP_ANM_COUNT ||
        (active==1 && kind>=10 && kind<=14 && (!s->cache.active || s->mode!=BTP_BUILDING || s->campaign.building!=25)) ||
        (!cinema && !invasion && !yard && active!=3 && ((kind != 0 && kind != 6 && kind != 8 && (kind<9 || kind>14)) || active != (kind ? 1u : 2u))) || !r->animations[kind].count ||
        ((kind==0 || kind==8) && r->animations[kind].count != (kind ? 3u : 18u))) return 0;
    s->cutscene = (BtpCutsceneState){.active=(uint8_t)active,.kind=(uint8_t)kind,
        /* 0000:4A3D adds 50 retraces for every film except the repeating
           dream. This includes repairs, invasion and the cache ending.
           Failed yard startup uses its own truncated 09B8 routine. */
        .remaining=(uint16_t)(r->animations[kind].units[0]+(kind!=8 && active!=7 ? 50u : 0u))};
    if (!s->cutscene.remaining) s->cutscene.remaining=1;
    return 1;
}
int btp_cutscene_tick(BtpState *s, const BtpResources *r)
{
    BtpCutsceneState *c = &s->cutscene;
    if (!c->active || c->kind >= BTP_ANM_COUNT) return 0;
    const BtpAnm *a = &r->animations[c->kind];
    /* 32ms logical ticks at VGA's 70Hz; preserve fractional retraces in saves.
       Decode CPU cost and host presentation remain explicitly approximate. */
    unsigned scaled = c->refresh_fraction+2240u;
    unsigned units = scaled/1000u; c->refresh_fraction = (uint16_t)(scaled%1000u);
    for (unsigned budget = 0; budget < 256; ++budget) {
        if (units < c->remaining) { c->remaining = (uint16_t)(c->remaining-units); return 0; }
        units -= c->remaining;
        if (c->hold) {
            if (!c->kind && s->audio.sound_count) { c->remaining=1;return 0; }
            s->cutscene = (BtpCutsceneState){0}; return 1;
        }
        /* 09B8:16B2's failed-start routine plays O0 only while the next
           sequence letter is below 'I', then uses sound 14 and a final pause. */
        if ((unsigned)c->step+1u < (c->active==7 ? 8u : a->count)) ++c->step;
        else if (c->kind == 8 && c->cycle < 6) { ++c->cycle; c->step = 0; }
        /* 0000:4A6E suppresses the startup sound and final pause when the
           caller supplied a nonzero flag, as the cinema does. */
        else if (c->active==2 || c->active==3 || c->active>=5) {
            c->hold = 1;c->remaining = 60;
            if (!c->kind) btp_audio_effect(s,c->active==7 ? 14u : 12u);
            continue;
        }
        else { s->cutscene = (BtpCutsceneState){0}; return 1; }
        c->remaining = a->units[c->step] ? a->units[c->step] : 1;
    }
    return 0;
}
static int cutscene_valid(const BtpState *s,int edited)
{
    const BtpCutsceneState *c = &s->cutscene;
    if (!c->active) return !c->kind && !c->step && !c->cycle && !c->hold && !c->remaining && !c->refresh_fraction &&
        s->script.status != BTP_SCRIPT_ANIMATION;
    if (!c->remaining || c->refresh_fraction >= 1000 || (c->active!=3 && !s->checkpoint_valid) || c->hold > 1) return 0;
    if (c->active==4) return c->kind==2 && c->step<31 && !c->cycle && !c->hold && c->remaining<=16384 &&
        s->mode==BTP_MISSION && s->campaign.invasion && s->late.invasion_popup==3 && s->combat.phase==BTP_COMBAT_STORY;
    if (c->active>=5 && c->active<=7) return !c->kind && c->step<(c->active==7 ? 8u : 18u) && !c->cycle && c->remaining<=16384 &&
        s->mode==BTP_YARD && s->yard.active && s->script.status==BTP_SCRIPT_NATIVE &&
        (s->script.native_action==40 || s->script.native_action==35);
    if (c->active==3) return c->kind>0 && c->kind<BTP_ANM_COUNT && c->step<BTP_ANM_FRAMES && !c->cycle &&
        c->remaining<=16384 && s->combat.phase==BTP_COMBAT_ROUND && (s->mode==BTP_MISSION || s->mode==BTP_ENCOUNTER);
    if (c->active==1 && s->campaign.building==16) return c->kind<10 && c->step<BTP_ANM_FRAMES &&
        (c->kind==8 ? c->cycle<7 : !c->cycle) && !c->hold && c->remaining<=16384 &&
        s->mode==BTP_BUILDING && s->script.status==BTP_SCRIPT_ANIMATION &&
        s->script.animation_kind==c->kind && (s->script.animation_flags==1 || s->script.animation_flags==2);
    if (c->active==1 && c->kind==6) return c->step<31 && !c->cycle && !c->hold && c->remaining<=(edited ? 16384u : !c->step ? 54u : 4u) &&
        s->mode==BTP_BUILDING && (s->campaign.building==5 || s->campaign.building==9 || s->campaign.building==11 || s->campaign.building==13) &&
        s->script.status==BTP_SCRIPT_ANIMATION && s->script.animation_kind==6 && s->script.animation_flags==1;
    if (c->active==1 && c->kind==9) return c->step<12 && !c->cycle && !c->hold && c->remaining<=(edited ? 16384u : !c->step ? 57u : 7u) &&
        s->mode==BTP_BUILDING && !s->entry_slot && s->campaign.invasion &&
        s->script.status==BTP_SCRIPT_ANIMATION && s->script.animation_kind==9 && s->script.animation_flags==1;
    if (c->active==1 && c->kind>=10 && c->kind<=14) return c->step<BTP_ANM_FRAMES && !c->cycle && !c->hold && c->remaining<=16384 &&
        s->cache.active && s->campaign.building==25 && s->mode==BTP_BUILDING && s->script.status==BTP_SCRIPT_ANIMATION &&
        s->script.animation_kind==c->kind && s->script.animation_flags==1;
    if (c->active == 1) return c->kind == 8 && c->step < 3 && c->cycle < 7 && !c->hold && c->remaining <= (edited ? 16384u : 7u) &&
        s->mode == BTP_BUILDING && s->entry_slot == 6 && s->script.status == BTP_SCRIPT_ANIMATION &&
        s->script.animation_kind == 8 && s->script.animation_flags == 1;
    if (c->active == 2) return !c->kind && c->step < 18 && !c->cycle &&
        c->remaining <= (edited && !c->hold ? 16384u : c->hold ? 60u : !c->step ? 55u : 5u) && (!c->hold || c->step == 17) &&
        s->mode == BTP_MISSION && s->script.status == BTP_SCRIPT_NATIVE && s->script.native_action == 1;
    return 0;
}
int btp_cutscene_valid(const BtpState *s) { return cutscene_valid(s,s->project!=0); }
int btp_cutscene_valid_resources(const BtpState *s,const BtpResources *r)
{
    int edited=r->project && s->cutscene.kind<22 && r->project->chi_animations[s->cutscene.kind];
    if (edited && s->cutscene.active && s->cutscene.step>=r->animations[s->cutscene.kind].count) return 0;
    return cutscene_valid(s,edited);
}
