#include "data/unit_data.h"
#include "core/campaign.h"
#include "core/party.h"
#include "core/world.h"
#include "core/combat.h"
#include "core/npc.h"
#include "core/yard.h"
#include "core/service.h"
#include <string.h>
static void begin(BtpState *s,const BtpResources *r,unsigned event)
{
    BtpCampaignState *v=&s->campaign;
    v->return_map=s->map_id;v->return_x=s->x_half;v->return_y=s->y_half;
    v->battle_x=(uint16_t)(v->world_x&~127u);v->battle_y=(uint16_t)(v->world_y&~127u);v->encounter=(uint8_t)event;
    if (event==1) {
        /* Original positions remain world coordinates across sector seams.
           Centre the native window so nearby units do not wrap by 128. */
        unsigned x=v->world_x>64 ? v->world_x-64u : 0u,y=v->world_y>64 ? v->world_y-64u : 0u;
        v->battle_x=(uint16_t)(x>1920 ? 1920 : x&~15u);v->battle_y=(uint16_t)(y>1920 ? 1920 : y&~15u);
    }
    BtpCombatState *c=&s->combat;
    /* 103B:000A(0) describes the attacking force and asks to engage before
       computer/messages/graphics settings. Rex's argument -1 skips it. */
    *c=(BtpCombatState){.phase=(uint8_t)(event==1 ? BTP_COMBAT_OFFER : BTP_COMBAT_CONTROL),
        .selected=(uint8_t)(event==1 ? 0 : 1),.messages=2,.graphics=1,.movement=255,.kick_target=255,.enemy_movement=255};
    memset(c->orders,255,11);memset(c->enemy_orders,255,sizeof c->enemy_orders);memset(c->enemy_modes,255,sizeof c->enemy_modes);
    btp_party_init(s);btp_party_sync(s);
    unsigned formed=0;
    for (unsigned i=0;i<4;++i) if (s->party.mech_types[i]!=255 && btp_party_mech(s,i)[0]!=255) {
        unsigned pilot=btp_party_mech(s,i)[121];
        if (pilot>=8 || s->party.people[pilot][0]==255 || s->party.people[pilot][12]!=i) continue;
        BtpCombatUnit *u=&c->unit[c->count];memcpy(u->record,btp_party_mech(s,i),125);
        u->x=(uint8_t)((v->world_x-v->battle_x+r->combat.mech_formation_x[formed])&127);u->y=(uint8_t)((v->world_y-v->battle_y+r->combat.mech_formation_y[formed])&127);c->ids[c->count++]=(uint8_t)i;++formed;
    }
    formed=0;
    for (unsigned i=0;i<8;++i) if (s->party.people[i][0]!=255 && s->party.people[i][12]>=8) {
        BtpCombatUnit *u=&c->unit[c->count];u->infantry=1;memcpy(u->record,s->party.people[i],17);
        /* Original 103B:01DC formations assign fresh encounter positions. */
        u->x=(uint8_t)((v->world_x-v->battle_x+r->combat.formation_x[formed])&127);u->y=(uint8_t)((v->world_y-v->battle_y+r->combat.formation_y[formed])&127);++formed;
        c->ids[c->count++]=(uint8_t)(4+i);
    }
    c->friends=c->count;c->target_unit=c->friends;c->last_target=c->friends;
    /* 3920 uses FF for an unset computer heading; zero is north. */
    memset(c->plan_direction,255,c->count);c->plan_direction[0]=0;
    for (unsigned i=0;i<c->friends;++i) {
        c->plans[i].movement=255;c->plans[i].kick=255;memset(c->plans[i].orders,255,11);
    }
    s->mode=BTP_ENCOUNTER;s->x_half=c->unit[0].x;s->y_half=(uint16_t)(c->unit[0].y+(!c->unit[0].infantry ? 2u : 0u));
}
void btp_campaign_rex(BtpState *s,const BtpResources *r)
{
    btp_party_init(s);BtpPartyState *p=&s->party;uint8_t *rex=p->people[1];
    memset(rex,0,17);rex[0]=p->next_id++;rex[1]=12;rex[2]=9;rex[3]=8;
    memcpy(rex+4,r->combat.rex_skills,7);rex[11]=7;rex[12]=8;rex[15]=120;
    for (unsigned i=0;i<4;++i) if (p->mech_types[i]==255) {
        uint8_t *m=btp_party_mech(s,i);memcpy(m,btp_mech_template(&r->combat,BTP_MECH_COMMANDO,0),125);m[0]=255;m[121]=1;p->mech_types[i]='C';
        if (!i) s->campaign.owned=1;
        break;
    }
    s->campaign.world_x=1385;s->campaign.world_y=1118;s->x_half=105;s->y_half=94;
    s->script.position_x=0x0a69;s->script.position_y=0x805e;
    s->campaign.mounted=0;for (unsigned i=0;i<8;++i) p->people[i][12]=8;
    begin(s,r,2);BtpCombatState *c=&s->combat;
    unsigned x=114+(btp_rng_next(s->npc.rng)&1u),y=93+(btp_rng_next(s->npc.rng)&1u);
    unsigned count=2+(btp_rng_next(s->npc.rng)&3u);
    for (unsigned i=0;i<count;++i) {
        unsigned slot=c->count++;BtpCombatUnit *u=&c->unit[slot];u->infantry=1;u->record[12]=8;
        u->x=(uint8_t)(x+r->combat.rex_x[i]);u->y=(uint8_t)(y+r->combat.rex_y[i]);u->direction=6;c->ids[slot]=(uint8_t)(16+i);
        for (unsigned k=4;k<=9;++k) u->record[k]=(uint8_t)(btp_rng_next(s->npc.rng)&1u);
        u->record[1]=(uint8_t)btp_combat_dice(s->npc.rng);u->record[15]=(uint8_t)(u->record[1]*10);
        u->record[11]=(uint8_t)(btp_rng_next(s->npc.rng)%8u);
    }
}
unsigned btp_campaign_candidates(BtpState *s,const BtpResources *r,BtpCombatUnit candidates[12],uint8_t ids[12],int *dx_out,int *dy_out)
{
    btp_party_init(s);
    int dx=10+(int)(btp_rng_next(s->npc.rng)&7u);if (btp_rng_next(s->npc.rng)&1u) dx=-dx;
    int dy=10+(int)(btp_rng_next(s->npc.rng)&7u);if (btp_rng_next(s->npc.rng)&1u) dy=-dy;
    memset(candidates,0,12*sizeof *candidates);memset(ids,0,12);unsigned count=0;
    for (unsigned i=0;i<8;++i) if (btp_rng_next(s->npc.rng)&1u) {
        BtpCombatUnit *u=&candidates[count];u->infantry=1;u->record[0]=1;u->record[12]=8;ids[count++]=(uint8_t)(16+i);
        unsigned weapon=0;for (unsigned j=0;j<7;++j) weapon+=btp_rng_next(s->npc.rng)&3u;
        u->record[11]=r->combat.encounter_weapons[weapon];
        u->record[1]=(uint8_t)btp_combat_dice(s->npc.rng);u->record[15]=(uint8_t)(10*u->record[1]);
        u->record[2]=(uint8_t)btp_combat_dice(s->npc.rng);
        for (unsigned j=4;j<=10;++j) u->record[j]=(uint8_t)(btp_rng_next(s->npc.rng)&3u);
        u->record[13]=(uint8_t)(btp_rng_next(s->npc.rng)&3u);
        u->record[14]=(uint8_t)(btp_combat_dice(s->npc.rng)+btp_combat_dice(s->npc.rng));
    }
    for (unsigned i=0;i<4;++i) if ((btp_rng_next(s->npc.rng)&1u) && s->map_id!=2 &&
        btp_party_mech(s,i)[0]!=255 && s->party.mech_types[i]!=255) {
        /* Starport's ordinary encounters are on foot. Its separate arena
           setup supplies mechs explicitly; parked ownership cannot qualify
           a random town encounter for enemy vehicles. */
        unsigned kind=btp_rng_next(s->npc.rng)%3u;
        memcpy(candidates[count].record,btp_mech_template(&r->combat,BTP_MECH_ENCOUNTER,kind),125);ids[count++]=(uint8_t)(12+i);
    }
    *dx_out=dx;*dy_out=dy;return count;
}
enum { ENCOUNTER_SIDE=128, ENCOUNTER_CELLS=128*128 };
static void encounter_reachable(const BtpState *s,const BtpResources *r,uint8_t reachable[ENCOUNTER_CELLS])
{
    BtpMap map;btp_combat_map(r,s,&map);
    uint8_t allowed[ENCOUNTER_CELLS];uint16_t queue[ENCOUNTER_CELLS];
    memset(reachable,0,ENCOUNTER_CELLS);
    for (unsigned y=0;y<ENCOUNTER_SIDE;++y) for (unsigned x=0;x<ENCOUNTER_SIDE;++x) {
        unsigned at=y*ENCOUNTER_SIDE+x;allowed[at]=0;
        if (x>=126) continue;
        /* 05AB:1174/13F8 and combat movement sample ceil(x/2) for a
           person, and both adjacent ground tiles for a mech. */
        if (btp_map_tile(&map,(int)(x+1)/2,(int)y/2)<85) allowed[at]=1;
        int wx=(s->campaign.battle_x+(int)x)/2,wy=(s->campaign.battle_y+(int)y)/2;
        if (btp_map_tile(&map,(int)x/2,(int)y/2)<85 && btp_map_tile(&map,(int)x/2+1,(int)y/2)<85 &&
            btp_world_location(r,s,wx,wy)!=2 && btp_world_location(r,s,wx+1,wy)!=2) allowed[at]|=2;
    }
    /* Owner-requested protection beyond the original's terrain-only scan:
       every proposed enemy must be able to approach a living party member.
       Flood each footprint separately; ignore temporary unit occupancy and
       use the same eight destination checks as combat movement. Starport
       remains closed to ordinary enemy mechs, including battles outside it.
       This guard consumes no random draws and never affects scripted fights. */
    for (unsigned bit=1;bit<=2;bit*=2) {
        unsigned head=0,tail=0;
        for (unsigned i=0;i<s->combat.friends;++i) {
            const BtpCombatUnit *u=&s->combat.unit[i];if (u->record[0]==255) continue;
            /* A wide enemy may approach an infantryman from either side
               even when its centre cannot occupy that exact half-step. */
            int margin=bit==2 && u->infantry ? 1 : 0;
            for (int offset=-margin;offset<=margin;++offset) {
                int x=(int)u->x+offset;if (x<0 || x>=ENCOUNTER_SIDE || u->y>=ENCOUNTER_SIDE) continue;
                unsigned at=(unsigned)u->y*ENCOUNTER_SIDE+(unsigned)x;
                if ((allowed[at]&bit) && !(reachable[at]&bit)) {
                    reachable[at]|=(uint8_t)bit;queue[tail++]=(uint16_t)at;
                }
            }
        }
        while (head<tail) {
            unsigned at=queue[head++];int x=(int)(at%ENCOUNTER_SIDE),y=(int)(at/ENCOUNTER_SIDE);
            for (int dy=-1;dy<=1;++dy) for (int dx=-1;dx<=1;++dx) {
                int nx=x+dx,ny=y+dy;
                if ((!dx && !dy) || nx<0 || ny<0 || nx>=ENCOUNTER_SIDE || ny>=ENCOUNTER_SIDE) continue;
                unsigned next=(unsigned)ny*ENCOUNTER_SIDE+(unsigned)nx;
                if ((allowed[next]&bit) && !(reachable[next]&bit)) {
                    reachable[next]|=(uint8_t)bit;queue[tail++]=(uint16_t)next;
                }
            }
        }
    }
}
int btp_campaign_random(BtpState *s,const BtpResources *r)
{
    BtpCombatUnit candidates[12];uint8_t ids[12];int dx,dy;
    unsigned count=btp_campaign_candidates(s,r,candidates,ids,&dx,&dy);
    if (!count) return 0;
    begin(s,r,1);BtpCombatState *c=&s->combat;
    uint8_t reachable[ENCOUNTER_CELLS];encounter_reachable(s,r,reachable);
    /* Original 05AB:0DA6/106F offsets from the exploration cursor, not
       from the first mech's ground point two half-steps farther north. */
    int start_x=(int)s->campaign.world_x-s->campaign.battle_x+dx;
    int start_y=(int)s->campaign.world_y-s->campaign.battle_y+dy,x=start_x,y=start_y,column=0,mechs=0;
    for (unsigned i=0;i<count;++i) {
        /* 05AB:11F5 leaves a gap before the vehicles; 13B7 advances three
           half-steps after each placed mech and wraps after column eight.
           Failed terrain/reachability candidates still advance one cell. */
        if (!candidates[i].infantry && !mechs) { ++x;++column;mechs=1; }
        int placed=0;
        while (y<start_y+24) {
            if (x>=0 && y>=2 && x<126 && y<128 &&
                (reachable[(unsigned)y*ENCOUNTER_SIDE+(unsigned)x]&(candidates[i].infantry ? 1u : 2u))) {
                unsigned tile=btp_world_tile(r,s,s->campaign.battle_x/2+(x+(int)candidates[i].infantry)/2,s->campaign.battle_y/2+y/2);
                unsigned second=btp_world_tile(r,s,s->campaign.battle_x/2+x/2+1,s->campaign.battle_y/2+y/2);
                if (tile>15 && tile<85 &&
                    (candidates[i].infantry || (second>15 && second<85))) { placed=1;break; }
            }
            ++x;if (++column>16) { column=0;x=start_x;++y; }
        }
        if (!placed) continue;
        unsigned at=c->count++;c->unit[at]=candidates[i];c->unit[at].x=(uint8_t)x;c->unit[at].y=(uint8_t)y;c->unit[at].direction=6;c->plan_direction[at]=255;c->ids[at]=ids[i];
        x+=candidates[i].infantry ? 1 : 3;column+=candidates[i].infantry ? 1 : 3;
        if (column>(candidates[i].infantry ? 16 : 8)) { column=0;x=start_x;++y; }
    }
    if (c->count==c->friends) { s->mode=BTP_EXPLORE;s->x_half=s->campaign.return_x;s->y_half=s->campaign.return_y;s->campaign.encounter=0;s->combat=(BtpCombatState){0};return 0; }
    return 1;
}
void btp_campaign_result(BtpState *s,const BtpResources *r)
{
    BtpCombatState *c=&s->combat;
    if (!s->campaign.encounter || c->phase || s->aftermath.phase) return;
    if (s->campaign.encounter==4 && !s->story_flags[35] && !s->aftermath.applied &&
        s->party.people[0][0]!=255) {
        unsigned pilot=btp_combat_target(c,4);
        if (pilot>=c->count || c->unit[pilot].record[0]!=255) {
            /* 103B:13AD..13DA holds the arena result before the cashier.
               D32D distinguishes a standing mech from a surviving pilot. */
            s->story_flags[33]=(uint8_t)(c->unit[0].record[0]!=255);
            s->aftermath.applied=1;s->aftermath.phase=11;return;
        }
    }
    if (s->campaign.encounter>=3) { btp_yard_result(s,r);return; }
    if (!s->aftermath.applied) {
    for (unsigned i=0;i<c->friends;++i) {
        unsigned id=c->ids[i];
        if (id<4) memcpy(btp_party_mech(s,id),c->unit[i].record,125);
        else if (id<12) { memcpy(s->party.people[id-4],c->unit[i].record,17);s->party.x[id-4]=(uint16_t)(s->campaign.battle_x+c->unit[i].x);s->party.y[id-4]=(uint16_t)(s->campaign.battle_y+c->unit[i].y); }
    }
        s->aftermath.applied=2;
        if (c->lost) { s->mode=BTP_GAME_OVER;return; }
        /* 103B:10A3..10DA announces defeated enemies before scavenging.
           Keep this pause explicit so saving cannot apply the rewards twice. */
        for (unsigned i=12;i<24;++i) if (s->aftermath.wrecks[i]) {
            s->aftermath.phase=5;return;
        }
    }
    if (s->aftermath.applied==2) {
        unsigned donors=0,owned=0,skill=0,technician=0;
        for (unsigned i=0;i<4;++i) { donors|=s->aftermath.wrecks[12+i];owned|=btp_party_mech(s,i)[0]!=255; }
        for (unsigned i=0;i<8;++i) if (s->party.people[i][0]!=255 && s->party.people[i][9]>skill) {
            skill=s->party.people[i][9];technician=i;
        }
        if (donors && owned && skill) { s->aftermath.pilot=(uint8_t)technician;s->aftermath.phase=8;return; }
        s->aftermath.applied=4;
    }
    if (s->aftermath.applied==4) {
        s->aftermath.applied=1;
        /* 103B:0C4C calls salvage before pocket cash, including withdrawal. */
        unsigned wreck=0,empty=0;
        for (unsigned i=0;i<4;++i) { wreck|=s->aftermath.wrecks[i] || s->aftermath.wrecks[12+i];empty|=btp_party_mech(s,i)[0]==255; }
        for (unsigned i=0;i<8 && wreck && empty && !btp_world_populated(r,s);++i) if (s->party.people[i][0]!=255 && s->party.people[i][8] && s->party.people[i][12]>=8) {
            s->aftermath.pilot=(uint8_t)i;s->aftermath.phase=1;return;
        }
        s->aftermath.pilot=8;btp_aftermath_input(s,r,BTP_IDLE);if (s->aftermath.phase) return;
    }
    if (s->aftermath.applied==1) {
        s->aftermath.applied=3;s->aftermath.phase=(uint8_t)(c->fled ? 6 : 7);
        if (!c->fled) {
            /* The original treats remaining wounds after looting, clearing
               the previous treatment cooldown first (103B:1256..12BD). */
            unsigned wounded=0;
            for (unsigned i=0;i<8;++i) if (s->party.people[i][0]!=255)
                wounded|=s->party.people[i][15]!=10u*s->party.people[i][1];
            s->story_flags[41]=0;
            if (wounded) { btp_service_heal(s,r,0,2);s->aftermath.phase=10; }
        }
        return;
    }
    unsigned event=s->campaign.encounter;s->campaign.encounter=0;
    s->x_half=s->campaign.return_x;s->y_half=s->campaign.return_y;s->map_id=s->campaign.return_map;
    s->combat=(BtpCombatState){0};s->effects=(BtpEffectsState){0};
    s->aftermath=(BtpAftermathState){0};
    s->service=(BtpServiceState){0};
    s->campaign.mounted=(uint8_t)(s->party.people[0][12]<4);
    s->campaign.owned=0;for (unsigned i=0;i<4;++i) s->campaign.owned|=(uint8_t)(s->party.mech_types[i]!=255);
    memcpy(s->skills,s->party.people[0]+4,3);memcpy(s->mech_skills,s->party.people[0]+7,2);
    s->technician=s->party.people[0][9];s->weapon=s->party.people[0][11];s->armor=s->party.people[0][13];s->armor_points=s->party.people[0][14];
    if (event==2) { s->mode=BTP_BUILDING;btp_script_native_return(&s->script,btp_state_bld(r,s),s->story_flags); }
    else s->mode=BTP_EXPLORE;
}

