#include "data/chi_missions.h"
#include "data/unit_data.h"
#include "data/definitions.h"
#include "core/combat.h"
#include "core/combat_ai.h"
#include "core/npc.h"
#include "core/animation.h"
#include "data/chi_spatial.h"
#include "core/effects.h"
#include "core/campaign.h"
#include "core/world.h"
#include "core/party.h"
#include "core/audio.h"
#include "core/yard.h"
#include "core/spy.h"
#include "core/events.h"
#include "core/battle_mission.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>

static const int8_t dx[8] = {0,1,1,1,0,-1,-1,-1};
static const int8_t dy[8] = {-1,-1,0,1,1,1,0,-1};
int btp_invasion_outside(unsigned x,unsigned y)
{
    /* Executed 103B:0610: packed 0B7F/B07F inclusive, 0D00/D000
       exclusive. These preserve the original extra half-tile at the edge. */
    return x<1535 || x>=1664 || y<1535 || y>=1664;
}
static unsigned tile_at(const BtpMap *m, int sx, int sy, int at);
static int half(int n) { return n/2-(n < 0 && n%2 != 0); }
static unsigned turn(unsigned from, unsigned to)
{
    return from == to ? from : (from+(((to-from)&7u) < 5 ? 1u : 7u))&7u;
}
static int los(const BtpMap *m,unsigned gate,int x,int y,int tx,int ty,const uint8_t *prefix,const BtpResources *r,const BtpState *s)
{
    /* 0E31:1BFE follows a gradually turning ray through a 24x24 working
       grid. Preserve its asymmetric parity updates instead of Bresenham. */
    int sx=x, sy=y, at=(((y&15)/2)+2)*24+((x&15)/2)+152+(x&1), px=!(x&1), py=y&1;
    unsigned heading=btp_combat_direction(x,y,tx,ty);
    for (unsigned i=0; i<256; ++i) {
        /* The nine descriptors immediately precede the 24x24 grid at
           BUFFER:07A4. A long ray can read one of them at its edge. */
        if (at<(r ? -585 : -9) || at>=576 || (at<0 && !prefix)) return -1;
        unsigned tile;
        if (at<-9) {
            /* 0E31:1BFE's ray can underflow the viewport into BUFFER:0564,
               the nine raw sector-height grids before its descriptors.
               These are height bytes, not the corresponding forest tiles. */
            unsigned cell=(unsigned)(at+585),sector=cell/64u;
            int ox=((int)s->campaign.battle_x+sx)/128-1+(int)(sector%3u);
            int oy=((int)s->campaign.battle_y+sy)/128-1+(int)(sector/3u);
            tile=btp_world_descriptor(r,s,ox*64+(int)(cell%8u)*8,
                oy*64+(int)((cell%64u)/8u)*8);
            if (tile<144) tile&=240u;
        } else tile=at<0 ? prefix[at+9] : r ? btp_world_tile(r,s,
            (int)s->campaign.battle_x/2+(sx&~15)/2-8+at%24,
            (int)s->campaign.battle_y/2+(sy&~15)/2-8+at/24) : tile_at(m,sx,sy,at);
        if (tile>=gate) return 0;
        if (x == tx && y == ty) return 1;
        unsigned desired=btp_combat_direction(x,y,tx,ty);
        if (heading > 7 || desired > 7) return 0;
        heading=turn(heading,desired);
        x+=dx[heading]; y+=dy[heading];
        if (dx[heading]) { px=(px+dx[heading])&1; if (!px) at+=dx[heading]; }
        if (dy[heading]) { py=(py+dy[heading])&1; if (!py) at+=24*dy[heading]; }
    }
    return 0;
}
int btp_combat_los(const BtpMap *m,unsigned gate,int x,int y,int tx,int ty)
{
    return los(m,gate,x,y,tx,ty,NULL,NULL,NULL);
}
int btp_combat_scene_los(const BtpResources *r,const BtpState *s,const BtpMap *m,int x,int y,int tx,int ty)
{
    if (s->event.enabled || !s->campaign.encounter || !r->world.native) return btp_combat_los(m,s->gate,x,y,tx,ty);
    uint8_t prefix[9];
    int bx=((int)s->campaign.battle_x+x)&~15,by=((int)s->campaign.battle_y+y)&~15;
    for (unsigned i=0;i<9;++i) prefix[i]=(uint8_t)btp_world_descriptor(r,s,
        bx/2+8*((int)(i%3u)-1),by/2+8*((int)(i/3u)-1));
    return los(m,s->gate,x,y,tx,ty,prefix,r,s);
}
static int grid(int sx, int sy, int x, int y, int cost, unsigned *mask)
{
    int screen_x=x-sx+26, screen_y=y-sy+12;
    int at=(((sy&15)/2)+2)*24+((sx&15)/2)+2+half(screen_y)*24+half(screen_x-13);
    static const unsigned masks[4]={9,3,12,6};
    *mask=masks[(screen_x&1)+2*(screen_y&1)];
    if ((cost ? screen_x&1 : !(screen_x&1)) && (sx&1)) { ++at; *mask^=10; }
    if ((screen_y&1) && (sy&1)) { at+=24; *mask^=5; }
    return at;
}
static unsigned tile_at(const BtpMap *m, int sx, int sy, int at)
{
    if (at < 0 || at >= 576) return 255;
    /* Keep the sector bits when a battle has a generated-world margin. */
    return btp_map_tile(m,(sx&~15)/2-8+at%24,(sy&~15)/2-8+at/24);
}
static int occupied(const BtpCombatUnit *mover, const BtpCombatUnit *other, int x, int y)
{
    return other && other->record[0] != 255 && y == other->y &&
        abs(x-other->x) < 1+!mover->infantry+!other->infantry;
}
unsigned btp_combat_id(const BtpCombatState *c, unsigned i)
{
    if (c->friends && i<c->count) return c->ids[i];
    return !i ? 0 : c->unit[i].infantry ? 15u+i : 11u+i;
}
unsigned btp_combat_target(const BtpCombatState *c, unsigned id)
{
    for (unsigned i=0;i<c->count;++i) if (btp_combat_id(c,i)==id) return i;
    return BTP_COMBAT_UNITS;
}
static void plan_points(const BtpMap *m, unsigned gate, const BtpCombatUnit *u,
    const BtpCombatUnit *other, int tx, int ty, unsigned movement, int computer,
    int points, const uint8_t *wx, const uint8_t *wy, unsigned waypoints,
    const BtpCombatUnit *units, unsigned count, unsigned self, unsigned friends, const BtpState *state, int8_t steps[12][2])
{
    memset(steps,2,24);
    int x=u->x, y=u->y, stopped=0;
    unsigned heading=computer ? u->direction : btp_combat_direction(x,y,tx,ty);
    unsigned waypoint=0;
    for (unsigned i=0; i<12 && points>0 && !stopped; ++i) {
        while (x==tx && y==ty && waypoint<waypoints) {
            tx=wx[waypoint];ty=wy[waypoint++];heading=btp_combat_direction(x,y,tx,ty);
        }
        if (x==tx && y==ty) break;
        unsigned desired=btp_combat_direction(x,y,tx,ty);
        if (desired>7) break;
        if (heading>7) heading=desired;
        heading=turn(heading,desired);
        steps[i][0]=steps[i][1]=0;
        for (unsigned trial=0; trial<8; ++trial) {
            int offset=trial ? (int)((trial+1)/2)*(trial&1u ? 1 : -1) : 0;
            unsigned d=(unsigned)((int)heading+offset+8)&7u;
            int nx=x+dx[d], ny=y+dy[d]; unsigned mask;
            if (nx<0 || ny<0 || nx>=2*m->width-2 || ny>=2*m->height-(m->authored && !u->infantry ? 2 : 0)) continue;
            int at=grid(u->x,u->y,nx,ny,0,&mask);
            /* Executed 0E31:0006 checks blocking tiles for Jump as well.
               103B:1BAC skips terrain costs in Jump; it does not skip walls. */
            if (tile_at(m,u->x,u->y,at)>=gate || (!u->infantry && tile_at(m,u->x,u->y,at+(nx&1 ? -1 : 1))>=gate)) continue;
            unsigned vehicle=u->infantry ? 0u : btp_vehicle_kind(u->record);
            if (vehicle && (!btp_vehicle_terrain(vehicle,tile_at(m,u->x,u->y,at)) ||
                !btp_vehicle_terrain(vehicle,tile_at(m,u->x,u->y,at+(nx&1 ? -1 : 1))))) continue;
            /* 0E31:16AB blocks a mech on allied infantry. Enemy infantry
               is eligible for trampling, so it must not divert the planned
               path before the movement routine can resolve that contact. */
            int blocked=other && !(!u->infantry && other->infantry) && occupied(u,other,nx,ny);
            for (unsigned k=0;k<count;++k)
                if (k!=self && !(!u->infantry && units[k].infantry && (state ? btp_battle_hostile(state,self,k) : (k<friends)!=(self<friends))) &&
                    occupied(u,&units[k],nx,ny)) blocked=1;
            if (blocked) { if (nx==tx && ny==ty) stopped=1; continue; }
            steps[i][0]=dx[d]; steps[i][1]=dy[d]; x=nx; y=ny; heading=d; break;
        }
        unsigned mask, tile=tile_at(m,u->x,u->y,grid(u->x,u->y,x,y,1,&mask));
        int cost=movement==2 || (!u->infantry && btp_vehicle_kind(u->record)==3 && tile<16) || tile>=64 || !(tile&mask) ? 1 : (tile&240u)==32 ? 3 : 2;
        points-=cost;
    }
}
void btp_combat_plan(const BtpMap *m, unsigned gate, const BtpCombatUnit *u,
    const BtpCombatUnit *other, int tx, int ty, unsigned movement, int computer, int8_t steps[12][2])
{
    plan_points(m,gate,u,other,tx,ty,movement,computer,btp_combat_points(u,movement),NULL,NULL,0,NULL,0,0,1,NULL,steps);
}
static void route(const BtpMap *m,unsigned gate,const BtpCombatState *c,const BtpState *s,int8_t steps[12][2])
{
    unsigned actor=c->active_unit,enemy=c->friends ? c->friends : 1u;
    plan_points(m,gate,&c->unit[actor],&c->unit[enemy],c->goal_x,c->goal_y,c->movement,0,
        btp_combat_points(&c->unit[actor],c->movement),c->waypoint_x,c->waypoint_y,c->waypoint_count,
        c->friends ? c->unit : NULL,c->friends ? c->count : 0,actor,c->friends ? c->friends : 1u,s,steps);
}
void btp_combat_route(const BtpMap *m,unsigned gate,const BtpCombatState *c,int8_t steps[12][2]) { route(m,gate,c,NULL,steps); }
void btp_combat_route_state(const BtpMap *m,unsigned gate,const BtpState *s,int8_t steps[12][2]) { route(m,gate,&s->combat,s,steps); }
static unsigned movement_gate(const BtpState *s)
{
    /* 09B8's mounted arena view sets the original terrain threshold to 139.
       The personal exploration threshold would incorrectly block its exit. */
    return s->campaign.encounter==4 ? 139u : s->gate;
}
void btp_combat_plan_actor(const BtpMap *map,const BtpState *s,unsigned actor,
    int x,int y,unsigned movement,int8_t steps[12][2])
{
    const BtpCombatState *c=&s->combat;const BtpCombatUnit *u=&c->unit[actor];
    plan_points(map,movement_gate(s),u,NULL,x,y,movement,1,btp_combat_points(u,movement),
        NULL,NULL,0,c->unit,c->count,actor,c->friends ? c->friends : 1u,s,steps);
}
void btp_combat_map(const BtpResources *r,const BtpState *s,BtpMap *m)
{
    const BtpScene *scene=btp_scene(r,s);if (scene) { *m=scene->rules;return; }
    if (s->campaign.invasion) {
        *m=(BtpMap){.width=128,.height=128};
        for (int y=0;y<128;++y) for (int x=0;x<128;++x) {
            /* The Citadel is an overlay on the world. Switch the actual
               collision tiles together with DESTRUCT, while still fighting. */
            unsigned tile=x>=32 && x<96 && y>=32 && y<96 ? btp_map_tile(btp_active_map(r,s),x-32,y-32) : btp_world_tile(r,s,s->campaign.battle_x/2+x,s->campaign.battle_y/2+y);
            m->tiles[y*128+x]=(uint8_t)tile;
        }
        return;
    }
    if (!s->campaign.encounter) { *m=*btp_active_map(r,s);return; }
    *m=(BtpMap){.width=64,.height=64};
    for (int y=0;y<64;++y) for (int x=0;x<64;++x)
        m->tiles[y*64+x]=(uint8_t)btp_world_tile(r,s,s->campaign.battle_x/2+x,s->campaign.battle_y/2+y);
}
static void store_plan(BtpCombatState *c)
{
    if (!c->friends) return;
    BtpCombatPlan *p=&c->plans[c->active_unit];
    p->movement=c->movement;p->x=c->goal_x;p->y=c->goal_y;p->active=c->goal_active;p->count=c->waypoint_count;
    memcpy(p->wx,c->waypoint_x,11);memcpy(p->wy,c->waypoint_y,11);memcpy(p->orders,c->orders,11);p->kick=c->kick_target;
}
static void load_plan(BtpCombatState *c,unsigned unit)
{
    c->active_unit=(uint8_t)unit;
    const BtpCombatPlan *p=&c->plans[unit];
    c->movement=p->movement;c->goal_x=p->x;c->goal_y=p->y;c->goal_active=p->active;c->waypoint_count=p->count;
    memcpy(c->waypoint_x,p->wx,11);memcpy(c->waypoint_y,p->wy,11);memcpy(c->orders,p->orders,11);c->kick_target=p->kick;
}
void btp_combat_select(BtpCombatState *c,unsigned unit)
{
    if (!c->friends || unit>=c->friends) return;
    store_plan(c);load_plan(c,unit);
    /* Original menu 5 retains its row across units. Infantry does not use
       that selector; a new mech list bounds it when the list is opened. */
}
unsigned btp_combat_cover(const BtpMap *m, const BtpCombatUnit *u, unsigned *terrain)
{
    unsigned tile=btp_map_tile(m,(u->x+1)/2,u->y/2), mask=(u->y&1u) ? 4u : 1u;
    *terrain=tile;
    if (tile>=48 || !(tile&mask)) return 0;
    unsigned cover=(tile&15u)==15 && ((tile&48u)==0 || (tile&48u)==32) ? 16u : 8u;
    /* Original person/robot flags are 2/4; mech footprints use 8/16. */
    return u->infantry ? cover/4u : cover;
}
static void menu(BtpCombatState *c)
{
    c->phase=BTP_COMBAT_MENU;c->selected=9;c->weapon_ui=0;
}
unsigned btp_combat_menu_count(const BtpCombatState *c)
{
    return c->unit[c->active_unit].infantry ? 8u : 10u;
}
unsigned btp_combat_menu_command(const BtpCombatState *c,unsigned row)
{
    /* Executed 103B:14C3 selects DS:3A6F or DS:3ABC by original unit ID.
       Clear Moves is distinct from the mech's Run/Jump/Kick commands. */
    static const uint8_t foot[8]={0,10,3,5,6,7,8,9};
    return row<btp_combat_menu_count(c) ? c->unit[c->active_unit].infantry ? foot[row] : row : 9u;
}
unsigned btp_combat_menu_row(const BtpCombatState *c)
{
    for (unsigned row=0;row<btp_combat_menu_count(c);++row)
        if (btp_combat_menu_command(c,row)==c->selected) return row;
    return 0;
}
int btp_combat_scan_detail(const BtpCombatState *c)
{
    return c->scan_unit<c->count && !c->unit[c->scan_unit].infantry;
}
static int scan_eligible(const BtpState *s,unsigned i)
{
    const BtpCombatState *c=&s->combat;
    unsigned friends=c->friends ? c->friends : 1u;
    int friendly=s->battle_mission.active ? btp_battle_side(s,NULL,i)!=BTP_SIDE_HOSTILE : i<friends;
    if (i>=c->count || c->unit[i].record[0]==255 || friendly!=(c->target_selected==0)) return 0;
    /* 103B:2591 and 05AB:1467 restrict on-foot/damaged-sensor enemy
       scanning to humans. Friends remain available regardless of sensors. */
    return !c->target_selected || !(c->unit[c->active_unit].infantry || c->unit[c->active_unit].record[119]==2) || c->unit[i].infantry;
}
static void notice(BtpCombatState *c,unsigned id,unsigned back);
static void scan_next(BtpState *s,unsigned after)
{
    BtpCombatState *c=&s->combat;unsigned best=BTP_COMBAT_UNITS,best_id=24;
    for (unsigned pass=0;pass<2 && best==BTP_COMBAT_UNITS;++pass)
        for (unsigned i=0;i<c->count;++i) if (scan_eligible(s,i)) {
            unsigned id=btp_combat_id(c,i);
            if ((pass || id>after) && id<best_id) { best=i;best_id=id; }
        }
    if (best==BTP_COMBAT_UNITS) { notice(c,17,BTP_COMBAT_SCAN_CHOICE);return; }
    c->scan_unit=(uint8_t)best;c->phase=BTP_COMBAT_SCAN;c->selected=0;
    if (btp_spy_unit(s,best)) s->spy_discovered=1;
}
int btp_combat_waypoint(BtpCombatState *c, unsigned x, unsigned y, unsigned movement)
{
    if (x>253 || y>255 || movement>2) return 0;
    if (c->goal_active && c->movement==movement) {
        if (c->goal_x==x && c->goal_y==y) return 1;
        for (unsigned i=0;i<c->waypoint_count;++i)
            if (c->waypoint_x[i]==x && c->waypoint_y[i]==y) return 1;
        if (c->waypoint_count==11) return 0;
        c->waypoint_x[c->waypoint_count]=(uint8_t)x;
        c->waypoint_y[c->waypoint_count++]=(uint8_t)y;
    } else {
        c->waypoint_count=0;memset(c->waypoint_x,0,11);memset(c->waypoint_y,0,11);
        c->goal_x=(uint8_t)x;c->goal_y=(uint8_t)y;c->movement=(uint8_t)movement;c->goal_active=1;
    }
    return 1;
}
static void arrived(BtpCombatState *c)
{
    if (c->waypoint_count) {
        c->goal_x=c->waypoint_x[0];c->goal_y=c->waypoint_y[0];--c->waypoint_count;
        memmove(c->waypoint_x,c->waypoint_x+1,c->waypoint_count);
        memmove(c->waypoint_y,c->waypoint_y+1,c->waypoint_count);
        c->waypoint_x[c->waypoint_count]=c->waypoint_y[c->waypoint_count]=0;
    } else { c->goal_active=0;c->movement=255; }
}
static void notice(BtpCombatState *c, unsigned id, unsigned back)
{
    c->notice=(uint8_t)id;c->notice_return=(uint8_t)back;c->phase=BTP_COMBAT_NOTICE;
}
static void weapon_list(BtpCombatState *c)
{
    unsigned count=btp_combat_weapon_count(&c->unit[c->active_unit]);
    uint16_t *fired=c->active_unit ? &c->enemy_fired[c->active_unit-1] : &c->fired;
    c->phase=BTP_COMBAT_WEAPONS;
    if (c->weapon_selected>count) c->weapon_selected=0;
    for (unsigned i=0;i<count;++i) {
        unsigned target=btp_combat_target(c,c->orders[i]);
        if ((btp_combat_weapon_type(&c->unit[c->active_unit],i)&128u) ||
            (target<c->count && c->unit[target].record[0]==255)) c->orders[i]=255;
        /* 0D43 clears the order's high bit when displaying a live target.
           Native target IDs and the original fired/disabled bits are separate. */
        if (c->orders[i]!=255) *fired&=(uint16_t)~(1u<<i);
    }
}
void btp_combat_begin(BtpState *s, const BtpResources *r)
{
    BtpCombatState *c=&s->combat;
    *c=(BtpCombatState){.phase=BTP_COMBAT_CONTROL,.selected=1,.messages=2,.graphics=1,
        .movement=255,.walk={6,12},.plan_direction={0,6},.enemy_movement=255,
        .count=2,.target_unit=1,.kick_target=255,.last_target=1};
    memset(c->orders,255,sizeof c->orders);
    memset(c->enemy_orders,255,sizeof c->enemy_orders);memset(c->enemy_modes,255,sizeof c->enemy_modes);
    memcpy(c->unit[0].record,btp_chi_mission_unit(r,BTP_MUNIT_TRAINING_LOAN_0+s->story_flags[2]),125);
    unsigned assignment=s->mission.assignment;
    c->unit[0].x=(uint8_t)btp_chi_training(r,assignment,BTP_TRAIN_START_X);
    c->unit[0].y=(uint8_t)(btp_chi_training(r,assignment,BTP_TRAIN_START_Y)-2u);c->unit[0].direction=2;
    /* 07DC:0765..07ED sets the training restriction at STATE:0090 for
       assignments 3..7. The shell assignment 2 still offers global control. */
    if (!btp_chi_training(r,assignment,BTP_TRAIN_CONTROL_PROMPT)) { c->phase=BTP_COMBAT_MESSAGES;c->selected=2; }
    unsigned count_mask=btp_chi_training(r,assignment,BTP_TRAIN_COUNT_MASK);
    /* Assignment 3 always drew a count, including when an author fixes its
       size. Other assignments draw only when explicitly made variable. */
    unsigned extra=assignment==3 || count_mask ? btp_rng_next(s->npc.rng)&count_mask : 0;
    c->count=(uint8_t)(1+(s->campaign.invasion ? btp_chi_mission(r,BTP_MIS_INVASION_ENEMY_COUNT) : btp_chi_training(r,assignment,BTP_TRAIN_ENEMY_COUNT)+extra));
    unsigned mask=btp_chi_training(r,assignment,BTP_TRAIN_SPAWN_MASK);
    unsigned x=btp_chi_training(r,assignment,BTP_TRAIN_SPAWN_X)+(btp_rng_next(s->npc.rng)&mask);
    unsigned y=btp_chi_training(r,assignment,BTP_TRAIN_SPAWN_Y)+(btp_rng_next(s->npc.rng)&mask);
    int foot=!s->campaign.invasion && btp_chi_training(r,assignment,BTP_TRAIN_INFANTRY);
    int shell=!s->campaign.invasion && btp_chi_training(r,assignment,BTP_TRAIN_SHELL);
    /* Original slot-8 onward offsets at DS:1642/164E. */
    for (unsigned i=1;i<c->count;++i) {
        BtpCombatUnit *u=&c->unit[i];u->direction=6;c->plan_direction[i]=6;c->walk[i]=12;
        u->x=(uint8_t)((shell ? btp_chi_training(r,assignment,BTP_TRAIN_SHELL_X) : x)+btp_chi_training_enemy(r,assignment,i-1,0));
        u->y=(uint8_t)(y+btp_chi_training_enemy(r,assignment,i-1,1));
        if (foot) {
            u->infantry=1;u->record[12]=8;
            for (unsigned k=4;k<=9;++k) u->record[k]=(uint8_t)(btp_rng_next(s->npc.rng)&btp_chi_training(r,assignment,BTP_TRAIN_INFANTRY_SKILL_MASK));
            u->record[1]=(uint8_t)btp_combat_dice(s->npc.rng);u->record[15]=(uint8_t)(10*u->record[1]);
            u->record[11]=(uint8_t)(btp_rng_next(s->npc.rng)%btp_chi_training(r,assignment,BTP_TRAIN_INFANTRY_WEAPONS));
        } else {
            memcpy(u->record,btp_chi_mission_unit(r,s->campaign.invasion ? BTP_MUNIT_INVASION_ENEMY_0+i-1 : btp_chi_training_unit(assignment,i-1)),125);
            if (shell) { u->record[36]=u->record[37]=0;memset(u->record+39,0,12); }
        }
    }
    if (s->campaign.invasion) {
        /* A 64-half-tile margin preserves the original packed-world escape
           bounds on all four sides without wrapping signed coordinates. */
        s->campaign.battle_x=(uint16_t)(btp_citadel_origin(s,0)-64u);s->campaign.battle_y=(uint16_t)(btp_citadel_origin(s,1)-64u);
        for (unsigned i=0;i<c->count;++i) { c->unit[i].x+=64;c->unit[i].y+=64; }
        s->x_half=c->unit[0].x;s->y_half=(uint16_t)(c->unit[0].y+2u);
    }
}
static void invasion_event(BtpState *s,const BtpResources *r)
{
    /* 103B:0F7A emits one entry from DS:3A2E per round; if combat ends,
       it drains the remaining entries before returning to TRAINING.BLD. */
    s->late.invasion_popup=(uint8_t)(2u+s->late.invasion_event);
    s->combat.phase=BTP_COMBAT_STORY;s->combat.flash=0;
    if (s->late.invasion_event==1) {
        (void)btp_rng_next(s->npc.rng); /* Forced O2 still consumes its original outtake draw. */
        (void)btp_cutscene_begin(s,r,2,4);
    }
}
static void finish(BtpState *s,const BtpResources *r)
{
    BtpCombatState *c=&s->combat;
    if (s->campaign.invasion && s->late.invasion_event<5) {
        s->late.invasion_end=1;invasion_event(s,r);return;
    }
    s->late.invasion_popup=s->late.invasion_end=0;
    s->x_half=c->unit[0].x;s->y_half=(uint16_t)(c->unit[0].y+(c->unit[0].infantry ? 0u : 2u));
    if (s->campaign.encounter) { c->phase=BTP_COMBAT_NONE;c->flash=0;return; }
    s->mission.corner=1;s->mission.idle=0;s->mission.walk=c->walk[0];
    s->mission.direction=c->unit[0].direction;c->phase=BTP_COMBAT_NONE;c->flash=0;
    /* 103B:0D6D..0DA5: training encounter argument 1 waits for a key
       after the original return-to-base message. */
    if (!s->campaign.invasion) s->mission.phase=BTP_MISSION_RETURN;
    if (s->campaign.invasion) {
        s->campaign.world_x=(uint16_t)(s->campaign.battle_x+s->x_half);
        s->campaign.world_y=(uint16_t)(s->campaign.battle_y+s->y_half);
        s->x_half=(uint16_t)(s->campaign.world_x&127u);
        s->y_half=(uint16_t)(s->campaign.world_y&127u);
    }
    if (c->lost && !s->campaign.invasion) { s->x_half=(uint16_t)btp_chi_training(r,s->mission.assignment,BTP_TRAIN_RETURN_X);s->y_half=(uint16_t)btp_chi_training(r,s->mission.assignment,BTP_TRAIN_RETURN_Y_MAX); }
}
/* The original command menu calls the same per-actor planner as a round.
   Assigning computer orders previews that actor without advancing combat. */
