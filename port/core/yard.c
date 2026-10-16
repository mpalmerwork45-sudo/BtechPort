#include "data/unit_data.h"
#include "core/yard.h"
#include "core/party.h"
#include "core/animation.h"
#include "core/audio.h"
#include "core/npc.h"
#include "core/combat.h"
#include <string.h>
_Static_assert(sizeof(BtpYardState)+1<=BTP_STATE_BYTES-19305,"Yard/reply state exceeds the reserved save payload");
static void keep_party(BtpState *s,unsigned active)
{
    s->yard=(BtpYardState){.active=(uint8_t)active};
    for (unsigned i=0;i<8;++i) {
        s->yard.membership[i]=s->party.people[i][12];
        if (i) { s->yard.ids[i-1]=s->party.people[i][0];s->party.people[i][0]=255; }
    }
    for (unsigned i=0;i<4;++i) {
        s->yard.types[i]=s->party.mech_types[i];memcpy(s->yard.mechs[i],btp_party_mech(s,i),125);
    }
}
static void restore_party(BtpState *s)
{
    for (unsigned i=1;i<8;++i) s->party.people[i][0]=s->yard.ids[i-1];
    for (unsigned i=0;i<4;++i) {
        memcpy(btp_party_mech(s,i),s->yard.mechs[i],125);s->party.mech_types[i]=s->yard.types[i];
    }
    for (unsigned i=0;i<8;++i) s->party.people[i][12]=s->yard.membership[i];
}
static void combat_state(BtpState *s,unsigned event)
{
    BtpCombatState *c=&s->combat;
    *c=(BtpCombatState){.phase=BTP_COMBAT_CONTROL,.selected=1,.messages=2,.graphics=1,.movement=255,
        .kick_target=255,.enemy_movement=255,.friends=1,.count=1,.target_unit=1,.last_target=1};
    memset(c->orders,255,11);memset(c->enemy_orders,255,sizeof c->enemy_orders);memset(c->enemy_modes,255,sizeof c->enemy_modes);
    c->plans[0].movement=255;c->plans[0].kick=255;memset(c->plans[0].orders,255,11);
    s->campaign.encounter=(uint8_t)event;s->mode=BTP_ENCOUNTER;
    s->campaign.return_x=s->x_half;s->campaign.return_y=s->y_half;
}
void btp_yard_begin_guards(BtpState *s,const BtpResources *r)
{
    /* 07DC:0AA8 invokes 0D49(0,0x88): the original consumes two initial
       coordinate draws, then overrides the spawn with 0D10/7024. */
    combat_state(s,3);s->campaign.battle_x=1664;s->campaign.battle_y=896;
    BtpCombatState *c=&s->combat;c->ids[0]=4;c->unit[0].infantry=1;
    memcpy(c->unit[0].record,s->party.people[0],17);c->unit[0].x=(uint8_t)s->x_half;c->unit[0].y=(uint8_t)s->y_half;
    (void)btp_rng_next(s->npc.rng);(void)btp_rng_next(s->npc.rng);
    for (unsigned i=0;i<8;++i) {
        unsigned at=c->count++;BtpCombatUnit *u=&c->unit[at];u->infantry=1;u->record[12]=8;
        /* The original enemy person indices are 8..15. These deliberately
           index the latter half of the DS:1642/164E formations. */
        u->x=(uint8_t)(16u+r->combat.special_x[8+i]);u->y=(uint8_t)(36u+r->combat.special_y[8+i]);u->direction=6;
        c->ids[at]=(uint8_t)(16+i);c->plan_direction[at]=6;c->walk[at]=12;
        for (unsigned k=4;k<=9;++k) u->record[k]=(uint8_t)(btp_rng_next(s->npc.rng)&1u);
        u->record[1]=(uint8_t)btp_combat_dice(s->npc.rng);u->record[15]=(uint8_t)(10u*u->record[1]);
        u->record[11]=(uint8_t)(btp_rng_next(s->npc.rng)%14u);
    }
    s->yard.timer=0;s->yard.phase=BTP_YARD_WALK;
}
void btp_yard_finish_prison(BtpState *s,const BtpResources *r,int success)
{
    /* 09B8:152F restores the seven IDs and four vehicles, returns to
       0D00/7014, then copies the Stinger template into the first empty bay. */
    restore_party(s);s->party.people[0][12]=8;s->campaign.mounted=0;
    if (success) for (unsigned i=0;i<4;++i) if (btp_party_mech(s,i)[0]==255) {
        memcpy(btp_party_mech(s,i),btp_mech_template(&r->combat,BTP_MECH_ENCOUNTER,2),125);
        s->party.mech_types[i]=btp_party_mech(s,i)[0];s->campaign.owned=1;break;
    }
    if (!success) s->story_flags[40]=1;
    s->campaign.world_x=1664;s->campaign.world_y=916;s->x_half=0;s->y_half=20;
    s->script.position_x=0x0d00;s->script.position_y=0x7014;
    s->yard=(BtpYardState){0};s->campaign.encounter=0;
    s->combat=(BtpCombatState){0};s->effects=(BtpEffectsState){0};s->aftermath=(BtpAftermathState){0};
    s->mode=BTP_BUILDING;btp_script_native_return(&s->script,btp_state_bld(r,s),s->story_flags);
}
static void gate(BtpState *s,unsigned raw,unsigned tile)
{
    BtpYardState *v=&s->yard;unsigned index=raw-0x101du;
    unsigned x=(index/64u%8u)*8u+index%8u,y=index/512u*8u+index%64u/8u;
    for (unsigned i=0;i<v->gate_count;++i) if (v->gates[i][0]==x && v->gates[i][1]==y) { v->gates[i][2]=(uint8_t)tile;return; }
    if (v->gate_count<16) { uint8_t *g=v->gates[v->gate_count++];g[0]=(uint8_t)x;g[1]=(uint8_t)y;g[2]=(uint8_t)tile; }
}
static void force_fields(BtpState *s,int open)
{
    /* 09B8:137F/1441: the same three original raw-map strips, closed with
       animated field tiles or opened using the original per-cell RNG draws. */
    unsigned v=s->yard.variant;
    if (v==1) {
        gate(s,0x1c8f,open ? 67u : 111u);
        for (unsigned i=0;i<5;++i) gate(s,0x1c90+i,open ? 64u+(btp_rng_next(s->npc.rng)&3u) : 106u);
        gate(s,0x1ccd,open ? 66u : 112u);
    } else if (v==2) {
        gate(s,0x1a78,open ? 65u : 111u);
        for (unsigned i=0;i<4;++i) gate(s,0x1a79+i,open ? 64u+(btp_rng_next(s->npc.rng)&3u) : 106u);
        for (unsigned i=0;i<6;++i) gate(s,0x1ab5+i,open ? 64u+(btp_rng_next(s->npc.rng)&3u) : 106u);
        gate(s,0x1abb,open ? 66u : 112u);
    } else if (v==3) {
        gate(s,0x1ad9,open ? 64u : 113u);
        for (unsigned i=4;i<60;i+=8) gate(s,0x1c9d+i,open ? 64u+(btp_rng_next(s->npc.rng)&3u) : 107u);
        gate(s,0x1cd9,open ? 65u : 112u);
    }
}
static void arena_party(BtpState *s,const BtpResources *r,unsigned slot,int rental)
{
    keep_party(s,2);s->yard.slot=(uint8_t)slot;s->yard.rental=(uint8_t)rental;s->yard.phase=BTP_YARD_LOAN;
    uint8_t record[125];memcpy(record,rental ? btp_mech_template(&r->combat,BTP_MECH_LOAN,0) : btp_party_mech(s,slot),125);
    if (!rental) record[0]=s->party.mech_types[slot];
    memcpy(s->campaign.mech,record,125);s->campaign.mech[121]=0;s->campaign.mech[122]=255;
    s->campaign.owned=1;s->party.mech_types[0]=record[0];s->party.people[0][12]=0;s->campaign.mounted=1;
}
void btp_yard_begin_arena(BtpState *s,const BtpResources *r)
{
    /* A half-sector origin covers both the arena and the pursuing mechs'
       original west-side positions, without changing their world coordinates. */
    combat_state(s,4);s->campaign.battle_x=1216;s->campaign.battle_y=1024;
    BtpCombatState *c=&s->combat;memcpy(c->unit[0].record,s->campaign.mech,125);
    c->unit[0].x=107;c->unit[0].y=87;c->unit[0].direction=4;c->ids[0]=0;
    unsigned x=80u+(btp_rng_next(s->npc.rng)&3u);
    if (btp_rng_next(s->npc.rng)&1u) x=104u+(btp_rng_next(s->npc.rng)&3u);
    unsigned y=111u+(btp_rng_next(s->npc.rng)&3u),count=1;
    if (s->yard.rental) for (unsigned i=0;i<4;++i) if (s->yard.types[i]==255) count=2;
    unsigned kind=btp_combat_dice(s->npc.rng)-2u;
    if (s->yard.rental) kind=3u+(btp_rng_next(s->npc.rng)&3u);
    unsigned difficulty=s->story_flags[3]>6 ? 6u : s->story_flags[3];
    for (unsigned i=0;i<count;++i) {
        /* 07DC:0D49 replaces the second rental record from 27E8:05DE,
           then applies the normal difficulty reduction to that record. */
        unsigned at=c->count++;BtpCombatUnit *u=&c->unit[at];memcpy(u->record,i && s->yard.rental ? btp_mech_template(&r->combat,BTP_MECH_SPECTATOR,0) : btp_mech_template(&r->combat,BTP_MECH_ARENA,kind),125);
        for (unsigned k=17;k<=27;++k) u->record[k]=(uint8_t)(u->record[k]>r->combat.arena_reduction[difficulty] ? (unsigned)u->record[k]-r->combat.arena_reduction[difficulty] : 0u);
        if (difficulty>4) for (unsigned k=0;k<5;++k) { unsigned part=52u+(btp_rng_next(s->npc.rng)&31u);if (u->record[part]) u->record[part]|=128; }
        if (difficulty>5) { u->record[117]=btp_rng_next(s->npc.rng)&1u;u->record[119]=btp_rng_next(s->npc.rng)&1u;u->record[118]=btp_rng_next(s->npc.rng)&1u; }
        u->x=(uint8_t)(x+r->combat.special_x[i]);u->y=(uint8_t)(y+r->combat.special_y[i]);u->direction=6;c->ids[at]=(uint8_t)(12+i);c->walk[at]=12;c->plan_direction[at]=6;
        if (i && s->yard.rental) { u->x=70;u->y=102;u->direction=2;c->walk[at]=0; }
    }
    s->x_half=107;s->y_half=89;s->yard.phase=BTP_YARD_FIGHT;
}
int btp_yard_native(BtpState *s,const BtpResources *r)
{
    unsigned kind=btp_building_kind(r,s),action=s->script.native_action;
    if (kind==13 && action==40) {
        keep_party(s,1);
        for (unsigned i=0;i<4;++i) btp_party_mech(s,i)[0]=255;
        s->party.people[0][12]=8;s->campaign.mounted=0;
        s->campaign.world_x=1680;s->campaign.world_y=932;s->x_half=16;s->y_half=36;
        s->mode=BTP_YARD;return 1;
    }
    if (kind==10 && action==33) {
        arena_party(s,r,0,1);btp_script_native_return(&s->script,btp_state_bld(r,s),s->story_flags);return 1;
    }
    if (kind==10 && action==34) {
        if (!s->yard.active) s->yard=(BtpYardState){.active=2,.phase=BTP_YARD_OWN};
        s->mode=BTP_YARD;return 1;
    }
    if (kind==10 && action==35 && s->yard.active==2) {
        s->mode=BTP_YARD;s->yard.phase=BTP_YARD_BOOT;
        s->campaign.world_x=1323;s->campaign.world_y=1111;s->x_half=43;s->y_half=87;
        (void)btp_rng_next(s->npc.rng);(void)btp_cutscene_begin(s,r,0,6);return 1;
    }
    return 0;
}
void btp_yard_input(BtpState *s,const BtpResources *r,BtpAction a)
{
    BtpYardState *v=&s->yard;
    if (s->cutscene.active) { (void)btp_cutscene_tick(s,r);return; }
    if (s->audio.sound_count) return;
    if (v->phase==BTP_YARD_BOOT) { v->variant=btp_rng_next(s->npc.rng)&3u;force_fields(s,0);btp_yard_begin_arena(s,r);return; }
    if (v->phase==BTP_YARD_OWN) {
        if (a==BTP_DOWN || a==BTP_RIGHT) v->selected=(uint8_t)((v->selected+1u)%4u);
        if (a==BTP_UP || a==BTP_LEFT) v->selected=(uint8_t)((v->selected+3u)%4u);
        if ((a==BTP_ACCEPT || a==BTP_OPEN_MENU) && s->party.mech_types[v->selected]!=255) {
            unsigned slot=v->selected;arena_party(s,r,slot,0);s->mode=BTP_BUILDING;
            btp_script_native_return(&s->script,btp_state_bld(r,s),s->story_flags);
        }
        return;
    }
    if (v->phase==BTP_YARD_CLIMB) {
        if (a==BTP_ACCEPT || a==BTP_OPEN_MENU) v->phase=BTP_YARD_SWITCH;
        return;
    }
    if (v->phase==BTP_YARD_SWITCH) {
        if (a==BTP_ACCEPT || a==BTP_OPEN_MENU) {
            /* 07DC:0BA6 counts distinct boarding attempts. The third starts;
               previous choices cannot be used to increment the counter again. */
            ++v->attempts;v->phase=(uint8_t)(v->attempts==3 ? BTP_YARD_FOUND : BTP_YARD_FAIL);
            if (v->attempts==3) (void)btp_rng_next(s->npc.rng);
            (void)btp_cutscene_begin(s,r,0,v->attempts==3 ? 5u : 7u);
        }
        return;
    }
    if (v->phase==BTP_YARD_FAIL) { if (a==BTP_ACCEPT || a==BTP_OPEN_MENU) v->phase=BTP_YARD_WALK;return; }
    if (v->phase==BTP_YARD_FOUND) { if (a==BTP_ACCEPT || a==BTP_OPEN_MENU) btp_yard_finish_prison(s,r,1);return; }
    if (a==BTP_IDLE && v->idle) { --v->idle;return; }
    v->idle=10;
    if (btp_action_moves(a)) {
        const BtpMap *m=btp_active_map(r,s);unsigned before=btp_player_direction(s->facing);
        int x=(int)s->x_half+btp_action_dx(a),y=(int)s->y_half+btp_action_dy(a);
        s->facing=(uint8_t)a;s->player_walk=btp_walk_next(s->player_walk,before,btp_player_direction((unsigned)a));
        if (x>=0 && y>=0 && x<2*m->width && y<2*m->height && btp_map_tile(m,(x+1)/2,y/2)<85) {
            s->x_half=(uint16_t)x;s->y_half=(uint16_t)y;s->blocked=0;
            s->campaign.world_x=(uint16_t)(1664+x);s->campaign.world_y=(uint16_t)(896+y);
        } else s->blocked=BTP_WALL;
    }
    /* 07DC:0AE6 triggers a search at 0D14/18/1C/20, row 702D. */
    if (s->y_half==45 && s->x_half>=20 && s->x_half<=32 && !((s->x_half-20u)&3u)) {
        unsigned mech=(s->x_half-20u)/4u;
        if (!(v->checked&(1u<<mech))) { v->checked|=(uint8_t)(1u<<mech);v->slot=(uint8_t)mech;v->phase=BTP_YARD_CLIMB; }
    }
    if (++v->timer==81) {
        btp_yard_begin_guards(s,r);
    }
}
void btp_yard_result(BtpState *s,const BtpResources *r)
{
    if (s->campaign.encounter==4 && !s->combat.phase) {
        /* 14D3:1062 returns the loan, or keeps it after D32F's arena escape.
           A kept loan occupies bay zero; its former vehicle is moved to the
           first free later bay. Four full bays reproduce the original loss
           of the attempted extra vehicle, rather than inventing a fifth bay. */
        uint8_t player[125];memcpy(player,s->combat.unit[0].record,125);
        unsigned slot=s->yard.slot,rental=s->yard.rental,stolen=s->story_flags[35];
        unsigned y=s->campaign.battle_y+s->combat.unit[0].y;
        unsigned pilot=btp_combat_target(&s->combat,4);
        int dead=s->party.people[0][0]==255 ||
            (pilot<s->combat.count && s->combat.unit[pilot].record[0]==255);
        if (pilot<s->combat.count) memcpy(s->party.people[0],s->combat.unit[pilot].record,17);
        /* 14D3:10EA clears arena fire in sector 8A; wrecks elsewhere retain
           their own world position. Empty entries keep the original Y byte. */
        for (unsigned i=0;i<64;++i) {
            BtpTerrainMark *mark=&s->terrain_marks[i];
            if ((mark->sprite&126u)==124 && mark->sector==0x8a) mark->sprite=mark->sector=mark->x=0;
        }
        restore_party(s);
        if (!rental) {
            memcpy(btp_party_mech(s,slot),player,125);s->party.mech_types[slot]=player[0];
            /* 07DC:1B41 returns the selected owned vehicle to storage. Its
               retained model tag remains available at garage checkout. */
            if (!stolen) btp_party_mech(s,slot)[0]=255;
        }
        else if (stolen) {
            unsigned owned=0,free=4;
            for (unsigned i=0;i<4;++i) owned|=s->yard.types[i]!=255;
            for (unsigned i=1;i<4;++i) if (s->yard.types[i]==255 && free==4) free=i;
            if (!owned || free<4) {
                if (owned) { memcpy(btp_party_mech(s,free),s->yard.mechs[0],125);btp_party_mech(s,free)[0]=s->yard.types[0];s->party.mech_types[free]=s->yard.types[0]; }
                memcpy(s->campaign.mech,player,125);s->party.mech_types[0]=player[0];
            }
        }
        if (dead) { s->party.people[0][0]=255;s->story_flags[40]=1; }
        s->campaign.owned=0;
        for (unsigned i=0;i<4;++i) {
            uint8_t *m=btp_party_mech(s,i);
            if (s->party.mech_types[i]!=255) {
                s->campaign.owned=1;
                /* Only escape/theft restores the outdoor vehicles. A normal
                   arena return preserves parked records and their crew seats;
                   activating them here made them chase the on-foot party. */
                if (stolen) m[0]=s->party.mech_types[i];
            }
            if (stolen) m[121]=m[122]=255;
        }
        for (unsigned i=0;i<8;++i) s->party.people[i][12]=8;
        s->campaign.mounted=0;
        if (!stolen) force_fields(s,1);
        s->campaign.world_x=(uint16_t)(stolen ? 1264u : 1337u);s->campaign.world_y=(uint16_t)(stolen ? y : 1117u);
        s->map_id=(uint8_t)(stolen ? 0 : 2);s->x_half=(uint16_t)(stolen ? 1264u : 57u);s->y_half=(uint16_t)(stolen ? y : 93u);
        /* Escaping the arena crosses out of Starport; its suspended walkers
           must not remain attached to the surrounding wilderness map. */
        if (stolen) btp_npc_enter(s,&r->map);
        s->script.position_x=(uint16_t)((s->campaign.world_x/128u)*256u+(s->campaign.world_x&127u));
        s->script.position_y=(uint16_t)((s->campaign.world_y/128u)*4096u+(s->campaign.world_y&127u));
        s->yard=(BtpYardState){0};s->campaign.encounter=0;s->combat=(BtpCombatState){0};
        s->effects=(BtpEffectsState){0};s->aftermath=(BtpAftermathState){0};s->mode=BTP_BUILDING;
        btp_script_native_return(&s->script,btp_state_bld(r,s),s->story_flags);return;
    }
    if (s->campaign.encounter!=3 || s->combat.phase) return;
    memcpy(s->party.people[0],s->combat.unit[0].record,17);
    if (s->combat.lost) { btp_yard_finish_prison(s,r,0);return; }
    s->x_half=s->campaign.return_x;s->y_half=s->campaign.return_y;
    s->campaign.world_x=(uint16_t)(1664+s->x_half);s->campaign.world_y=(uint16_t)(896+s->y_half);
    s->campaign.encounter=0;s->combat=(BtpCombatState){0};s->effects=(BtpEffectsState){0};
    s->aftermath=(BtpAftermathState){0};s->mode=BTP_YARD;
}
void btp_yard_alarm(BtpState *s,const BtpResources *r,unsigned target)
{
    if (s->campaign.encounter!=4 || !s->yard.rental || btp_combat_id(&s->combat,target)!=13) return;
    /* 187F:1ECE copies the working terrain grid for the display; it does
       not write a new map tile. Keep the original Starport terrain here. */
    if (s->story_flags[35]) return;
    s->story_flags[35]=1;s->yard.alarm=1;BtpCombatState *c=&s->combat;
    /* 12E8:1D32 dispatches two original UrbanMechs at 097D/8030 and
       097D/8070. The shifted arena origin retains these exact locations. */
    for (unsigned i=0;i<2 && c->count<24;++i) {
        unsigned at=c->count++;BtpCombatUnit *u=&c->unit[at];memcpy(u->record,btp_mech_template(&r->combat,BTP_MECH_URBANMECH,0),125);
        u->x=61;u->y=(uint8_t)(48u+64u*i);u->direction=4;c->ids[at]=(uint8_t)(14+i);
        c->plan_direction[at]=4;c->walk[at]=8;
    }
}
unsigned btp_yard_tile(const BtpState *s,unsigned tile,int x,int y)
{
    for (unsigned i=0;i<s->yard.gate_count;++i) if (s->yard.gates[i][0]==x && s->yard.gates[i][1]==y) return s->yard.gates[i][2];
    return tile;
}
int btp_yard_valid(const BtpState *s)
{
    const BtpYardState *v=&s->yard;
    if (!v->active) {
        const uint8_t *b=(const uint8_t *)v;for (unsigned i=0;i<sizeof *v;++i) if (b[i]) return 0;
        return s->mode!=BTP_YARD;
    }
    if (v->active>2 || v->phase>BTP_YARD_FIGHT || v->timer>80 || v->idle>10 || v->checked>15 || v->attempts>3 ||
        v->selected>4 || v->slot>3 || v->rental>1 || v->variant>3 || v->alarm>3 || v->gate_count>16 || !s->checkpoint_valid) return 0;
    for (unsigned i=0;i<16;++i) {
        const uint8_t *g=v->gates[i];
        if (i<v->gate_count ? g[0]>=64 || g[1]>=64 || g[2]>=250 : g[0] || g[1] || g[2]) return 0;
    }
    if (v->active==1) return (s->mode==BTP_YARD || (s->mode==BTP_ENCOUNTER && s->campaign.encounter==3)) && s->campaign.building==13 &&
        s->script.status==BTP_SCRIPT_NATIVE && s->script.native_action==40 && v->phase<=BTP_YARD_FOUND;
    /* The owned-mech selector returns to ARENA.BLD's liability waiver
       before native 35 starts combat. That held page is saveable too. */
    if (s->campaign.building==10 && s->mode==BTP_BUILDING && v->phase==BTP_YARD_LOAN)
        return s->script.status==BTP_SCRIPT_WAIT;
    return s->campaign.building==10 && s->script.status==BTP_SCRIPT_NATIVE &&
        ((s->mode==BTP_YARD && (s->script.native_action==34 || s->script.native_action==35)) ||
         (s->mode==BTP_ENCOUNTER && s->campaign.encounter==4 && s->script.native_action==35));
}