void btp_campaign_avoid(BtpState *s)
{
    /* 103B:0499 exits before salvage/cash when No's RNG & 3 is nonzero. */
    s->x_half=s->campaign.return_x;s->y_half=s->campaign.return_y;s->map_id=s->campaign.return_map;
    s->campaign.encounter=0;s->combat=(BtpCombatState){0};s->effects=(BtpEffectsState){0};
    s->aftermath=(BtpAftermathState){0};s->mode=BTP_EXPLORE;
}
unsigned btp_aftermath_cash(uint8_t rng[3],unsigned count)
{
    unsigned amount=0;for (unsigned i=0;i<count;++i) amount+=(btp_rng_next(rng)&15u)+3u;
    return amount<2 ? 2 : amount;
}
int btp_salvage_eligible(const uint8_t m[125],unsigned skill)
{
    return skill>=4 || (m[117]!=3 && m[118]!=2 && m[31]!=0);
}
void btp_salvage_copy(BtpState *s,unsigned slot,unsigned pilot,const uint8_t m[125],unsigned kind)
{
    if (slot>=4 || pilot>=8) return;
    uint8_t *dest=btp_party_mech(s,slot);memmove(dest+1,m+1,124);dest[0]=(uint8_t)kind;
    dest[121]=(uint8_t)pilot;s->party.people[pilot][12]=(uint8_t)slot;
    dest[117]=dest[118]=1;if (!dest[31]) dest[31]=1;if (!dest[32]) dest[32]=1;
    s->party.mech_types[slot]=(uint8_t)kind;s->campaign.owned=1;
}
void btp_campaign_destroy(BtpState *s,unsigned unit)
{
    BtpCombatState *c=&s->combat;BtpCombatUnit *u=&c->unit[unit];unsigned id=c->ids[unit];
    s->aftermath.wrecks[id]=(uint8_t)(u->infantry ? 128 : u->record[0]);u->record[0]=255;
    if (s->campaign.encounter==4 && s->yard.rental && !s->story_flags[35] && id==12) {
        /* 0D43:0AE1..0B08 retires the spectator when the actual opponent
           falls. It is removed silently, with no casualty, sound or alarm. */
        unsigned spectator=btp_combat_target(c,13);
        if (spectator<c->count) c->unit[spectator].record[0]=255;
    }
    if (id<4) s->aftermath.eject|=(uint16_t)(1u<<id);
    /* 12E8:1BD1 treats either of the first two character slots as an
       essential party member, including Rex after he joins Jason. */
    if (id==4 || id==5) s->effects.pending=2;
    for (unsigned i=0;i<c->count;++i) {
        for (unsigned j=0;j<11;++j) {
            if (c->plans[i].orders[j]==id) c->plans[i].orders[j]=255;
            if (i && c->enemy_orders[i-1][j]==id) c->enemy_orders[i-1][j]=255;
            if (c->orders[j]==id) c->orders[j]=255;
        }
        if (c->plans[i].kick==id) c->plans[i].kick=255;
        if (i && c->enemy_orders[i-1][11]==id) c->enemy_orders[i-1][11]=255;
    }
    if (c->kick_target==id) c->kick_target=255;
}
void btp_campaign_eject(BtpState *s)
{
    BtpCombatState *c=&s->combat;
    for (unsigned id=0;id<4;++id) if (s->aftermath.eject&(1u<<id)) {
        unsigned dead=btp_combat_target(c,id);if (dead>=c->count) continue;
        const BtpCombatUnit wreck=c->unit[dead];
        for (unsigned crew=0;crew<2;++crew) {
            unsigned p=wreck.record[121+crew];if (p>=8 || s->party.people[p][0]==255 || c->count>=24) continue;
            s->party.people[p][12]=8;s->party.x[p]=(uint16_t)(s->campaign.battle_x+wreck.x+crew);s->party.y[p]=(uint16_t)(s->campaign.battle_y+wreck.y);
            unsigned at=c->friends;
            /* Unit IDs stay original; only native array indexes shift. No
               visual effects remain at this insertion boundary. */
            for (unsigned k=c->count;k>at;--k) {
                c->unit[k]=c->unit[k-1];c->ids[k]=c->ids[k-1];c->plans[k]=c->plans[k-1];
                memcpy(c->path[k],c->path[k-1],sizeof c->path[k]);c->moved[k]=c->moved[k-1];c->path_index[k]=c->path_index[k-1];c->walk[k]=c->walk[k-1];c->plan_direction[k]=c->plan_direction[k-1];c->fallback[k]=c->fallback[k-1];
                memcpy(c->enemy_orders[k-1],c->enemy_orders[k-2],12);c->enemy_fired[k-1]=c->enemy_fired[k-2];
                if (k==2) c->enemy_modes[0]=c->enemy_movement;else c->enemy_modes[k-2]=c->enemy_modes[k-3];
            }
            /* Original 0D43:0A35 creates people facing direction zero,
               independently of their destroyed vehicle's facing. */
            c->unit[at]=(BtpCombatUnit){.infantry=1,.x=(uint8_t)((wreck.x+crew)&127),.y=wreck.y};memcpy(c->unit[at].record,s->party.people[p],17);
            c->ids[at]=(uint8_t)(4+p);c->plans[at]=(BtpCombatPlan){.movement=255,.kick=255};memset(c->plans[at].orders,255,11);
            memset(c->path[at],0,sizeof c->path[at]);c->moved[at]=c->path_index[at]=c->walk[at]=c->plan_direction[at]=c->fallback[at]=0;
            memset(c->enemy_orders[at-1],255,12);c->enemy_fired[at-1]=0;if (at==1) c->enemy_movement=255;else c->enemy_modes[at-2]=255;
            if (c->last_attacker>=at) ++c->last_attacker;
            if (c->last_target>=at) ++c->last_target;
            if (c->target_unit>=at) ++c->target_unit;
            if (c->scan_unit>=at) ++c->scan_unit;
            ++c->friends;++c->count;
        }
        if (c->active_unit==dead) for (unsigned i=0;i<c->friends;++i) if (c->unit[i].record[0]!=255) { btp_combat_select(c,i);break; }
    }
    s->aftermath.eject=0;
}
static void pockets(BtpState *s)
{
    BtpAftermathState *v=&s->aftermath;unsigned dead=0,any=0,weapon=0;
    for (unsigned i=0;i<8;++i) {
        any|=v->wrecks[4+i] || v->wrecks[16+i];
        if (v->wrecks[16+i]) {
            ++dead;
            /* Primary 05AB:09A1 samples C6EB+17*(4+i), which overlaps
               owned-mech bytes. Preserve this original classifier quirk. */
            unsigned byte=11u+17u*i;weapon|=btp_party_mech(s,byte/125u)[byte%125u]!=0;
        }
    }
    if (!any) { v->phase=0;return; }
    v->cash=(uint16_t)btp_aftermath_cash(s->npc.rng,dead);s->credits+=v->cash;v->phase=3;v->notice=(uint8_t)weapon;v->unit=16;
}
static void next_pilot(BtpState *s)
{
    BtpAftermathState *v=&s->aftermath;
    v->attempts=0;memset(v->inspected,0,sizeof v->inspected);memset(v->models,0,sizeof v->models);
    for (unsigned i=v->pilot+1u;i<8;++i) if (s->party.people[i][0]!=255 && s->party.people[i][8] && s->party.people[i][12]>=8) {
        v->pilot=(uint8_t)i;v->phase=1;v->selected=0;return;
    }
    v->pilot=8;pockets(s);
}
static unsigned salvage_left(const BtpAftermathState *v)
{
    unsigned count=0;for (unsigned i=0;i<16;++i) count+=v->wrecks[i]!=0;return count;
}
static void salvage_attempts(BtpState *s)
{
    BtpAftermathState *v=&s->aftermath;
    /* The original takes two random draws per inspected wreck. A failed
       inspection immediately repeats for the same pilot, without a key wait
       or another Yes/No. The accumulated results share one held text page. */
    do {
        if (!salvage_left(v)) { v->phase=2;v->notice=2;return; }
        unsigned id=btp_rng_next(s->npc.rng)&3u;id+=12u*(btp_rng_next(s->npc.rng)&1u);
        while (!v->wrecks[id]) id=(id+1u)&15u;
        unsigned kind=v->wrecks[id];v->wrecks[id]=0;v->unit=(uint8_t)id;v->cash=(uint16_t)kind;
        if (v->attempts<16) { v->inspected[v->attempts]=(uint8_t)id;v->models[v->attempts++]=(uint8_t)kind; }
        unsigned at=btp_combat_target(&s->combat,id),skill=0,slot=0;
        for (unsigned i=0;i<8;++i) if (s->party.people[i][0]!=255 && s->party.people[i][9]>skill) skill=s->party.people[i][9];
        while (slot<4 && btp_party_mech(s,slot)[0]!=255) ++slot;
        v->phase=2;v->notice=1;
        if (at<s->combat.count && kind!=128 && btp_salvage_eligible(s->combat.unit[at].record,skill)) {
            if (slot<4) btp_salvage_copy(s,slot,v->pilot,s->combat.unit[at].record,kind);
            v->notice=0;return;
        }
    } while (salvage_left(v));
}
static void next_weapon(BtpState *s)
{
    BtpAftermathState *v=&s->aftermath;
    while (v->unit<24) {
        unsigned at=btp_combat_target(&s->combat,v->unit);
        if (v->wrecks[v->unit] && at<s->combat.count && s->combat.unit[at].record[11]) { v->phase=4;v->selected=0;return; }
        ++v->unit;
    }
    v->phase=0;
}
void btp_aftermath_input(BtpState *s,const BtpResources *r,BtpAction a)
{
    (void)r;BtpAftermathState *v=&s->aftermath;
    if (!v->phase) { pockets(s);return; }
    unsigned count=v->phase==1 || (v->phase==4 && btp_party_count(&s->party)==1) ? 2u : v->phase==4 ? btp_party_count(&s->party)+1u : 1u;
    if (a==BTP_UP || a==BTP_LEFT) v->selected=(uint8_t)((v->selected+count-1)%count);
    if (a==BTP_DOWN || a==BTP_RIGHT) v->selected=(uint8_t)((v->selected+1)%count);
    if (a==BTP_OPEN_MENU) a=BTP_ACCEPT;
    if (a!=BTP_ACCEPT && a!=BTP_CANCEL) return;
    if (v->phase==5 || v->phase==7 || v->phase==11) { v->phase=0;return; }
    if (v->phase==6) { v->phase=7;return; }
    if (v->phase==10) { s->service=(BtpServiceState){0};v->phase=7;return; }
    if (v->phase==8) {
        uint8_t wrecks[4][125]={{0}},marked[4]={0};
        for (unsigned i=0;i<4;++i) {
            unsigned at=btp_combat_target(&s->combat,12+i);
            if (at<s->combat.count && v->wrecks[12+i]) { marked[i]=1;memcpy(wrecks[i],s->combat.unit[at].record,125); }
        }
        v->cash=(uint16_t)btp_party_field_salvage(s,(const uint8_t (*)[125])wrecks,marked);
        s->credits-=v->cash;v->applied=4;v->phase=(uint8_t)(v->cash ? 9 : 0);return;
    }
    if (v->phase==9) { s->credits+=v->cash;v->cash=0;v->phase=0;return; }
    if (v->phase==1) {
        if (v->selected || a==BTP_CANCEL) { next_pilot(s);return; }
        salvage_attempts(s);
    } else if (v->phase==2) {
        if (v->notice==2) { v->pilot=8;pockets(s); }
        else if (!salvage_left(v)) v->notice=2;
        /* Older saves may hold the former per-wreck failure page. Resume
           this pilot's search, preserving the already consumed RNG draws. */
        else if (v->notice==1) salvage_attempts(s);
        else next_pilot(s);
    }
    else if (v->phase==3) { if (v->notice) next_weapon(s);else v->phase=0; }
    else if (v->phase==4) {
        unsigned p=btp_party_count(&s->party)==1 ? 0u : btp_party_slot(&s->party,v->selected);
        if (a==BTP_ACCEPT && (btp_party_count(&s->party)==1 ? !v->selected : p<8) && s->party.people[p][0]!=255) {
            /* 05AB:0A54 redistributes the recipient's old weapon next.
               Keep the same recovered slot until that weapon is dropped. */
            unsigned at=btp_combat_target(&s->combat,v->unit),old=s->party.people[p][11];
            s->party.people[p][11]=s->combat.unit[at].record[11];s->combat.unit[at].record[11]=(uint8_t)old;
            if (!p) s->weapon=s->party.people[p][11];
            if (old) return;
        }
        ++v->unit;next_weapon(s);
    }
}
int btp_aftermath_valid(const BtpState *s)
{
    const BtpAftermathState *v=&s->aftermath;
    if (v->eject>15 || v->phase>11 || v->selected>8 || v->pilot>8 || v->unit>24 || v->notice>2 || v->applied>4 ||
        v->attempts>16 || (v->phase!=9 && v->cash>144)) return 0;
    unsigned inspected=0;
    for (unsigned i=0;i<16;++i) {
        if (i>=v->attempts) { if (v->inspected[i] || v->models[i]) return 0; }
        else {
            if (v->inspected[i]>=16 || !v->models[i] || v->models[i]>128 || (inspected&(1u<<v->inspected[i]))) return 0;
            inspected|=1u<<v->inspected[i];
        }
    }
    if (v->phase==11 && (s->campaign.encounter!=4 || s->story_flags[35] || v->applied!=1)) return 0;
    if ((v->eject || v->phase || v->applied) && !s->campaign.encounter) return 0;
    if (v->phase && (s->mode!=BTP_ENCOUNTER || s->combat.phase || !v->applied)) return 0;
    for (unsigned i=0;i<24;++i) if (v->wrecks[i] && (!s->campaign.encounter || (i>=4 && i<12 ? v->wrecks[i]!=128 : i>=16 ? v->wrecks[i]!=128 : v->wrecks[i]>=128))) return 0;
    return 1;
}