static void computer_plan(BtpState *s,const BtpResources *r,const BtpMap *terrain,unsigned index,int enemy_ai)
{
    BtpCombatState *c=&s->combat;unsigned friends=c->friends ? c->friends : 1u;
    int friendly=index<friends;
    if (friendly && !(c->automatic&(UINT32_C(1)<<index))) return;
    if (c->unit[index].record[0]==255) return;
    if (s->battle_mission.active && btp_battle_actor_plan(s,r,terrain,index)) return;
    /* Updated orders use explicit saved policy. Story eligibility still
       precedes planning: in particular the target shell cannot become mobile. */
    if (!c->unit[index].infantry && (friendly || (enemy_ai))) {
        BtpAiPlan plan;
        if (btp_combat_ai_plan(s,r,terrain,index,&plan)) {
            memcpy(c->path[index],plan.path,sizeof plan.path);c->plan_direction[index]=plan.direction;
            if (index) {
                memcpy(c->enemy_orders[index-1],plan.orders,12);
                if (index==1) c->enemy_movement=plan.movement;else c->enemy_modes[index-2]=plan.movement;
            } else if (!c->friends) {
                c->movement=plan.movement;memcpy(c->orders,plan.orders,11);c->kick_target=plan.orders[11];
                c->goal_active=c->waypoint_count=0;c->goal_x=plan.x;c->goal_y=plan.y;
                memset(c->waypoint_x,0,11);memset(c->waypoint_y,0,11);
            }
            if (friendly && c->friends) {
                BtpCombatPlan *p=&c->plans[index];*p=(BtpCombatPlan){.movement=plan.movement,.x=plan.x,.y=plan.y,.kick=plan.orders[11]};
                memcpy(p->orders,plan.orders,11);
            }
            return;
        }
    }
    /* 0E31:03AB: the weapon-component range scan intentionally uses the
       component value as the table index, even when ammunition is empty. */
    BtpCombatUnit enemy=c->unit[index];enemy.direction=c->plan_direction[index];
    unsigned first= friendly ? friends : 0u,last=friendly ? c->count : friends,prey=first;
    if (s->battle_mission.active) { first=0;last=c->count; }
    if (friendly || c->friends) {
        /* 0E31:0483..059E searches the actor's own class first. Mechs
           prefer enemy mechs; people prefer people, then fall back. Distance
           ties retain the lower original unit ID, including after ejections. */
        unsigned same=0;prey=BTP_COMBAT_UNITS;
        for (unsigned i=first;i<last;++i) if (btp_battle_hostile(s,index,i) && c->unit[i].record[0]!=255 && c->unit[i].infantry==enemy.infantry &&
            !(!friendly && c->unit[i].infantry && btp_spy_unit(s,i)) &&
            !(s->campaign.encounter==4 && s->yard.rental && !s->story_flags[35] && btp_combat_id(c,i)==13)) same=1;
        for (unsigned i=first;i<last;++i) {
            if (!btp_battle_hostile(s,index,i) || c->unit[i].record[0]==255 || (same && c->unit[i].infantry!=enemy.infantry) ||
                (!friendly && c->unit[i].infantry && btp_spy_unit(s,i)) ||
                (s->campaign.encounter==4 && s->yard.rental && !s->story_flags[35] && btp_combat_id(c,i)==13)) continue;
            unsigned distance=btp_combat_distance(enemy.x,enemy.y,c->unit[i].x,c->unit[i].y);
            if (prey==BTP_COMBAT_UNITS || distance<btp_combat_distance(enemy.x,enemy.y,c->unit[prey].x,c->unit[prey].y) ||
                (distance==btp_combat_distance(enemy.x,enemy.y,c->unit[prey].x,c->unit[prey].y) && btp_combat_id(c,i)<btp_combat_id(c,prey))) prey=i;
        }
        if (prey==BTP_COMBAT_UNITS) return;
    }
    int ex=enemy.x,ey=enemy.y,px=c->unit[prey].x,py=c->unit[prey].y,goal_x=ex,goal_y=ey;
    unsigned distance=btp_combat_distance(ex,ey,px,py),preferred=255;
    int visible=btp_combat_scene_los(r,s,terrain,ex,ey,px,py)>0;
    for (unsigned i=51;i<86;++i) {
        unsigned component=enemy.record[i];
        if (component>=16 && component<=32) {
            unsigned value=(r->combat.weapons[component][14]&224u)>>3;
            if (value<preferred) preferred=value;
        }
    }
    if (preferred==255) preferred=0;
    if (enemy.infantry) preferred=r->combat.weapons[enemy.record[11]][14]>>5;
    /* 0E31:0955..097C only cancels the move for vehicle against vehicle.
       A vehicle near a person retains its facing and trampling route. */
    int close=!enemy.infantry && !c->unit[prey].infantry && visible && abs(px-ex)<=3 && abs(py-ey)<2;
    uint8_t first_movement=255;
    uint8_t *movement=index==0 && c->friends ? &first_movement : index==0 ? &c->movement : index==1 ? &c->enemy_movement : &c->enemy_modes[index-2];*movement=255;
    if ((enemy_ai || friendly) && close) {
        c->plan_direction[index]=(uint8_t)btp_combat_direction(ex,ey,px,py);
        c->unit[index].direction=c->fallback[index];
    } else if ((enemy_ai || friendly) && (!visible || !preferred || distance>preferred || enemy.infantry)) {
        int tx=px,ty=py;
        /* 0E31:06DF..07A4 retreats a person from a vehicle. Against
           another person it keeps the target position and approaches. */
        if (enemy.infantry && !c->unit[prey].infantry) { tx=ex+((px>ex)-(px<ex))*-6;ty=ey+((py>ey)-(py<ey))*-6; }
        if (visible && preferred && (!enemy.infantry || c->unit[prey].infantry)) {
            int sx=(tx>ex)-(tx<ex),sy=(ty>ey)-(ty<ey);
            if (distance>preferred) { tx=ex+sx*(int)(distance-preferred);ty=ey+sy*(int)(distance-preferred); }
            else { tx=ex;ty=ey; }
        }
        goal_x=tx;goal_y=ty;
        *movement=(uint8_t)(enemy.heat || enemy.infantry ? 0 : 1);
        /* 0E31:046F normalizes robot IDs before 103B:2474. IDs 20/21
           cross its threshold and take six points; IDs 16..19 take three. */
        int points=btp_combat_points(&enemy,*movement);
        if (!friendly && enemy.infantry && !s->battle_mission.active) {
            unsigned id=btp_combat_id(c,index);
            if (id>=20) points=6;
            else {
                BtpCombatUnit alias={.infantry=1};
                /* Original enemy IDs 16..19 accidentally consult owned
                   character slots 4..7. Preserve that alias, even if inactive. */
                if (s->party.enabled && id>=16) memcpy(alias.record,s->party.people[id-12],17);
                points=btp_combat_points(&alias,*movement);
            }
        }
        plan_points(terrain,movement_gate(s),&enemy,&c->unit[prey],tx,ty,*movement,1,points,NULL,NULL,0,
            s->mission.assignment==5 || c->friends ? c->unit : NULL,s->mission.assignment==5 || c->friends ? c->count : 0,index,friends,s,c->path[index]);
    }
    uint8_t automatic_orders[12];uint8_t *orders=index ? c->enemy_orders[index-1] : automatic_orders;
    memset(orders,255,12);
    if (friendly || enemy_ai || c->friends) {
        for (unsigned w=0;w<btp_combat_weapon_count(&enemy) && w<10;++w)
            if (btp_combat_weapon(&enemy,w)<33 && enemy.heat<30) orders[w]=(uint8_t)btp_combat_id(c,prey);
        if (!enemy.infantry && enemy.heat<30) orders[11]=(uint8_t)btp_combat_id(c,prey);
    }
    if (!index && !c->friends) {
        memcpy(c->orders,orders,11);c->kick_target=orders[11];c->goal_active=0;c->waypoint_count=0;
        int max_x=s->campaign.invasion ? 253 : 125,max_y=s->campaign.invasion ? 255 : 127;
        c->goal_x=(uint8_t)(goal_x<0 ? 0 : goal_x>max_x ? max_x : goal_x);
        c->goal_y=(uint8_t)(goal_y<0 ? 0 : goal_y>max_y ? max_y : goal_y);
        memset(c->waypoint_x,0,11);memset(c->waypoint_y,0,11);
    }
    if (friendly && c->friends) {
        BtpCombatPlan *p=&c->plans[index];p->movement=*movement;p->active=0;p->count=0;p->kick=orders[11];memcpy(p->orders,orders,11);
        int max_x=s->campaign.invasion ? 253 : 125,max_y=s->campaign.invasion ? 255 : 127;
        p->x=(uint8_t)(goal_x<0 ? 0 : goal_x>max_x ? max_x : goal_x);
        p->y=(uint8_t)(goal_y<0 ? 0 : goal_y>max_y ? max_y : goal_y);
        memset(p->wx,0,11);memset(p->wy,0,11);
    }
}
static void begin_round(BtpState *s, const BtpResources *r, int enemy_ai)
{
    if (s->battle_mission.active && s->battle_mission.stage!=1) {
        if (s->combat.round==65535) { s->battle_mission.outcome=2;s->combat.lost=1;finish(s,r);return; }
        s->battle_mission.stage=1;s->battle_mission.round=++s->combat.round;
        btp_battle_signal(s,btp_adventure(r),BTP_HOOK_ROUND_START,BTP_COMBAT_GROUPS);return;
    }
    s->battle_mission.stage=0;
    BtpMap terrain;btp_combat_map(r,s,&terrain);
    BtpCombatState *c=&s->combat;
    memset(c->path,0,sizeof c->path);
    for (unsigned i=0;i<c->count;++i) memset(c->path[i],2,sizeof c->path[i]);
    store_plan(c);
    unsigned friends=c->friends ? c->friends : 1u,active=c->active_unit;
    if (c->friends) {
        for (unsigned i=0;i<friends;++i) {
            btp_combat_select(c,i);
            if (c->goal_active) btp_combat_route_state(&terrain,movement_gate(s),s,c->path[i]);
            if (i) {
                memcpy(c->enemy_orders[i-1],c->orders,11);c->enemy_orders[i-1][11]=c->kick_target;
                if (i==1) c->enemy_movement=c->movement;else c->enemy_modes[i-2]=c->movement;
            }
        }
        btp_combat_select(c,active);
    } else if (c->goal_active) btp_combat_route_state(&terrain,movement_gate(s),s,c->path[0]);
    for (unsigned index=0;index<c->count;++index) computer_plan(s,r,&terrain,index,enemy_ai);
    /* Computer orders replace the selected unit's plan too. Refresh its
       editor before a later selection can write old orders back over it. */
    if (c->friends) load_plan(c,active);
    memset(c->moved,0,sizeof c->moved);memset(c->path_index,0,sizeof c->path_index);
    memset(c->enemy_fired,0,sizeof c->enemy_fired);
    c->fired=0;c->step=0;c->delay=0;c->last_event=0;c->flash=0;c->phase=BTP_COMBAT_ROUND;
    btp_effects_begin_round(s);
    if (!s->battle_mission.active) ++c->round;
}
unsigned btp_combat_walk_frame(unsigned frame,unsigned previous,unsigned direction,int infantry)
{
    static const uint8_t frames[8][4]={{0,1,2,3},{4,5,6,7},{6,7,4,5},{5,6,7,4},
        {8,9,10,11},{12,13,14,15},{15,12,13,14},{14,15,12,13}};
    if (direction>7) return frame;
    unsigned next=0;
    if (direction==previous) for (unsigned i=0;i<4;++i)
        if (frames[direction][i]==frame) next=(i+1u)%4u;
    return infantry ? btp_walk_next((uint8_t)frame,(uint8_t)previous,(uint8_t)direction) : frames[direction][next];
}
static void mark(BtpState *s,unsigned sprite,int x,int y);
static void advance(BtpState *s,const BtpResources *r, unsigned index)
{
    BtpCombatState *c=&s->combat;
    BtpCombatUnit *u=&c->unit[index];unsigned p=c->path_index[index];
    if (p>=12 || u->record[0]==255) return;
    int mx=c->path[index][p][0], my=c->path[index][p][1];
    if (mx==2 || my==2) {
        unsigned friends=c->friends ? c->friends : 1u;
        int arrived=c->friends ? u->x==c->plans[index].x && u->y==c->plans[index].y :
            u->x==c->goal_x && u->y==c->goal_y;
        if (index<friends && (c->automatic&(1u<<index)) && arrived) {
            /* 12E8 clears a computer move when it reaches the end marker.
               Later shots and cooling then use stationary mode (FF).
               Enemy AI retains its command mode through wave cleanup. */
            if (index<c->friends) c->plans[index].movement=255;
            if (index==c->active_unit) c->movement=255;
            if (index==1) c->enemy_movement=255;
            else if (index>1) c->enemy_modes[index-2]=255;
        }
        return;
    }
    if (!mx && !my) return;
    int x=u->x+mx,y=u->y+my;
    for (unsigned i=0;i<c->count;++i) if (i!=index && occupied(u,&c->unit[i],x,y) &&
        !(!u->infantry && c->unit[i].infantry && btp_battle_hostile(s,index,i))) return;
    if (!u->infantry) for (unsigned i=0;i<c->count;++i)
        if (c->unit[i].infantry && btp_battle_hostile(s,index,i) && occupied(u,&c->unit[i],x,y)) {
            /* Original movement blocks friendly soldiers but crushes enemies
               under a vehicle's two-step footprint, without an RNG draw. */
            btp_effects_crush(s,index,i);c->unit[i].record[15]=0;
            mark(s,126,c->unit[i].x,c->unit[i].y);
            if (s->campaign.encounter) btp_campaign_destroy_resources(s,i,r);
            else { c->unit[i].record[0]=255;c->unit[i].x=c->unit[i].y=127; }
        }
    unsigned direction=btp_combat_direction(u->x,u->y,x,y);
    c->walk[index]=(uint8_t)btp_combat_walk_frame(c->walk[index],u->direction,direction,u->infantry);
    u->direction=(uint8_t)direction;c->plan_direction[index]=(uint8_t)direction;
    u->x=(uint8_t)x;u->y=(uint8_t)y;++c->moved[index];++c->path_index[index];
}
static void mark(BtpState *s,unsigned sprite,int x,int y)
{
    int ox=s->campaign.invasion || s->campaign.encounter ? s->campaign.battle_x : (int)btp_citadel_origin(s,0);
    int oy=s->campaign.invasion || s->campaign.encounter ? s->campaign.battle_y : (int)btp_citadel_origin(s,1);
    btp_world_mark(s,sprite,ox+x,oy+y);
}
void btp_combat_ignite(BtpState *s, const BtpCombatUnit *target)
{
    /* 12E8:1E46 rolls 2d6; values outside 5..9 add sprite 124 through
       103B:27C9. The original 64-entry ring survives encounters. It does
       not replace the map's terrain/LOS grid or implement spreading fire. */
    unsigned roll=btp_combat_dice(s->npc.rng);
    if (roll>=5 && roll<=9) return;
    mark(s,124,(int)target->x-(target->infantry ? 1 : 0),
        (int)target->y-(target->infantry ? 0 : 1));
}
static void end_round(BtpState *s,const BtpResources *r)
{
    BtpCombatState *c=&s->combat;
    unsigned remaining=0;
    if (s->battle_mission.active && s->battle_mission.stage==2) goto resolved_hooks;
    if (btp_spy_begin(s)) return;
    for (unsigned i=c->friends ? c->friends : 1u;i<c->count;++i) remaining+=c->unit[i].record[0]!=255;
    BtpMap map;btp_combat_map(r,s,&map);
    for (unsigned i=0;i<c->count;++i) if (c->unit[i].record[0]!=255) {
        unsigned terrain,mode=i==0 ? c->friends ? c->plans[0].movement : c->movement : i==1 ? c->enemy_movement : c->enemy_modes[i-2];
        (void)btp_combat_cover(&map,&c->unit[i],&terrain);
        btp_combat_cool(&c->unit[i],mode==255 ? -1 : (int)mode,c->moved[i],terrain);
    }
    if (s->battle_mission.active) {
        s->battle_mission.stage=2;btp_battle_observe(s,btp_adventure(r));
        btp_battle_signal(s,btp_adventure(r),BTP_HOOK_ROUND_END,BTP_COMBAT_GROUPS);return;
    }
resolved_hooks:
    if (s->battle_mission.active) { s->battle_mission.stage=0;remaining=btp_battle_hostiles(s); }
    /* 12E8 completes heat accounting before 103B checks victory. */
    if (s->campaign.encounter==4 && !s->story_flags[35] && c->unit[0].record[0]==255) {
        /* 103B:0F13..0F31 runs after 12E8's cooling pass, including a
           defeated arena match with a surviving ejected pilot. */
        c->lost=1;finish(s,r);return;
    }
    if (!remaining && !(s->battle_mission.active && btp_adventure(r)->battles[s->battle_mission.encounter].scripted)) { c->won=1;finish(s,r);return; }
    if (!c->goal_active) c->movement=255;
    c->delay=0;c->flash=0;menu(c);
    if (s->campaign.invasion && s->late.invasion_event<5) invasion_event(s,r);
}
unsigned btp_combat_delay_ticks(unsigned speed)
{
    /* 12E8:0D76 calls 0E31:1DCC after an attack, not after a movement
       microstep. Convert its 12*selection retraces to 32 ms ticks; the
       report's first displayed tick supplies one period. Speed five waits
       for a key at that same attack boundary. */
    return speed && speed<5 ? (12u*speed*100u+223u)/224u-1u : 0u;
}
static void round_tick(BtpState *s, const BtpResources *r, int enemy_ai)
{
    BtpCombatState *c=&s->combat;
    uint8_t moved_before[BTP_COMBAT_UNITS];memcpy(moved_before,c->moved,sizeof moved_before);
    /* The original movement loop (12E8:1002..1286) has no speed wait.
       Keep one visible movement microstep per host tick. */
    c->flash=0;
    advance(s,r,0);
    /* Ignore old in-progress target paths too: loading an earlier checkpoint
       must not reanimate the training shell. */
    if (enemy_ai) for (unsigned i=1;i<c->count;++i) advance(s,r,i);
    /* The original redraws movement only when a visible unit advances.
       Empty microsteps and offscreen opponents must not accelerate fire. */
    for (unsigned i=0;i<c->count;++i) if (moved_before[i]!=c->moved[i] &&
        btp_combat_visible(c->unit[i].x,c->unit[i].y,c->unit[i].infantry,
            c->unit[c->active_unit].x,c->unit[c->active_unit].y)) {
        int ox=s->campaign.encounter || s->campaign.invasion ? s->campaign.battle_x : (int)btp_citadel_origin(s,0);
        int oy=s->campaign.encounter || s->campaign.invasion ? s->campaign.battle_y : (int)btp_citadel_origin(s,1);
        btp_world_animate_marks(s,ox+c->unit[c->active_unit].x,oy+c->unit[c->active_unit].y);break;
    }
    BtpMap map;btp_combat_map(r,s,&map);
    unsigned terrain[BTP_COMBAT_UNITS]={0};
    for (unsigned i=0;i<c->count;++i) c->unit[i].cover=(uint8_t)btp_combat_cover(&map,&c->unit[i],&terrain[i]);
    for (unsigned ordinal=0;ordinal<(c->friends ? 24u : c->count);++ordinal) {
        unsigned actor=c->friends ? btp_combat_target(c,ordinal) : ordinal;
        if (actor>=c->count) continue;
        if (c->unit[actor].record[0]==255 || (actor && (!enemy_ai))) continue;
        for (unsigned i=0;i<12;++i) {
            uint8_t *order=actor ? &c->enemy_orders[actor-1][i] : c->friends ? i==11 ? &c->plans[0].kick : &c->plans[0].orders[i] : i==11 ? &c->kick_target : &c->orders[i];
            uint16_t *fired=actor ? &c->enemy_fired[actor-1] : &c->fired;
            if (*order==255 || (*fired&(1u<<i))) continue;
            unsigned target=btp_combat_target(c,*order);
            if (target>=c->count || c->unit[target].record[0]==255) { *order=255;continue; }
            if (s->battle_mission.active && !btp_battle_hostile(s,actor,target)) { *order=255;continue; }
            BtpCombatUnit *attacker=&c->unit[actor],*enemy=&c->unit[target];
            unsigned w=i==11 ? 32 : btp_combat_weapon(attacker,i);
            if (w>=33 || (i==11 && !btp_combat_can_kick(attacker))) { *order=255;continue; }
            if (attacker->heat>=30 || btp_combat_mount_range(&r->combat,btp_active_combat_profile(s,r),attacker,enemy,i,NULL)>=3) continue;
            /* 0E31:1BFE returns visible immediately for E48E and unit 13.
               The arena alarm clears E48E; ordinary shots use the ray. */
            int los=s->campaign.encounter==4 && s->yard.rental && !s->story_flags[35] && btp_combat_id(c,target)==13 ? 1 :
                btp_combat_scene_los(r,s,&map,attacker->x,attacker->y,enemy->x,enemy->y);
            if (!los) { if (!c->flash) c->last_event=3;continue; }
            if (los<0) { if (!c->flash) c->last_event=4;continue; }
            int ignition=enemy->cover && terrain[target]>=16 && terrain[target]<=63 &&
                ((w>=16 && w<=18) || w==11);
            int movement=actor ? (actor==1 ? c->enemy_movement : c->enemy_modes[actor-2]) : c->friends ? (c->plans[0].active || (c->automatic&1u)) ? c->plans[0].movement : 255 : (c->goal_active || (c->automatic&1u)) ? c->movement : 255;
            if (!btp_combat_ai_fire(s,r,&map,actor,target,i,movement==255 ? -1 : movement)) continue;
            unsigned skill=actor ? 0u : s->mech_skills[i==11 ? 1 : 0];
            /* 12E8:03B5 / 071B also use an enemy vehicle's pilot slot in
               C614's skill table. Loan opponents commonly alias Jason. */
            if (s->party.enabled && !attacker->infantry && attacker->record[121]<8)
                skill=s->party.people[attacker->record[121]][i==11 ? 8 : 7];
            c->shot=btp_combat_attack_profile(attacker,enemy,&r->combat,i,movement==255 ? -1 : movement,c->moved[target],
                skill,btp_combat_id(c,actor),s->explored,s->npc.rng,btp_active_combat_profile(s,r));
            if (ignition && !c->shot.hit) btp_combat_ignite(s,enemy);
            c->last_attacker=(uint8_t)actor;c->last_target=(uint8_t)target;
            c->last_weapon=(uint8_t)i;c->last_event=(uint8_t)(c->shot.hit ? 1 : 2);
            *fired|=(uint16_t)(1u<<i);c->flash=c->graphics && c->last_event<=2 ? 3 : 0;
            unsigned queued=s->effects.count;
            btp_effects_shot(s,actor,target,w);
            const BtpAuthoredWeapon *definition=attacker->infantry ? NULL : btp_authored_weapon(r->combat.definitions,attacker->record,i);
            if (definition && s->effects.count>queued) {
                /* Keep the actual authored weapon in queued text even when
                   another mount shares its animation/sound behavior. */
                s->effects.text[queued].authored=1;
                s->effects.text[queued].content_weapon=(uint8_t)(definition-r->combat.definitions->weapons);
            }
            if (c->graphics) {
                unsigned kind=0;
                if (c->shot.hit && !enemy->infantry && (w==10 || w==11)) kind=1;
                if (c->shot.hit && w>=15 && w<=18 && !attacker->infantry)
                    kind=actor==0 ? s->story_flags[2] ? 7u : 4u : target==0 && s->story_flags[2] ? 3u : 0u;
                if (kind) {
                    if (btp_outtake_roll(s,kind,0)) s->effects.outtakes[s->effects.count-1u][0]=(uint8_t)kind;
                }
                if (c->shot.toppled) {
                    if (btp_outtake_roll(s,16,0)) s->effects.outtakes[s->effects.count-1u][1]=16;
                }
            }
            if (c->shot.destroyed) {
                btp_yard_alarm(s,r,target);
                /* 12E8:1B7F / 1C6E preserve the original corpse/wreck artwork. */
                if (!(s->campaign.encounter==4 && btp_combat_id(c,target)==13))
                    mark(s,enemy->infantry ? 126u : 128u+(target==0 && s->story_flags[2]!=0),
                    (int)enemy->x-(enemy->infantry ? 0 : 1),
                    (int)enemy->y-(enemy->infantry ? 0 : 1));
                if (s->campaign.encounter) btp_campaign_destroy_resources(s,target,r);
                else {
                    enemy->record[0]=255;
                    if (target || !s->campaign.invasion) enemy->x=enemy->y=127;
                    if (!target) { s->effects.pending=2;return; }
                }
                /* The original finishes every actor's attacks in this
                   microstep before reacting to its cleared continue flag. */
                if (s->effects.pending==2 && !c->friends) return;
                /* 103B checks victory after the full 12E8 wave. Remaining
                   movement orders still execute when the last enemy dies. */
            }
            break; /* One attack per unit per microstep, including Kick. */
        }
    }
    if (c->friends) {
        unsigned active=c->active_unit;
        for (unsigned i=0;i<c->friends;++i) { btp_combat_select(c,i);if (c->goal_active && c->unit[i].x==c->goal_x && c->unit[i].y==c->goal_y) arrived(c); }
        btp_combat_select(c,active);
    } else if (c->goal_active && c->unit[0].x==c->goal_x && c->unit[0].y==c->goal_y) arrived(c);
    s->x_half=c->unit[0].x;s->y_half=(uint16_t)(c->unit[0].y+(c->unit[0].infantry ? 0u : 2u));
    /* A campaign encounter has no training mission. Keep its gait in the
       campaign record so movement does not create an unsaveable mission. */
    if (s->campaign.encounter) {
        s->campaign.mech_walk=c->walk[0];s->campaign.mech_direction=c->unit[0].direction;
    } else {
        s->mission.walk=c->walk[0];s->mission.direction=c->unit[0].direction;
    }
    if ((s->campaign.invasion && btp_chi_mission(r,BTP_MIS_INVASION_ESCAPE) && (c->unit[0].x<btp_chi_mission(r,BTP_MIS_INVASION_ESCAPE_MIN) || c->unit[0].x>=btp_chi_mission(r,BTP_MIS_INVASION_ESCAPE_MAX) || c->unit[0].y<btp_chi_mission(r,BTP_MIS_INVASION_ESCAPE_MIN) || c->unit[0].y>=btp_chi_mission(r,BTP_MIS_INVASION_ESCAPE_MAX))) ||
        /* 103B:0CCE accepts the original arena escape band only after the
           special arena target has triggered D32F. */
        (s->campaign.encounter==4 && s->story_flags[35] &&
         (int)s->campaign.battle_x+c->unit[0].x>(int)btp_chi_mission(r,BTP_MIS_ARENA_ESCAPE_MIN)+btp_chi_map_offset(r,2,0) && (int)s->campaign.battle_x+c->unit[0].x<(int)btp_chi_mission(r,BTP_MIS_ARENA_ESCAPE_MAX)+btp_chi_map_offset(r,2,0))) {
        if (s->effects.count || s->presentation.count || s->audio.sound_count) s->effects.pending=3;
        else { c->fled=1;finish(s,r); }
        return;
    }
    if (++c->step==12 && !s->effects.count) end_round(s,r);
}
static void combat_tick(BtpState *s, const BtpResources *r, BtpAction a, int enemy_ai)
{
    BtpCombatState *c=&s->combat;
    /* Space selects the highlighted command on every held combat page,
       including movement confirmation. Only a running wave treats it as
       the interrupt key; reopening an already open menu loses the choice. */
    if (a==BTP_OPEN_MENU) {
        if (c->phase==BTP_COMBAT_ROUND) {
            /* 103B:100D..102E preserves individual computer assignments. */
            c->paused=1;c->auto_run=0;
            if (s->menu.speed==5) c->delay=0; /* Space also acknowledges a held attack. */
            return;
        }
        a=BTP_ACCEPT;
    }
    if (c->phase==BTP_COMBAT_OFFER || c->phase==BTP_COMBAT_AVOID) {
        if (c->phase==BTP_COMBAT_OFFER && (a==BTP_UP || a==BTP_DOWN || a==BTP_LEFT || a==BTP_RIGHT)) c->selected^=1u;
        if (a==BTP_ACCEPT || a==BTP_OPEN_MENU) {
            if (c->phase==BTP_COMBAT_OFFER && c->selected) {
                if (btp_rng_next(s->npc.rng)&btp_chi_mission(r,BTP_MIS_ENCOUNTER_AVOID_MASK)) { btp_campaign_avoid(s);return; }
                c->phase=BTP_COMBAT_AVOID;return;
            }
            c->phase=BTP_COMBAT_CONTROL;c->selected=1;
        }
        return;
    }
    if (c->phase==BTP_COMBAT_STORY) {
        if (a==BTP_ACCEPT || a==BTP_CANCEL || a==BTP_OPEN_MENU) {
            if (s->late.invasion_popup>1) ++s->late.invasion_event;
            s->late.invasion_popup=0;
            if (s->late.invasion_end) finish(s,r);else menu(c);
        }
        return;
    }
    if (s->presentation.count) {
        if (s->audio.sound_count) return;
        unsigned kind=s->presentation.kinds[0];--s->presentation.count;
        memmove(s->presentation.kinds,s->presentation.kinds+1,s->presentation.count);
        s->presentation.kinds[s->presentation.count]=0;
        (void)btp_cutscene_begin(s,r,kind,3);return;
    }
    if (s->audio.sound_count) return;
    /* Apply pacing after each completed report/outtake, before another
       queued actor or movement can advance. The same saved delay byte also
       finishes a wait restored from an earlier executable. */
    if (c->phase==BTP_COMBAT_ROUND && c->delay) {
        if (s->menu.speed==5) { if (a!=BTP_IDLE) c->delay=0; }
        else { --c->delay;if (c->flash) --c->flash; }
        return;
    }
    if (s->effects.count) { btp_effects_tick(s,r);return; }
    if (c->phase==BTP_COMBAT_SPY) {
        if (a==BTP_ACCEPT || a==BTP_CANCEL || a==BTP_OPEN_MENU) {
            btp_spy_combat_finish(s);
            if (s->aftermath.eject) btp_campaign_eject(s);
            end_round(s,r);
        }
        return;
    }
    if (s->campaign.encounter==4 && s->yard.alarm==1 && c->phase==BTP_COMBAT_ROUND) {
        s->yard.alarm=2;c->flash=0;notice(c,7,BTP_COMBAT_ROUND);return;
    }
    if (s->aftermath.eject) btp_campaign_eject(s);
    if (s->effects.pending) {
        c->won=(uint8_t)(s->effects.pending==1);c->lost=(uint8_t)(s->effects.pending==2);
        c->fled=(uint8_t)(s->effects.pending==3);
        s->effects.pending=0;finish(s,r);return;
    }
    if (s->battle_mission.active && s->battle_mission.outcome) {
        unsigned outcome=s->battle_mission.outcome;
        c->won=(uint8_t)(outcome==1);c->lost=(uint8_t)(outcome==2);c->fled=(uint8_t)(outcome==3);
        finish(s,r);return;
    }
    if (s->battle_mission.active && s->battle_mission.stage==1) { begin_round(s,r,enemy_ai);return; }
    if (s->campaign.encounter==4 && c->phase==BTP_COMBAT_MENU && !s->story_flags[35]) {
        /* Resume older saves held at the former arena dead end. No attack
           or new round is needed to complete an already-decided match. */
        unsigned opponent=btp_combat_target(c,12),spectator=btp_combat_target(c,13);
        if (opponent<c->count && c->unit[opponent].record[0]==255) {
            if (s->yard.rental && spectator<c->count) c->unit[spectator].record[0]=255;
            end_round(s,r);return;
        }
        if (c->unit[0].record[0]==255) { end_round(s,r);return; }
    }
    /* A shot on the twelfth microstep must finish its presentation before
       cleanup returns to the command menu. This state is also saveable. */
    if (c->phase==BTP_COMBAT_ROUND && c->step==12) { end_round(s,r);return; }
    if (c->phase==BTP_COMBAT_MENU && c->auto_run && !c->paused && a==BTP_IDLE) { begin_round(s,r,enemy_ai);return; }
    if (c->phase==BTP_COMBAT_PICK) {
        if (a==BTP_UP || a==BTP_LEFT) c->scan_unit=(uint8_t)((c->scan_unit+c->friends-1u)%c->friends);
        if (a==BTP_DOWN || a==BTP_RIGHT) c->scan_unit=(uint8_t)((c->scan_unit+1u)%c->friends);
        if (a==BTP_ACCEPT && c->unit[c->scan_unit].record[0]!=255) {
            btp_combat_select(c,c->scan_unit);menu(c);
        }
        if (a==BTP_CANCEL) menu(c);
        return;
    }
    unsigned count=btp_combat_weapon_count(&c->unit[c->active_unit]);
    if (c->phase==BTP_COMBAT_ROUND) {
        round_tick(s,r,enemy_ai);
        return;
    }
    if (c->phase==BTP_COMBAT_NOTICE) {
        if (a==BTP_ACCEPT || a==BTP_CANCEL || ((c->notice>=15 || c->notice==3) && a!=BTP_IDLE)) {
            if (c->notice==7) { s->yard.alarm=3;notice(c,8,BTP_COMBAT_ROUND); }
            else if (c->notice==15 || c->notice==16) { c->notice=c->notice_return=0;scan_next(s,24); }
            else {
                if (c->notice==8) s->yard.alarm=0;
                if (c->notice==18 || c->notice==19) c->weapon_ui|=1u;
                if (c->notice==20) {
                    /* Shutdown ORs 80h into all twelve orders after the key
                       wait. Retain their targets, including the kick order. */
                    uint16_t *fired=c->active_unit ? &c->enemy_fired[c->active_unit-1] : &c->fired;
                    for (unsigned i=0;i<12;++i)
                        if ((i==11 ? c->kick_target : c->orders[i])!=255) *fired|=(uint16_t)(1u<<i);
                }
                int damaged_sensors=c->notice==21;
                c->phase=c->notice_return;c->notice=c->notice_return=0;
                if (damaged_sensors) weapon_list(c);
            }
        }
        return;
    }
    if (c->phase==BTP_COMBAT_REPLACE) {
        if (a==BTP_LEFT || a==BTP_RIGHT || a==BTP_UP || a==BTP_DOWN) c->target_selected^=1u;
        if (a==BTP_CANCEL || (a==BTP_ACCEPT && c->target_selected)) menu(c);
        else if (a==BTP_ACCEPT) {
            c->goal_active=0;c->movement=255;c->waypoint_count=0;
            memset(c->waypoint_x,0,11);memset(c->waypoint_y,0,11);
            c->phase=BTP_COMBAT_MOVE;c->cursor_x=c->unit[c->active_unit].x;c->cursor_y=c->unit[c->active_unit].y;
        }
        return;
    }
    if (c->phase==BTP_COMBAT_MOVE) {
        if (btp_action_moves(a)) {
            int x=c->cursor_x+btp_action_dx(a), y=c->cursor_y+btp_action_dy(a);
            const BtpScene *scene=btp_scene(r,s);
            int width=scene ? 2*scene->visual.width : s->campaign.invasion ? 256 : 2*r->map.width;
            int height=scene ? 2*scene->visual.height : s->campaign.invasion ? 256 : 2*r->map.height;
            if (x>=0 && x<width-2 && y>=0 && y<height-2) { c->cursor_x=(uint8_t)x;c->cursor_y=(uint8_t)y; }
        }
        if (a==BTP_ACCEPT) {
            if (!btp_combat_waypoint(c,c->cursor_x,c->cursor_y,c->selected)) notice(c,4,BTP_COMBAT_MENU);
            else menu(c);
        }
        if (a==BTP_CANCEL) menu(c);
        return;
    }
    if (c->phase==BTP_COMBAT_SCAN_DETAIL) {
        if (a==BTP_ACCEPT || a==BTP_CANCEL || a==BTP_OPEN_MENU) { c->phase=BTP_COMBAT_SCAN;c->selected=0; }
        return;
    }
    if (c->phase==BTP_COMBAT_SCAN_CHOICE) {
        if (a==BTP_UP || a==BTP_LEFT) c->selected=(uint8_t)((c->selected+2u)%3u);
        if (a==BTP_DOWN || a==BTP_RIGHT) c->selected=(uint8_t)((c->selected+1u)%3u);
        if (a==BTP_CANCEL || (a==BTP_ACCEPT && c->selected==2)) { menu(c);c->selected=6; }
        else if (a==BTP_ACCEPT) {
            c->target_selected=c->selected;
            if (c->selected && c->unit[c->active_unit].infantry) notice(c,15,BTP_COMBAT_SCAN_CHOICE);
            else if (c->selected && c->unit[c->active_unit].record[119]==2) notice(c,16,BTP_COMBAT_SCAN_CHOICE);
            else scan_next(s,24);
        }
        return;
    }
    if (c->phase==BTP_COMBAT_SCAN) {
        unsigned options=btp_combat_scan_detail(c) ? 3u : 2u;
        if (a==BTP_UP || a==BTP_LEFT) c->selected=(uint8_t)((c->selected+options-1u)%options);
        if (a==BTP_DOWN || a==BTP_RIGHT) c->selected=(uint8_t)((c->selected+1u)%options);
        if (a==BTP_CANCEL || (a==BTP_ACCEPT && c->selected==options-1u)) { menu(c);c->selected=6; }
        else if (a==BTP_ACCEPT && !c->selected) scan_next(s,btp_combat_id(c,c->scan_unit));
        else if (a==BTP_ACCEPT) { c->phase=BTP_COMBAT_SCAN_DETAIL;c->selected=0; }
        return;
    }
    if (c->phase==BTP_COMBAT_WEAPONS) {
        if (a==BTP_UP || a==BTP_LEFT) c->weapon_selected=(uint8_t)((c->weapon_selected+count)%(count+1));
        if (a==BTP_DOWN || a==BTP_RIGHT) c->weapon_selected=(uint8_t)((c->weapon_selected+1u)%(count+1));
        if (a==BTP_CANCEL || (a==BTP_ACCEPT && c->weapon_selected==count)) {
            unsigned selected=c->selected;menu(c);c->selected=(uint8_t)selected;
        } else if (a==BTP_ACCEPT) {
            const BtpCombatUnit *u=&c->unit[c->active_unit];
            unsigned type=btp_combat_weapon_type(u,c->weapon_selected);
            if (type&128u) notice(c,18,BTP_COMBAT_WEAPONS);
            else if (!u->record[39+c->weapon_selected]) notice(c,19,BTP_COMBAT_WEAPONS);
            else if (c->orders[c->weapon_selected]!=255) {
                c->phase=BTP_COMBAT_OVERRIDE;c->target_selected=0;c->weapon_ui|=1u;
            } else {
                c->phase=BTP_COMBAT_TARGET;c->target_selected=(uint8_t)(c->selected<3 ? c->selected : 0);
            }
        }
        return;
    }
    if (c->phase==BTP_COMBAT_OVERRIDE) {
        /* 0000:1A13 defaults to Yes. Declining keeps the prior order;
           accepting a mech override clears it before opening the selector. */
        if (a==BTP_LEFT || a==BTP_UP) c->target_selected=0;
        if (a==BTP_RIGHT || a==BTP_DOWN) c->target_selected=1;
        if (a==BTP_CANCEL || (a==BTP_ACCEPT && c->target_selected)) {
            if (c->unit[c->active_unit].infantry) { menu(c);c->selected=3; }
            else c->phase=BTP_COMBAT_WEAPONS;
        } else if (a==BTP_ACCEPT) {
            if (!c->unit[c->active_unit].infantry) c->orders[c->weapon_selected]=255;
            c->phase=BTP_COMBAT_TARGET;
            c->target_selected=(uint8_t)(c->unit[c->active_unit].infantry ? 2u : c->selected<3 ? c->selected : 0u);
        }
        return;
    }
    if (c->phase==BTP_COMBAT_TARGET || c->phase==BTP_COMBAT_KICK) {
        int kick=c->phase==BTP_COMBAT_KICK;
        int foot=c->unit[c->active_unit].infantry;
        uint8_t *order=kick ? &c->kick_target : &c->orders[foot ? 0u : c->weapon_selected];
        if (a==BTP_UP || a==BTP_LEFT) c->target_selected=(uint8_t)((c->target_selected+2u)%3u);
        if (a==BTP_DOWN || a==BTP_RIGHT) c->target_selected=(uint8_t)((c->target_selected+1u)%3u);
        if (a==BTP_CANCEL || (a==BTP_ACCEPT && c->target_selected==2)) {
            *order=255;
            if (kick || foot) { menu(c);c->selected=(uint8_t)(kick ? 4 : 3); }
            else { c->selected=2;c->weapon_ui=3;c->phase=BTP_COMBAT_WEAPONS; }
        } else if (a==BTP_ACCEPT && c->target_selected==0) {
            if (c->unit[c->target_unit].record[0]==255) return;
            *order=(uint8_t)btp_combat_id(c,c->target_unit);
            if (kick || foot) { menu(c);c->selected=(uint8_t)(kick ? 4 : 0); }
            else { c->selected=0;c->weapon_ui=3;c->phase=BTP_COMBAT_WEAPONS; }
        } else if (a==BTP_ACCEPT && c->target_selected==1) {
            /* 103B initializes target ID12; 0D43:0A16 wraps 23 to 12.
               The original manual selector cycles enemy slots only. */
            unsigned id=btp_combat_id(c,c->target_unit);
            for (unsigned n=0;n<24;++n) {
                id=id==23 ? 12u : id+1u;unsigned next=btp_combat_target(c,id);
                if (next<c->count && c->unit[next].record[0]!=255) { c->target_unit=(uint8_t)next;break; }
            }
        }
        return;
    }
    unsigned options=c->phase==BTP_COMBAT_MENU ? btp_combat_menu_count(c) : c->phase==BTP_COMBAT_MESSAGES ? 3u : 2u;
    unsigned row=c->phase==BTP_COMBAT_MENU ? btp_combat_menu_row(c) : c->selected;
    if (a==BTP_UP || a==BTP_LEFT) row=(row+options-1u)%options;
    if (a==BTP_DOWN || a==BTP_RIGHT) row=(row+1u)%options;
    c->selected=(uint8_t)(c->phase==BTP_COMBAT_MENU ? btp_combat_menu_command(c,row) : row);
    if (a!=BTP_ACCEPT) return;
    if (c->phase==BTP_COMBAT_CONTROL) {
        if (!c->selected) { c->automatic=(UINT32_C(1)<<(c->friends ? c->friends : 1u))-1u;c->auto_run=1; }
        c->phase=BTP_COMBAT_MESSAGES;c->selected=2;
    } else if (c->phase==BTP_COMBAT_MESSAGES) {
        c->messages=c->selected;c->phase=BTP_COMBAT_GRAPHICS;c->selected=0;
    } else if (c->phase==BTP_COMBAT_GRAPHICS) {
        c->graphics=(uint8_t)!c->selected;menu(c);
        if (s->campaign.invasion && !c->round) {
            /* 103B:04CF is the uneasy-feeling popup before the first round. */
            s->late.invasion_popup=1;c->phase=BTP_COMBAT_STORY;
        }
    }
    else if (c->phase==BTP_COMBAT_MENU) {
        if (c->selected<3) {
            c->automatic&=~(UINT32_C(1)<<c->active_unit);
            if (!btp_combat_points(&c->unit[c->active_unit],c->selected)) { notice(c,2,BTP_COMBAT_MENU);return; }
            if (c->goal_active && c->movement!=c->selected) {
                c->phase=BTP_COMBAT_REPLACE;c->target_selected=0;return;
            }
            c->cursor_x=c->unit[c->active_unit].x;c->cursor_y=c->unit[c->active_unit].y;c->phase=BTP_COMBAT_MOVE;
        } else if (c->selected==3) {
            /* 0D43:0004 uses menu 5 only for a mech. On foot, the existing
               menu-3 row (Use Weapons is row 2) becomes Cancel's selection. */
            c->weapon_ui=0;
            c->automatic&=~(UINT32_C(1)<<c->active_unit);
            if (c->unit[c->active_unit].infantry) {
                c->phase=(uint8_t)(c->orders[0]==255 ? BTP_COMBAT_TARGET : BTP_COMBAT_OVERRIDE);
                c->target_selected=(uint8_t)(c->orders[0]==255 ? 2 : 0);
            } else {
                const BtpCombatUnit *actor=&c->unit[c->active_unit];
                /* Original 0D43:0004 gives shutdown precedence over sensors.
                   Damaged sensors warn and continue; destroyed sensors return
                   to commands without discarding previously assigned targets. */
                if (actor->heat==30) notice(c,20,BTP_COMBAT_MENU);
                else if (actor->record[119]==1) notice(c,21,BTP_COMBAT_WEAPONS);
                else if (actor->record[119]==2) notice(c,22,BTP_COMBAT_MENU);
                else weapon_list(c);
            }
        }
        else if (c->selected==4) {
            if (!btp_combat_can_kick(&c->unit[c->active_unit])) notice(c,3,BTP_COMBAT_MENU);
            else { c->phase=BTP_COMBAT_KICK;c->target_selected=0; }
        }
        else if (c->selected==5) {
            /* 103B:169E..16D1 assigns this unit; repeated selection remains
               enabled. Next Mech and Begin Fight remain ordinary choices. */
            BtpMap terrain;btp_combat_map(r,s,&terrain);store_plan(c);
            c->automatic|=UINT32_C(1)<<c->active_unit;
            computer_plan(s,r,&terrain,c->active_unit,enemy_ai);
            if (c->friends) load_plan(c,c->active_unit);
            menu(c);c->selected=5;
        }
        else if (c->selected==6) { c->phase=BTP_COMBAT_SCAN_CHOICE;c->selected=0; }
        else if (c->selected==7) {
            /* Live original menu 3 rotates the active friendly unit directly;
               it does not open a character picker or inspect the new unit.
               In particular, selecting the spy is not his discovery event. */
            unsigned friends=c->friends ? c->friends : 1u;
            for (unsigned n=1;n<=friends;++n) {
                unsigned next=(c->active_unit+n)%friends;
                if (c->unit[next].record[0]!=255) { btp_combat_select(c,next);break; }
            }
            menu(c);c->selected=7;
        }
        else if (c->selected==8) {
            /* 103B:069F rejects a menu flee during the invasion; 0610's
               outside-Citadel result 2 bypasses it. Walking out still works. */
            if (s->campaign.invasion) notice(c,5,BTP_COMBAT_MENU);
            else if (s->campaign.encounter>=3 && !s->event.enabled) notice(c,6,BTP_COMBAT_MENU);
            else { c->fled=1;finish(s,r); }
        }
        else if (c->selected==10) {
            /* Original on-foot Clear Moves writes FF to this actor's path
               and clears its computer flag; other units and weapons remain. */
            c->goal_active=c->waypoint_count=0;c->movement=255;
            memset(c->waypoint_x,0,11);memset(c->waypoint_y,0,11);
            memset(c->path[c->active_unit],2,sizeof c->path[0]);
            c->automatic&=~(UINT32_C(1)<<c->active_unit);
            store_plan(c);menu(c);c->selected=10;
        }
        else { c->paused=0;begin_round(s,r,enemy_ai); }
    }
}
void btp_combat_tick(BtpState *s, const BtpResources *r, BtpAction a)
{
    combat_tick(s,r,a,s->campaign.encounter || btp_chi_training(r,s->mission.assignment,BTP_TRAIN_ENEMY_AI));
}
void btp_combat_tick_reference(BtpState *s, const BtpResources *r, BtpAction a)
{
    combat_tick(s,r,a,1);
}
#define COMBAT_FIELDS(X) X(phase) X(selected) X(messages) X(graphics) X(movement) X(goal_x) X(goal_y) X(goal_active) \
    X(cursor_x) X(cursor_y) X(weapon_selected) X(target_selected) X(scan_unit) X(step) X(delay) \
    X(notice) X(notice_return) X(fled) X(won) X(last_weapon) X(last_event) X(enemy_movement)
