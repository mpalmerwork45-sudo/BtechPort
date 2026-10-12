#include "core/animation.h"
#include "core/game.h"

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
    if (!s || !r || s->cutscene.active || (kind != 0 && kind != 6 && kind != 8 && kind != 9) ||
        active != (kind ? 1u : 2u) || !r->animations[kind].count ||
        ((kind==0 || kind==8) && r->animations[kind].count != (kind ? 3u : 18u))) return 0;
    s->cutscene = (BtpCutsceneState){.active=(uint8_t)active,.kind=(uint8_t)kind,
        .remaining=(uint16_t)(r->animations[kind].units[0]+(kind ? 0u : 50u))};
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
        if (c->hold) { s->cutscene = (BtpCutsceneState){0}; return 1; }
        if ((unsigned)c->step+1u < a->count) ++c->step;
        else if (c->kind == 8 && c->cycle < 6) { ++c->cycle; c->step = 0; }
        else if (!c->kind) { c->hold = 1; c->remaining = 60; continue; }
        else { s->cutscene = (BtpCutsceneState){0}; return 1; }
        c->remaining = a->units[c->step] ? a->units[c->step] : 1;
    }
    return 0;
}
int btp_cutscene_valid(const BtpState *s)
{
    const BtpCutsceneState *c = &s->cutscene;
    if (!c->active) return !c->kind && !c->step && !c->cycle && !c->hold && !c->remaining && !c->refresh_fraction &&
        s->script.status != BTP_SCRIPT_ANIMATION;
    if (!c->remaining || c->refresh_fraction >= 1000 || !s->checkpoint_valid || c->hold > 1) return 0;
    if (c->active==1 && c->kind==6) return c->step<31 && !c->cycle && !c->hold && c->remaining<=4 &&
        s->mode==BTP_BUILDING && (s->campaign.building==5 || s->campaign.building==11) &&
        s->script.status==BTP_SCRIPT_ANIMATION && s->script.animation_kind==6 && s->script.animation_flags==1;
    if (c->active==1 && c->kind==9) return c->step<12 && !c->cycle && !c->hold && c->remaining<=7 &&
        s->mode==BTP_BUILDING && !s->entry_slot && s->campaign.invasion &&
        s->script.status==BTP_SCRIPT_ANIMATION && s->script.animation_kind==9 && s->script.animation_flags==1;
    if (c->active == 1) return c->kind == 8 && c->step < 3 && c->cycle < 7 && !c->hold && c->remaining <= 7 &&
        s->mode == BTP_BUILDING && s->entry_slot == 6 && s->script.status == BTP_SCRIPT_ANIMATION &&
        s->script.animation_kind == 8 && s->script.animation_flags == 1;
    if (c->active == 2) return !c->kind && c->step < 18 && !c->cycle &&
        c->remaining <= (c->hold ? 60u : !c->step ? 55u : 5u) && (!c->hold || c->step == 17) &&
        s->mode == BTP_MISSION && s->script.status == BTP_SCRIPT_NATIVE && s->script.native_action == 1;
    return 0;
}