void btp_combat_encode(const BtpCombatState *c, uint8_t b[BTP_COMBAT_SAVE_BYTES])
{
    memset(b,0,BTP_COMBAT_SAVE_BYTES);size_t p=0;
    for (unsigned i=0;i<4;++i) b[6138+i]=(uint8_t)(c->automatic>>(8*i));
    b[6136]=c->shot.criticals;b[6137]=c->weapon_ui;b[6142]=c->auto_run;b[6143]=c->paused;
    for (unsigned i=0;i<2;++i) {
        const BtpCombatUnit *u=&c->unit[i];memcpy(b+p,u->record,125);p+=125;
        b[p++]=u->x;b[p++]=u->y;b[p++]=u->direction;b[p++]=u->heat;
        b[p++]=u->pool;b[p++]=u->burning;b[p++]=u->cover;
    }
#define FIELD(f) b[p++]=c->f;
    COMBAT_FIELDS(FIELD)
#undef FIELD
    memcpy(b+p,c->orders,11);p+=11;
    memcpy(b+p,c->moved,2);p+=2;memcpy(b+p,c->path_index,2);p+=2;memcpy(b+p,c->walk,2);p+=2;
    memcpy(b+p,c->plan_direction,2);p+=2;memcpy(b+p,c->fallback,2);p+=2;
    b[p++]=(uint8_t)c->round;b[p++]=(uint8_t)(c->round>>8);
    b[p++]=(uint8_t)c->fired;b[p++]=(uint8_t)(c->fired>>8);
    for (unsigned i=0;i<2;++i) for (unsigned j=0;j<12;++j) for (unsigned k=0;k<2;++k) b[p++]=(uint8_t)c->path[i][j][k];
    b[p++]=c->shot.hit;b[p++]=c->shot.location;b[p++]=c->shot.damage;b[p++]=c->shot.destroyed;b[p++]=c->shot.toppled;
    b[p++]=(uint8_t)c->shot.needed;b[p++]=(uint8_t)((uint16_t)c->shot.needed>>8);
    b[p++]=c->flash;
    if (!c->count) return;
    p=384;
    b[p++]=c->count;b[p++]=c->target_unit;b[p++]=c->kick_target;b[p++]=c->lost;
    b[p++]=c->last_attacker;b[p++]=c->last_target;
    for (unsigned i=0;i<7;++i) b[p++]=c->unit[i].infantry;
    for (unsigned i=2;i<7;++i) {
        const BtpCombatUnit *u=&c->unit[i];memcpy(b+p,u->record,125);p+=125;
        b[p++]=u->x;b[p++]=u->y;b[p++]=u->direction;b[p++]=u->heat;
        b[p++]=u->pool;b[p++]=u->burning;b[p++]=u->cover;
        b[p++]=c->moved[i];b[p++]=c->path_index[i];b[p++]=c->walk[i];
        b[p++]=c->plan_direction[i];b[p++]=c->fallback[i];
        for (unsigned j=0;j<12;++j) for (unsigned k=0;k<2;++k) b[p++]=(uint8_t)c->path[i][j][k];
    }
    memcpy(b+p,c->enemy_modes,5);p+=5;
    memcpy(b+p,c->enemy_orders,72);p+=72;
    for (unsigned i=0;i<6;++i) { b[p++]=(uint8_t)c->enemy_fired[i];b[p++]=(uint8_t)(c->enemy_fired[i]>>8); }
    b[p++]=c->waypoint_count;memcpy(b+p,c->waypoint_x,11);p+=11;memcpy(b+p,c->waypoint_y,11);p+=11;
    if (!c->friends && c->count<=7) return;
    p=1536;b[p++]=1;b[p++]=c->friends;b[p++]=c->active_unit;
    memcpy(b+p,c->ids,BTP_COMBAT_UNITS);p+=BTP_COMBAT_UNITS;
    memcpy(b+p,c->plans,sizeof c->plans);p+=sizeof c->plans;
    for (unsigned i=7;i<BTP_COMBAT_UNITS;++i) {
        const BtpCombatUnit *u=&c->unit[i];memcpy(b+p,u->record,125);p+=125;
        b[p++]=u->x;b[p++]=u->y;b[p++]=u->direction;b[p++]=u->heat;
        b[p++]=u->pool;b[p++]=u->burning;b[p++]=u->cover;b[p++]=u->infantry;
        b[p++]=c->moved[i];b[p++]=c->path_index[i];b[p++]=c->walk[i];
        b[p++]=c->plan_direction[i];b[p++]=c->fallback[i];
        for (unsigned j=0;j<12;++j) for (unsigned k=0;k<2;++k) b[p++]=(uint8_t)c->path[i][j][k];
        b[p++]=c->enemy_modes[i-2];memcpy(b+p,c->enemy_orders[i-1],12);p+=12;
        b[p++]=(uint8_t)c->enemy_fired[i-1];b[p++]=(uint8_t)(c->enemy_fired[i-1]>>8);
    }
    assert(p<=5600); /* Optional v51 mission state occupies the reserved tail. */
}
int btp_combat_decode(const uint8_t b[BTP_COMBAT_SAVE_BYTES], BtpCombatState *c)
{
    *c=(BtpCombatState){0};size_t p=0;
    for (unsigned i=0;i<4;++i) c->automatic|=(uint32_t)b[6138+i]<<(8*i);
    c->shot.criticals=b[6136];c->weapon_ui=b[6137];c->auto_run=b[6142];c->paused=b[6143];
    if (c->automatic>4095 || c->auto_run>1 || c->paused>1 || c->weapon_ui>3) return 0;
    for (unsigned i=0;i<2;++i) {
        BtpCombatUnit *u=&c->unit[i];memcpy(u->record,b+p,125);p+=125;
        u->x=b[p++];u->y=b[p++];u->direction=b[p++];u->heat=b[p++];
        u->pool=b[p++];u->burning=b[p++];u->cover=b[p++];
    }
#define FIELD(f) c->f=b[p++];
    COMBAT_FIELDS(FIELD)
#undef FIELD
    memcpy(c->orders,b+p,11);p+=11;
    memcpy(c->moved,b+p,2);p+=2;memcpy(c->path_index,b+p,2);p+=2;memcpy(c->walk,b+p,2);p+=2;
    memcpy(c->plan_direction,b+p,2);p+=2;memcpy(c->fallback,b+p,2);p+=2;
    c->round=(uint16_t)(b[p]|(unsigned)b[p+1]<<8);p+=2;
    c->fired=(uint16_t)(b[p]|(unsigned)b[p+1]<<8);p+=2;
    for (unsigned i=0;i<2;++i) for (unsigned j=0;j<12;++j) for (unsigned k=0;k<2;++k) {
        unsigned n=b[p++];if (n>2 && n!=255) return 0;c->path[i][j][k]=n==255 ? -1 : (int8_t)n;
    }
    c->shot.hit=b[p++];c->shot.location=b[p++];c->shot.damage=b[p++];c->shot.destroyed=b[p++];c->shot.toppled=b[p++];
    unsigned n=b[p]|(unsigned)b[p+1]<<8;p+=2;c->shot.needed=(int16_t)(n>=32768 ? (int)n-65536 : (int)n);
    c->flash=b[p++];
    for (;p<384;++p) if (b[p]) return 0;
    if (!b[384]) for (unsigned i=384;i<BTP_COMBAT_SAVE_BYTES;++i) if (b[i]) return 0;
    c->count=b[p++];c->target_unit=b[p++];c->kick_target=b[p++];c->lost=b[p++];
    c->last_attacker=b[p++];c->last_target=b[p++];
    for (unsigned i=0;i<7;++i) c->unit[i].infantry=b[p++];
    for (unsigned i=2;i<7;++i) {
        BtpCombatUnit *u=&c->unit[i];memcpy(u->record,b+p,125);p+=125;
        u->x=b[p++];u->y=b[p++];u->direction=b[p++];u->heat=b[p++];
        u->pool=b[p++];u->burning=b[p++];u->cover=b[p++];
        c->moved[i]=b[p++];c->path_index[i]=b[p++];c->walk[i]=b[p++];
        c->plan_direction[i]=b[p++];c->fallback[i]=b[p++];
        for (unsigned j=0;j<12;++j) for (unsigned k=0;k<2;++k) {
            unsigned v=b[p++];if (v>2 && v!=255) return 0;c->path[i][j][k]=v==255 ? -1 : (int8_t)v;
        }
    }
    memcpy(c->enemy_modes,b+p,5);p+=5;
    memcpy(c->enemy_orders,b+p,72);p+=72;
    for (unsigned i=0;i<6;++i) { c->enemy_fired[i]=(uint16_t)(b[p]|(unsigned)b[p+1]<<8);p+=2; }
    c->waypoint_count=b[p++];memcpy(c->waypoint_x,b+p,11);p+=11;memcpy(c->waypoint_y,b+p,11);p+=11;
    for (;p<1536;++p) if (b[p]) return 0;
    memset(c->enemy_modes+5,255,sizeof c->enemy_modes-5);
    memset(c->enemy_orders+6,255,sizeof c->enemy_orders-72);
    if (!b[1536]) { for (unsigned i=1536;i<6136;++i) if (b[i]) return 0;return c->count<=7; }
    p=1536;if (b[p++]!=1) return 0;c->friends=b[p++];c->active_unit=b[p++];
    memcpy(c->ids,b+p,BTP_COMBAT_UNITS);p+=BTP_COMBAT_UNITS;
    memcpy(c->plans,b+p,sizeof c->plans);p+=sizeof c->plans;
    for (unsigned i=7;i<BTP_COMBAT_UNITS;++i) {
        BtpCombatUnit *u=&c->unit[i];memcpy(u->record,b+p,125);p+=125;
        u->x=b[p++];u->y=b[p++];u->direction=b[p++];u->heat=b[p++];
        u->pool=b[p++];u->burning=b[p++];u->cover=b[p++];u->infantry=b[p++];
        c->moved[i]=b[p++];c->path_index[i]=b[p++];c->walk[i]=b[p++];
        c->plan_direction[i]=b[p++];c->fallback[i]=b[p++];
        for (unsigned j=0;j<12;++j) for (unsigned k=0;k<2;++k) { unsigned v=b[p++];if (v>2 && v!=255) return 0;c->path[i][j][k]=v==255 ? -1 : (int8_t)v; }
        c->enemy_modes[i-2]=b[p++];memcpy(c->enemy_orders[i-1],b+p,12);p+=12;
        c->enemy_fired[i-1]=(uint16_t)(b[p]|(unsigned)b[p+1]<<8);p+=2;
    }
    for (;p<6136;++p) if (b[p]) return 0;
    return c->count<=BTP_COMBAT_UNITS;
}
#undef COMBAT_FIELDS
int btp_combat_valid_resources(const BtpState *s,const BtpResources *r)
{
    const BtpCombatState *c=&s->combat;
    if (c->count>BTP_COMBAT_UNITS || c->friends>12 || c->active_unit>=BTP_COMBAT_UNITS || c->scan_unit>=BTP_COMBAT_UNITS) return 0;
    if (c->automatic>=(UINT32_C(1)<<(c->friends ? c->friends : 1u)) || c->auto_run>1 || c->paused>1 || c->weapon_ui>3) return 0;
        if (!s->campaign.encounter && (s->mission.assignment<2 || s->mission.assignment>7 || !s->mission.phase)) {
        uint8_t b[BTP_COMBAT_SAVE_BYTES];btp_combat_encode(c,b);
        for (unsigned i=0;i<sizeof b;++i) if (b[i]) return 0;
        return 1;
    }
    if ((s->campaign.encounter ? c->count>24 || c->friends<1 || c->friends>12 || c->friends>=c->count || c->active_unit>=c->friends :
        (s->campaign.invasion ? c->count!=1+btp_chi_mission(r,BTP_MIS_INVASION_ENEMY_COUNT) : c->count<1+btp_chi_training(r,s->mission.assignment,BTP_TRAIN_ENEMY_COUNT) || c->count>1+btp_chi_training(r,s->mission.assignment,BTP_TRAIN_ENEMY_COUNT)+btp_chi_training(r,s->mission.assignment,BTP_TRAIN_COUNT_MASK))) ||
        c->target_unit>=c->count || c->lost>1 || (!s->campaign.encounter && c->unit[0].infantry) ||
        c->last_attacker>=c->count || c->last_target>=c->count ||
        c->phase>BTP_COMBAT_OVERRIDE || c->selected>10 || c->messages>2 || c->graphics>1 ||
        (c->movement>2 && c->movement!=255) || c->goal_active>1 || c->goal_x>(s->campaign.invasion ? 253u : 125u) || c->goal_y>(s->campaign.invasion ? 255u : 127u) ||
        c->cursor_x>(s->campaign.invasion ? 253u : 125u) || c->cursor_y>(s->campaign.invasion ? 255u : 127u) || c->weapon_selected>11 || c->target_selected>2 ||
        c->scan_unit>=c->count || c->step>12 || c->delay>21 || c->notice>22 || c->notice_return>BTP_COMBAT_SCAN_CHOICE ||
        c->fled>1 || c->won>1 || c->fled+c->won+c->lost>1 || c->last_weapon>11 || c->last_event>5 || c->fired>=4096 ||
        c->shot.hit>1 || c->shot.location>35 || c->shot.destroyed>1 || c->shot.toppled>1 ||
        c->shot.needed < -4 || c->shot.needed>(s->combat_profile ? 42 : 30) || (c->enemy_movement>(s->combat_profile ? 2u : 1u) && c->enemy_movement!=255) ||
        c->flash>3 || (c->flash && (c->phase!=BTP_COMBAT_ROUND || !c->graphics || c->last_event<1 || c->last_event>2))) return 0;
    if ((!c->phase && !c->fled && !c->won && !c->lost) || (c->phase &&
        (((c->fled || c->won || c->lost) && !(c->phase==BTP_COMBAT_STORY && s->late.invasion_end)) ||
         (s->mode!=(s->campaign.encounter ? BTP_ENCOUNTER : BTP_MISSION) && !(s->battle_mission.in_hook && s->mode==BTP_EVENT))))) return 0;
    if ((c->phase==BTP_COMBAT_STORY)!=(s->late.invasion_popup!=0) ||
        (c->phase==BTP_COMBAT_STORY && (!s->campaign.invasion || s->late.invasion_event>5 ||
            (s->late.invasion_popup>1 && s->late.invasion_popup!=s->late.invasion_event+2u)))) return 0;
    if ((c->phase==BTP_COMBAT_NOTICE || c->phase==BTP_COMBAT_SPY)!=(c->notice!=0) || (!c->notice && c->notice_return)) return 0;
    if (c->phase==BTP_COMBAT_SPY && (!s->campaign.encounter || !s->spy_discovered || !s->story_flags[39] ||
        c->notice<10 || c->notice>14 || c->notice_return)) return 0;
    if (c->phase==BTP_COMBAT_NOTICE && c->notice_return!=BTP_COMBAT_MENU && c->notice_return!=BTP_COMBAT_CONTROL &&
        !(c->notice_return==BTP_COMBAT_WEAPONS && ((c->notice>=18 && c->notice<=19) || c->notice==21)) &&
        !(c->notice_return==BTP_COMBAT_SCAN_CHOICE && c->notice>=15 && c->notice<=17) &&
        !(c->notice_return==BTP_COMBAT_ROUND && s->campaign.encounter==4 && (c->notice==7 || c->notice==8))) return 0;
    if ((c->phase==BTP_COMBAT_OFFER || c->phase==BTP_COMBAT_AVOID) && (s->campaign.encounter!=1 || c->round || c->selected>1)) return 0;
    unsigned phase=c->notice ? c->notice_return : c->phase;
    /* The damaged-sensor page precedes weapon-list cursor normalization. */
    if (c->notice==21) phase=BTP_COMBAT_MENU;
    if (c->notice>=20 && (c->unit[c->active_unit].infantry || c->selected!=3 ||
        c->notice_return!=(c->notice==21 ? BTP_COMBAT_WEAPONS : BTP_COMBAT_MENU))) return 0;
    if ((phase==BTP_COMBAT_CONTROL || phase==BTP_COMBAT_GRAPHICS) && c->selected>1) return 0;
    if (phase==BTP_COMBAT_MESSAGES && c->selected>2) return 0;
    if (phase==BTP_COMBAT_SCAN_CHOICE && c->selected>2) return 0;
    if ((c->phase==BTP_COMBAT_SCAN || c->phase==BTP_COMBAT_SCAN_DETAIL) &&
        (c->target_selected>1 || c->selected>=(btp_combat_scan_detail(c) ? 3u : 2u))) return 0;
    if (c->phase==BTP_COMBAT_MENU && btp_combat_menu_command(c,btp_combat_menu_row(c))!=c->selected) return 0;
    /* Menu 5's cursor persists while another unit or an infantry selector
       is active. It is bounded by the weapon list only while that list is in use. */
    int foot=c->unit[c->active_unit].infantry;
    unsigned weapons=btp_combat_weapon_count(&c->unit[c->active_unit]);
    if (!foot && ((phase==BTP_COMBAT_WEAPONS && c->weapon_selected>weapons) ||
        ((phase==BTP_COMBAT_TARGET || phase==BTP_COMBAT_OVERRIDE) && c->weapon_selected>=weapons))) return 0;
    if (phase==BTP_COMBAT_WEAPONS && foot) return 0;
    if (c->phase==BTP_COMBAT_OVERRIDE && (c->target_selected>1 || c->orders[foot ? 0u : c->weapon_selected]==255)) return 0;
    if (c->weapon_ui && phase!=BTP_COMBAT_WEAPONS && phase!=BTP_COMBAT_TARGET && phase!=BTP_COMBAT_OVERRIDE) return 0;
    if (c->phase==BTP_COMBAT_ROUND && c->step>12) return 0;
    if (c->goal_active && c->movement>2) return 0;
    if (c->waypoint_count>11 || (c->waypoint_count && !c->goal_active) ||
        (c->phase==BTP_COMBAT_REPLACE && (c->selected>2 || c->target_selected>1))) return 0;
    for (unsigned i=0;i<11;++i) {
        if (i<c->waypoint_count ? c->waypoint_x[i]>(s->campaign.invasion ? 253u : 125u) || c->waypoint_y[i]>(s->campaign.invasion ? 255u : 127u) :
            c->waypoint_x[i] || c->waypoint_y[i]) return 0;
    }
    for (unsigned i=0;i<12;++i) {
        unsigned id=i==11 ? c->kick_target : c->orders[i];
        if (id!=255 && btp_combat_target(c,id)>=c->count) return 0;
    }
    unsigned alive=0;
    for (unsigned i=c->count;i<BTP_COMBAT_UNITS;++i) {
        const BtpCombatUnit *u=&c->unit[i];
        for (unsigned j=0;j<sizeof u->record;++j) if (u->record[j]) return 0;
        if (u->x || u->y || u->direction || u->heat || u->pool || u->burning || u->cover || u->infantry ||
            c->moved[i] || c->path_index[i] || c->walk[i] ||
            c->plan_direction[i] || c->fallback[i] || c->enemy_fired[i-1] || c->enemy_modes[i-2]!=255) return 0;
        for (unsigned j=0;j<12;++j) {
            if (c->path[i][j][0] || c->path[i][j][1] || c->enemy_orders[i-1][j]!=255) return 0;
        }
    }
    for (unsigned i=0;i<c->count;++i) {
        const BtpCombatUnit *u=&c->unit[i];
        if ((u->record[0]!=255 && (u->x>(s->campaign.invasion ? 253u : s->campaign.encounter || u->infantry ? 127u : 125u) || u->y>(s->campaign.invasion ? 255u : 127u))) || u->direction>7 || u->heat>30 || u->burning>3 ||
            (u->cover!=0 && u->cover!=(u->infantry ? 2 : 8) && u->cover!=(u->infantry ? 4 : 16)) || c->moved[i]>12 || c->path_index[i]>12 ||
            c->walk[i]>15 || (c->plan_direction[i]>7 && c->plan_direction[i]!=255) || c->fallback[i]>7 || u->infantry>1 ||
            (i && !s->campaign.encounter && u->infantry!=(!s->campaign.invasion && btp_chi_training(r,s->mission.assignment,BTP_TRAIN_INFANTRY))) || btp_combat_weapon_count(u)>11 || u->record[117]>3 || u->record[118]>2 || u->record[119]>2) return 0;
        if (u->infantry && (u->record[1]<2 || u->record[1]>12 || u->record[11]>13 || u->record[15]>120)) return 0;
        if (i) {
            if (i>=(c->friends ? c->friends : 1u)) alive+=u->record[0]!=255;
            unsigned movement=i==1 ? c->enemy_movement : c->enemy_modes[i-2];
            if ((movement>(i<c->friends || s->combat_profile ? 2u : 1u) && movement!=255) || c->enemy_fired[i-1]>=4096) return 0;
            for (unsigned w=0;w<12;++w) if (c->enemy_orders[i-1][w]!=255 && (c->friends ? btp_combat_target(c,c->enemy_orders[i-1][w])>=c->count : c->enemy_orders[i-1][w]!=0)) return 0;
        }
        for (unsigned j=0;j<12;++j) for (unsigned k=0;k<2;++k) if (c->path[i][j][k]<-1 || c->path[i][j][k]>2) return 0;
    }
    unsigned jason=btp_combat_target(c,4);
    unsigned rex=btp_combat_target(c,5);
    int lost=s->campaign.encounter ? (jason<c->count && c->unit[jason].record[0]==255) ||
        (btp_chi_mission(r,BTP_MIS_ENCOUNTER_ESSENTIAL_PEOPLE)>1 && rex<c->count && c->unit[rex].record[0]==255) : c->unit[0].record[0]==255;
    /* A surviving arena pilot is a lost match, not a campaign death. Before
       the end-of-round check, its destruction presentation may still drain. */
    if (s->campaign.encounter==4 && !s->story_flags[35] && c->unit[0].record[0]==255 && c->lost) lost=1;
    if (s->battle_mission.active) {
        /* Scripted defence can finish with surviving enemies or continue
           between waves. Real party deaths still take precedence at runtime. */
        return (lost || s->battle_mission.outcome==2)==(c->lost!=0 || s->effects.pending==2 || s->battle_mission.outcome==2);
    }
    return lost==(c->lost!=0 || s->effects.pending==2) &&
        (alive ? !c->won && s->effects.pending!=1 : c->won || s->effects.pending==1 || c->phase==BTP_COMBAT_ROUND || c->phase==BTP_COMBAT_SPY);
}

int btp_combat_valid(const BtpState *s) { return btp_combat_valid_resources(s,NULL); }
