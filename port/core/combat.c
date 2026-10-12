#include "core/combat.h"
#include "core/npc.h"
#include "core/animation.h"
#include "core/effects.h"
#include "core/campaign.h"
#include "core/world.h"
#include "core/party.h"
#include "core/audio.h"
#include <stdlib.h>
#include <string.h>

static const int8_t dx[8] = {0,1,1,1,0,-1,-1,-1};
static const int8_t dy[8] = {-1,-1,0,1,1,1,0,-1};
static unsigned tile_at(const BtpMap *m, int sx, int sy, int at);
static int half(int n) { return n/2-(n < 0 && n%2 != 0); }
static unsigned turn(unsigned from, unsigned to)
{
    return from == to ? from : (from+(((to-from)&7u) < 5 ? 1u : 7u))&7u;
}
int btp_combat_los(const BtpMap *m, unsigned gate, int x, int y, int tx, int ty)
{
    /* 0E31:1BFE follows a gradually turning ray through a 24x24 working
       grid. Preserve its asymmetric parity updates instead of Bresenham. */
    int sx=x, sy=y, at=(((y&15)/2)+2)*24+((x&15)/2)+152+(x&1), px=!(x&1), py=y&1;
    unsigned heading=btp_combat_direction(x,y,tx,ty);
    for (unsigned i=0; i<256; ++i) {
        if (at<0 || at>=576) return -1; /* Original reads outside its terrain grid. */
        if (tile_at(m,sx,sy,at) >= gate) return 0;
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
    return btp_map_tile(m,(sx&112)/2-8+at%24,(sy&112)/2-8+at/24);
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
    const BtpCombatUnit *units, unsigned count, unsigned self, int8_t steps[12][2])
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
            if (nx<0 || ny<0 || nx>=2*m->width-2 || ny>=2*m->height) continue;
            int at=grid(u->x,u->y,nx,ny,0,&mask);
            if (tile_at(m,u->x,u->y,at)>=gate || (!u->infantry && tile_at(m,u->x,u->y,at+(nx&1 ? -1 : 1))>=gate)) continue;
            int blocked=occupied(u,other,nx,ny);
            for (unsigned k=0;k<count;++k) if (k!=self && occupied(u,&units[k],nx,ny)) blocked=1;
            if (blocked) { if (nx==tx && ny==ty) stopped=1; continue; }
            steps[i][0]=dx[d]; steps[i][1]=dy[d]; x=nx; y=ny; heading=d; break;
        }
        unsigned mask, tile=tile_at(m,u->x,u->y,grid(u->x,u->y,x,y,1,&mask));
        int cost=movement==2 || tile>=64 || !(tile&mask) ? 1 : (tile&240u)==32 ? 3 : 2;
        points-=cost;
    }
}
void btp_combat_plan(const BtpMap *m, unsigned gate, const BtpCombatUnit *u,
    const BtpCombatUnit *other, int tx, int ty, unsigned movement, int computer, int8_t steps[12][2])
{
    plan_points(m,gate,u,other,tx,ty,movement,computer,btp_combat_points(u,movement),NULL,NULL,0,NULL,0,0,steps);
}
void btp_combat_route(const BtpMap *m, unsigned gate, const BtpCombatState *c, int8_t steps[12][2])
{
    unsigned actor=c->active_unit,enemy=c->friends ? c->friends : 1u;
    plan_points(m,gate,&c->unit[actor],&c->unit[enemy],c->goal_x,c->goal_y,c->movement,0,
        btp_combat_points(&c->unit[actor],c->movement),c->waypoint_x,c->waypoint_y,c->waypoint_count,
        c->friends ? c->unit : NULL,c->friends ? c->count : 0,actor,steps);
}
void btp_combat_map(const BtpResources *r,const BtpState *s,BtpMap *m)
{
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
void btp_combat_select(BtpCombatState *c,unsigned unit)
{
    if (!c->friends || unit>=c->friends) return;
    store_plan(c);c->active_unit=(uint8_t)unit;
    const BtpCombatPlan *p=&c->plans[unit];
    c->movement=p->movement;c->goal_x=p->x;c->goal_y=p->y;c->goal_active=p->active;c->waypoint_count=p->count;
    memcpy(c->waypoint_x,p->wx,11);memcpy(c->waypoint_y,p->wy,11);memcpy(c->orders,p->orders,11);c->kick_target=p->kick;
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
    c->phase=BTP_COMBAT_MENU; c->selected=9;
}
int btp_combat_waypoint(BtpCombatState *c, unsigned x, unsigned y, unsigned movement)
{
    if (x>125 || y>127 || movement>2) return 0;
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
void btp_combat_begin(BtpState *s, const BtpResources *r)
{
    BtpCombatState *c=&s->combat;
    *c=(BtpCombatState){.phase=BTP_COMBAT_CONTROL,.selected=1,.messages=2,.graphics=1,
        .movement=255,.walk={6,12},.plan_direction={0,6},.enemy_movement=255,
        .count=2,.target_unit=1,.kick_target=255,.last_target=1};
    memset(c->orders,255,sizeof c->orders);
    memset(c->enemy_orders,255,sizeof c->enemy_orders);memset(c->enemy_modes,255,sizeof c->enemy_modes);
    memcpy(c->unit[0].record,r->combat.loans[s->story_flags[2]],125);
    c->unit[0].x=64;c->unit[0].y=77;c->unit[0].direction=2;
    unsigned assignment=s->mission.assignment;
    if (assignment==3) c->count=(uint8_t)(4+(btp_rng_next(s->npc.rng)&3u));
    if (assignment==5) c->count=3;
    if (assignment>=6) c->count=(uint8_t)(s->campaign.invasion ? 5 : assignment-2);
    unsigned x=101+(btp_rng_next(s->npc.rng)&7u),y=89+(btp_rng_next(s->npc.rng)&7u);
    static const uint8_t ox[6]={1,2,0,1,0,0},oy[6]={2,2,3,3,0,1};
    /* Original slot-8 onward offsets at DS:1642/164E. */
    for (unsigned i=1;i<c->count;++i) {
        BtpCombatUnit *u=&c->unit[i];u->direction=6;c->plan_direction[i]=6;c->walk[i]=12;
        u->x=(uint8_t)(assignment==2 ? 114 : x+(assignment>=4 ? 4*((i-1)%2) : 0));
        u->y=(uint8_t)(y+(assignment>=6 ? 4*((i-1)/2) : 0));
        if (assignment==3) {
            u->infantry=1;u->record[12]=8;u->x=(uint8_t)(x+ox[i-1]);u->y=(uint8_t)(y+oy[i-1]);
            for (unsigned k=4;k<=9;++k) u->record[k]=(uint8_t)(btp_rng_next(s->npc.rng)&1u);
            u->record[1]=(uint8_t)btp_combat_dice(s->npc.rng);u->record[15]=(uint8_t)(10*u->record[1]);
            u->record[11]=(uint8_t)(btp_rng_next(s->npc.rng)%14u);
        } else {
            memcpy(u->record,s->campaign.invasion ? r->combat.jenner : r->combat.loans[0],125);
            if (assignment==2) { u->record[36]=u->record[37]=0;memset(u->record+39,0,12); }
        }
    }
}
static void finish(BtpState *s)
{
    BtpCombatState *c=&s->combat;
    s->x_half=c->unit[0].x;s->y_half=(uint16_t)(c->unit[0].y+(c->unit[0].infantry ? 0u : 2u));
    if (s->campaign.encounter) { c->phase=BTP_COMBAT_NONE;c->flash=0;return; }
    s->mission.corner=1;s->mission.idle=0;s->mission.walk=c->walk[0];
    s->mission.direction=c->unit[0].direction;c->phase=BTP_COMBAT_NONE;c->flash=0;
    /* 103B:0D6D..0DA5: training encounter argument 1 waits for a key
       after the original return-to-base message. */
    if (!s->campaign.invasion) s->mission.phase=BTP_MISSION_RETURN;
    if (s->campaign.invasion && !c->lost) {
        s->campaign.world_x=(uint16_t)(1536+s->x_half);
        s->campaign.world_y=(uint16_t)(1536+s->y_half);
        s->x_half&=127;s->y_half&=127;
    }
    if (c->lost && !s->campaign.invasion) { s->x_half=60;s->y_half=79; }
}
static void begin_round(BtpState *s, const BtpResources *r, int enemy_ai)
{
    BtpMap terrain;btp_combat_map(r,s,&terrain);
    if (s->campaign.invasion) {
        memset(terrain.tiles+62*64+56,64,8);memset(terrain.tiles+63*64+56,64,8);
    }
    BtpCombatState *c=&s->combat;
    memset(c->path,0,sizeof c->path);
    for (unsigned i=0;i<c->count;++i) memset(c->path[i],2,sizeof c->path[i]);
    store_plan(c);
    unsigned friends=c->friends ? c->friends : 1u,active=c->active_unit;
    if (c->friends) {
        for (unsigned i=0;i<friends;++i) {
            btp_combat_select(c,i);
            if (c->goal_active) btp_combat_route(&terrain,s->gate,c,c->path[i]);
            if (i) {
                memcpy(c->enemy_orders[i-1],c->orders,11);c->enemy_orders[i-1][11]=c->kick_target;
                if (i==1) c->enemy_movement=c->movement;else c->enemy_modes[i-2]=c->movement;
            }
        }
        btp_combat_select(c,active);
    } else if (c->goal_active) btp_combat_route(&terrain,s->gate,c,c->path[0]);
    for (unsigned index=friends;index<c->count;++index) {
    if (c->unit[index].record[0]==255) continue;
    /* 0E31:03AB: the weapon-component range scan intentionally uses the
       component value as the table index, even when ammunition is empty. */
    BtpCombatUnit enemy=c->unit[index];enemy.direction=c->plan_direction[index];
    unsigned prey=0;
    if (c->friends) for (unsigned i=0;i<friends;++i) if (c->unit[i].record[0]!=255 &&
        (c->unit[prey].record[0]==255 || btp_combat_distance(enemy.x,enemy.y,c->unit[i].x,c->unit[i].y)<btp_combat_distance(enemy.x,enemy.y,c->unit[prey].x,c->unit[prey].y))) prey=i;
    int ex=enemy.x,ey=enemy.y,px=c->unit[prey].x,py=c->unit[prey].y;
    unsigned distance=btp_combat_distance(ex,ey,px,py),preferred=255;
    int visible=btp_combat_los(&terrain,s->gate,ex,ey,px,py)>0;
    for (unsigned i=51;i<86;++i) {
        unsigned component=enemy.record[i];
        if (component>=16 && component<=32) {
            unsigned value=(r->combat.weapons[component][14]&224u)>>3;
            if (value<preferred) preferred=value;
        }
    }
    if (preferred==255) preferred=0;
    if (enemy.infantry) preferred=r->combat.weapons[enemy.record[11]][14]>>5;
    int close=!enemy.infantry && visible && abs(px-ex)<=3 && abs(py-ey)<2;
    uint8_t *movement=index==1 ? &c->enemy_movement : &c->enemy_modes[index-2];*movement=255;
    if (enemy_ai && close) {
        c->plan_direction[index]=(uint8_t)btp_combat_direction(ex,ey,px,py);
        c->unit[index].direction=c->fallback[index];
    } else if (enemy_ai && (!visible || !preferred || distance>preferred || enemy.infantry)) {
        int tx=px,ty=py;
        if (enemy.infantry) { tx=ex+((px>ex)-(px<ex))*-6;ty=ey+((py>ey)-(py<ey))*-6; }
        if (!enemy.infantry && visible && preferred) {
            int sx=(tx>ex)-(tx<ex),sy=(ty>ey)-(ty<ey);
            if (distance>preferred) { tx=ex+sx*(int)(distance-preferred);ty=ey+sy*(int)(distance-preferred); }
            else { tx=ex;ty=ey; }
        }
        *movement=(uint8_t)(enemy.heat || enemy.infantry ? 0 : 1);
        /* 0E31:046F normalizes robot IDs before 103B:2474. IDs 20/21
           cross its threshold and take six points; IDs 16..19 take three. */
        int points=enemy.infantry && btp_combat_id(c,index)>=20 ? 6 : btp_combat_points(&enemy,*movement);
        plan_points(&terrain,s->gate,&enemy,&c->unit[prey],tx,ty,*movement,1,points,NULL,NULL,0,
            s->mission.assignment==5 || c->friends ? c->unit : NULL,s->mission.assignment==5 || c->friends ? c->count : 0,index,c->path[index]);
    }
    memset(c->enemy_orders[index-1],255,12);
    if (s->mission.assignment>=3 || c->friends) {
        for (unsigned w=0;w<btp_combat_weapon_count(&enemy) && w<10;++w)
            if (btp_combat_weapon(&enemy,w)<33 && enemy.heat<30) c->enemy_orders[index-1][w]=(uint8_t)btp_combat_id(c,prey);
        if (!enemy.infantry && enemy.heat<30) c->enemy_orders[index-1][11]=(uint8_t)btp_combat_id(c,prey);
    }
    }
    memset(c->moved,0,sizeof c->moved);memset(c->path_index,0,sizeof c->path_index);
    memset(c->enemy_fired,0,sizeof c->enemy_fired);
    c->fired=0;c->step=0;c->delay=0;c->last_event=0;c->flash=0;c->phase=BTP_COMBAT_ROUND;
    ++c->round;
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
static void advance(BtpCombatState *c, unsigned index)
{
    BtpCombatUnit *u=&c->unit[index];unsigned p=c->path_index[index];
    if (p>=12 || u->record[0]==255) return;
    int mx=c->path[index][p][0], my=c->path[index][p][1];
    if (mx==2 || my==2 || (!mx && !my)) return;
    int x=u->x+mx,y=u->y+my;
    for (unsigned i=0;i<c->count;++i) if (i!=index && occupied(u,&c->unit[i],x,y)) return;
    unsigned direction=btp_combat_direction(u->x,u->y,x,y);
    c->walk[index]=(uint8_t)btp_combat_walk_frame(c->walk[index],u->direction,direction,u->infantry);
    u->direction=(uint8_t)direction;c->plan_direction[index]=(uint8_t)direction;
    u->x=(uint8_t)x;u->y=(uint8_t)y;++c->moved[index];++c->path_index[index];
}
static void mark(BtpState *s,unsigned sprite,unsigned x,unsigned y)
{
    s->terrain_marks[s->terrain_next]=(BtpTerrainMark){(uint8_t)sprite,s->map_id,(uint8_t)x,(uint8_t)y};
    s->terrain_next=(uint8_t)((s->terrain_next+1u)&63u);
}
void btp_combat_ignite(BtpState *s, const BtpCombatUnit *target)
{
    /* 12E8:1E46 rolls 2d6; values outside 5..9 add sprite 124 through
       103B:27C9. The original 64-entry ring survives encounters. It does
       not replace the map's terrain/LOS grid or implement spreading fire. */
    unsigned roll=btp_combat_dice(s->npc.rng);
    if (roll>=5 && roll<=9) return;
    mark(s,124,(target->x-(target->infantry ? 1u : 0u))&127u,
        (target->y-(target->infantry ? 0u : 1u))&127u);
}
static void end_round(BtpState *s,const BtpResources *r)
{
    BtpCombatState *c=&s->combat;
    BtpMap map;btp_combat_map(r,s,&map);
    for (unsigned i=0;i<c->count;++i) if (c->unit[i].record[0]!=255) {
        unsigned terrain,mode=i==0 ? c->movement : i==1 ? c->enemy_movement : c->enemy_modes[i-2];
        (void)btp_combat_cover(&map,&c->unit[i],&terrain);
        btp_combat_cool(&c->unit[i],mode==255 ? -1 : (int)mode,c->moved[i],terrain);
    }
    if (!c->goal_active) c->movement=255;
    c->delay=0;c->flash=0;menu(c);
}
static void round_tick(BtpState *s, const BtpResources *r, int enemy_ai)
{
    BtpCombatState *c=&s->combat;
    if (c->delay) { --c->delay;if (c->flash) --c->flash;return; } c->delay=2;c->flash=0;
    advance(c,0);
    /* Ignore old in-progress target paths too: loading an earlier checkpoint
       must not reanimate the training shell. */
    if (enemy_ai) for (unsigned i=1;i<c->count;++i) advance(c,i);
    BtpMap map;btp_combat_map(r,s,&map);
    unsigned terrain[BTP_COMBAT_UNITS]={0};
    for (unsigned i=0;i<c->count;++i) c->unit[i].cover=(uint8_t)btp_combat_cover(&map,&c->unit[i],&terrain[i]);
    for (unsigned ordinal=0;ordinal<(c->friends ? 24u : c->count);++ordinal) {
        unsigned actor=c->friends ? btp_combat_target(c,ordinal) : ordinal;
        if (actor>=c->count) continue;
        if (c->unit[actor].record[0]==255 || (actor && (!enemy_ai || s->mission.assignment==2))) continue;
        for (unsigned i=0;i<12;++i) {
            uint8_t *order=actor ? &c->enemy_orders[actor-1][i] : c->friends ? i==11 ? &c->plans[0].kick : &c->plans[0].orders[i] : i==11 ? &c->kick_target : &c->orders[i];
            uint16_t *fired=actor ? &c->enemy_fired[actor-1] : &c->fired;
            if (*order==255 || (*fired&(1u<<i))) continue;
            unsigned target=btp_combat_target(c,*order);
            if (target>=c->count || c->unit[target].record[0]==255) { *order=255;continue; }
            BtpCombatUnit *attacker=&c->unit[actor],*enemy=&c->unit[target];
            unsigned w=i==11 ? 32 : btp_combat_weapon(attacker,i);
            if (w>=33 || (i==11 && !btp_combat_can_kick(attacker))) { *order=255;continue; }
            if (attacker->heat>=30 || btp_combat_range(&r->combat,w,attacker->x,attacker->y,enemy->x,enemy->y)>=3) continue;
            int los=btp_combat_los(&map,s->gate,attacker->x,attacker->y,enemy->x,enemy->y);
            if (!los) { if (!c->flash) c->last_event=3;continue; }
            if (los<0) { if (!c->flash) c->last_event=4;continue; }
            int ignition=enemy->cover && terrain[target]>=16 && terrain[target]<=63 &&
                ((w>=16 && w<=18) || w==11);
            int movement=actor ? (actor==1 ? c->enemy_movement : c->enemy_modes[actor-2]) : c->friends ? c->plans[0].active ? c->plans[0].movement : 255 : c->goal_active ? c->movement : 255;
            unsigned skill=actor ? 0u : s->mech_skills[i==11 ? 1 : 0];
            if (c->friends && actor<c->friends && !attacker->infantry && attacker->record[121]<8)
                skill=s->party.people[attacker->record[121]][i==11 ? 8 : 7];
            c->shot=btp_combat_attack_unit(attacker,enemy,&r->combat,i,movement==255 ? -1 : movement,c->moved[target],
                skill,btp_combat_id(c,actor),s->npc.rng);
            if (ignition && !c->shot.hit) btp_combat_ignite(s,enemy);
            c->last_attacker=(uint8_t)actor;c->last_target=(uint8_t)target;
            c->last_weapon=(uint8_t)i;c->last_event=(uint8_t)(c->shot.hit ? 1 : 2);
            *fired|=(uint16_t)(1u<<i);c->flash=c->graphics && c->last_event<=2 ? 3 : 0;
            btp_effects_shot(s,actor,target,w);
            if (c->graphics) {
                unsigned sound=w<3 ? 13u : w==3 ? 5u : w<=6 ? 11u : w<=8 ? 6u :
                    w==9 || (w>=19 && w<=23) ? 3u : w==10 || w==11 || (w>=25 && w<=31) ? 1u :
                    w==12 || w==13 ? 9u : w>=15 && w<=18 ? 2u : 0u;
                btp_audio_effect(s,sound);if (c->shot.hit) btp_audio_effect(s,4);
                unsigned kind=0;
                if (c->shot.hit && !enemy->infantry && (w==10 || w==11)) kind=1;
                if (c->shot.hit && w>=15 && w<=18 && !attacker->infantry)
                    kind=actor==0 ? s->story_flags[2] ? 7u : 4u : target==0 && s->story_flags[2] ? 3u : 0u;
                if (kind) {
                    if (btp_outtake_roll(s,kind,0) && s->presentation.count<24)
                        s->presentation.kinds[s->presentation.count++]=(uint8_t)kind;
                }
                if (c->shot.toppled) {
                    if (btp_outtake_roll(s,16,0) && s->presentation.count<24) s->presentation.kinds[s->presentation.count++]=16;
                }
            }
            if (c->shot.destroyed) {
                /* 12E8:1B7F / 1C6E preserve the original corpse/wreck artwork. */
                mark(s,enemy->infantry ? 126u : 128u+(target==0 && s->story_flags[2]!=0),
                    (enemy->x-(enemy->infantry ? 0u : 1u))&127u,
                    (enemy->y-(enemy->infantry ? 0u : 1u))&127u);
                if (s->campaign.encounter) btp_campaign_destroy(s,target);
                else {
                    enemy->record[0]=255;
                    if (target || !s->campaign.invasion) enemy->x=enemy->y=127;
                    if (!target) { s->effects.pending=2;return; }
                }
                if (s->effects.pending==2) return;
                unsigned remaining=0;
                for (unsigned k=c->friends ? c->friends : 1u;k<c->count;++k) remaining+=c->unit[k].record[0]!=255;
                if (!remaining) { s->effects.pending=1;return; }
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
    s->mission.walk=c->walk[0];s->mission.direction=c->unit[0].direction;
    if (s->campaign.invasion && c->unit[0].y==127) { c->fled=1;finish(s);return; }
    if (++c->step==12 && !s->effects.count) end_round(s,r);
}
static void combat_tick(BtpState *s, const BtpResources *r, BtpAction a, int enemy_ai)
{
    BtpCombatState *c=&s->combat;
    if (s->effects.count) {
        btp_effects_tick(s,r);if (s->effects.count) return;
    }
    if (s->presentation.count) {
        unsigned kind=s->presentation.kinds[0];--s->presentation.count;
        memmove(s->presentation.kinds,s->presentation.kinds+1,s->presentation.count);
        s->presentation.kinds[s->presentation.count]=0;
        (void)btp_cutscene_begin(s,r,kind,3);return;
    }
    if (s->aftermath.eject) btp_campaign_eject(s);
    if (s->effects.pending) {
        c->won=(uint8_t)(s->effects.pending==1);c->lost=(uint8_t)(s->effects.pending==2);
        s->effects.pending=0;finish(s);return;
    }
    /* A shot on the twelfth microstep must finish its presentation before
       cleanup returns to the command menu. This state is also saveable. */
    if (c->phase==BTP_COMBAT_ROUND && c->step==12) { end_round(s,r);return; }
    if (c->phase==BTP_COMBAT_PICK) {
        if (a==BTP_UP || a==BTP_LEFT) c->scan_unit=(uint8_t)((c->scan_unit+c->friends-1u)%c->friends);
        if (a==BTP_DOWN || a==BTP_RIGHT) c->scan_unit=(uint8_t)((c->scan_unit+1u)%c->friends);
        if (a==BTP_ACCEPT && c->unit[c->scan_unit].record[0]!=255) { btp_combat_select(c,c->scan_unit);menu(c); }
        if (a==BTP_CANCEL) menu(c);
        return;
    }
    unsigned count=btp_combat_weapon_count(&c->unit[c->active_unit]);
    if (c->phase==BTP_COMBAT_ROUND) { round_tick(s,r,enemy_ai);return; }
    if (c->phase==BTP_COMBAT_NOTICE) {
        if (a==BTP_ACCEPT || a==BTP_CANCEL) { c->phase=c->notice_return;c->notice=c->notice_return=0; }
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
            if (x>=0 && x<2*r->map.width-2 && y>=0 && y<2*r->map.height-(s->campaign.invasion ? 0 : 2)) { c->cursor_x=(uint8_t)x;c->cursor_y=(uint8_t)y; }
        }
        if (a==BTP_ACCEPT) {
            if (!btp_combat_waypoint(c,c->cursor_x,c->cursor_y,c->selected)) notice(c,4,BTP_COMBAT_MENU);
            else menu(c);
        }
        if (a==BTP_CANCEL) menu(c);
        return;
    }
    if (c->phase==BTP_COMBAT_SCAN) {
        if (a==BTP_LEFT || a==BTP_UP) c->scan_unit=(uint8_t)((c->scan_unit+c->count-1u)%c->count);
        if (a==BTP_RIGHT || a==BTP_DOWN) c->scan_unit=(uint8_t)((c->scan_unit+1u)%c->count);
        if (a==BTP_ACCEPT || a==BTP_CANCEL) menu(c);
        return;
    }
    if (c->phase==BTP_COMBAT_WEAPONS) {
        if (a==BTP_UP) c->weapon_selected=(uint8_t)((c->weapon_selected+count)%(count+1));
        if (a==BTP_DOWN) c->weapon_selected=(uint8_t)((c->weapon_selected+1u)%(count+1));
        if (a==BTP_CANCEL || (a==BTP_ACCEPT && c->weapon_selected==count)) menu(c);
        else if (a==BTP_ACCEPT) { c->phase=BTP_COMBAT_TARGET;c->target_selected=0; }
        return;
    }
    if (c->phase==BTP_COMBAT_TARGET || c->phase==BTP_COMBAT_KICK) {
        int kick=c->phase==BTP_COMBAT_KICK;
        uint8_t *order=kick ? &c->kick_target : &c->orders[c->weapon_selected];
        if (a==BTP_UP) c->target_selected=(uint8_t)((c->target_selected+2u)%3u);
        if (a==BTP_DOWN) c->target_selected=(uint8_t)((c->target_selected+1u)%3u);
        if (a==BTP_CANCEL || (a==BTP_ACCEPT && c->target_selected==2)) {
            *order=255;if (kick) menu(c);else c->phase=BTP_COMBAT_WEAPONS;
        } else if (a==BTP_ACCEPT && c->target_selected==0) {
            if (c->unit[c->target_unit].record[0]==255) return;
            *order=(uint8_t)btp_combat_id(c,c->target_unit);
            if (kick) menu(c);else { ++c->weapon_selected;c->phase=BTP_COMBAT_WEAPONS; }
        } else if (a==BTP_ACCEPT && c->target_selected==1) {
            for (unsigned n=0;n<c->count-(c->friends ? c->friends : 1u);++n) {
                unsigned first=c->friends ? c->friends : 1u;
                c->target_unit=(uint8_t)(first+(c->target_unit-first+1u)%(c->count-first));
                if (c->unit[c->target_unit].record[0]!=255) break;
            }
        }
        return;
    }
    unsigned options=c->phase==BTP_COMBAT_MENU ? 10u : c->phase==BTP_COMBAT_MESSAGES ? 3u : 2u;
    if (a==BTP_UP || a==BTP_LEFT) c->selected=(uint8_t)((c->selected+options-1u)%options);
    if (a==BTP_DOWN || a==BTP_RIGHT) c->selected=(uint8_t)((c->selected+1u)%options);
    if (a!=BTP_ACCEPT) return;
    if (c->phase==BTP_COMBAT_CONTROL) {
        if (!c->selected) { notice(c,1,BTP_COMBAT_CONTROL);return; }
        c->phase=BTP_COMBAT_MESSAGES;c->selected=2;
    } else if (c->phase==BTP_COMBAT_MESSAGES) {
        c->messages=c->selected;c->phase=BTP_COMBAT_GRAPHICS;c->selected=0;
    } else if (c->phase==BTP_COMBAT_GRAPHICS) { c->graphics=(uint8_t)!c->selected;menu(c); }
    else if (c->phase==BTP_COMBAT_MENU) {
        if (c->selected<3) {
            if (!btp_combat_points(&c->unit[c->active_unit],c->selected)) { notice(c,2,BTP_COMBAT_MENU);return; }
            if (c->goal_active && c->movement!=c->selected) {
                c->phase=BTP_COMBAT_REPLACE;c->target_selected=0;return;
            }
            c->cursor_x=c->unit[c->active_unit].x;c->cursor_y=c->unit[c->active_unit].y;c->phase=BTP_COMBAT_MOVE;
        } else if (c->selected==3) { c->phase=BTP_COMBAT_WEAPONS;c->weapon_selected=0; }
        else if (c->selected==4) {
            if (!btp_combat_can_kick(&c->unit[c->active_unit])) notice(c,3,BTP_COMBAT_MENU);
            else { c->phase=BTP_COMBAT_KICK;c->target_selected=0; }
        }
        else if (c->selected==5) { if (c->friends>1) { c->phase=BTP_COMBAT_PICK;c->scan_unit=c->active_unit; } else notice(c,1,BTP_COMBAT_MENU); }
        else if (c->selected==6) { c->scan_unit=0;c->phase=BTP_COMBAT_SCAN; }
        else if (c->selected==7) menu(c);
        else if (c->selected==8) {
            if (s->campaign.invasion && c->unit[c->active_unit].y<127) notice(c,5,BTP_COMBAT_MENU);
            else { c->fled=1;finish(s); }
        }
        else begin_round(s,r,enemy_ai);
    }
}
void btp_combat_tick(BtpState *s, const BtpResources *r, BtpAction a)
{
    combat_tick(s,r,a,s->campaign.encounter || s->mission.assignment>=3);
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
}
int btp_combat_decode(const uint8_t b[BTP_COMBAT_SAVE_BYTES], BtpCombatState *c)
{
    *c=(BtpCombatState){0};size_t p=0;
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
    if (!b[1536]) { for (unsigned i=1536;i<BTP_COMBAT_SAVE_BYTES;++i) if (b[i]) return 0;return c->count<=7; }
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
    for (;p<BTP_COMBAT_SAVE_BYTES;++p) if (b[p]) return 0;
    return c->count<=BTP_COMBAT_UNITS;
}
#undef COMBAT_FIELDS
int btp_combat_valid(const BtpState *s)
{
    const BtpCombatState *c=&s->combat;
        if (!s->campaign.encounter && (s->mission.assignment<2 || s->mission.assignment>7 || !s->mission.phase)) {
        uint8_t b[BTP_COMBAT_SAVE_BYTES];btp_combat_encode(c,b);
        for (unsigned i=0;i<sizeof b;++i) if (b[i]) return 0;
        return 1;
    }
    if ((s->campaign.encounter ? c->count>24 || c->friends<1 || c->friends>12 || c->friends>=c->count || c->active_unit>=c->friends :
        (s->mission.assignment==3 ? c->count<4 || c->count>7 : c->count!=(s->mission.assignment>=6 ? s->campaign.invasion ? 5 : 4 : s->mission.assignment==5 ? 3 : 2))) ||
        c->target_unit<1 || c->target_unit>=c->count || c->lost>1 || (!s->campaign.encounter && c->unit[0].infantry) ||
        c->last_attacker>=c->count || c->last_target>=c->count ||
        c->phase>BTP_COMBAT_PICK || c->selected>9 || c->messages>2 || c->graphics>1 ||
        (c->movement>2 && c->movement!=255) || c->goal_active>1 || c->goal_x>125 || c->goal_y>127 ||
        c->cursor_x>125 || c->cursor_y>127 || c->weapon_selected>11 || c->target_selected>2 ||
        c->scan_unit>=c->count || c->step>12 || c->delay>2 || c->notice>5 || c->notice_return>BTP_COMBAT_SCAN ||
        c->fled>1 || c->won>1 || c->fled+c->won+c->lost>1 || c->last_weapon>11 || c->last_event>5 || c->fired>=4096 ||
        c->shot.hit>1 || c->shot.location>35 || c->shot.destroyed>1 || c->shot.toppled>1 ||
        c->shot.needed < -4 || c->shot.needed>30 || (c->enemy_movement>1 && c->enemy_movement!=255) ||
        c->flash>3 || (c->flash && (c->phase!=BTP_COMBAT_ROUND || !c->graphics || c->last_event<1 || c->last_event>2))) return 0;
    if ((!c->phase && !c->fled && !c->won && !c->lost) || (c->phase && (c->fled || c->won || c->lost || s->mode!=(s->campaign.encounter ? BTP_ENCOUNTER : BTP_MISSION)))) return 0;
    if ((c->phase==BTP_COMBAT_NOTICE)!=(c->notice!=0) || (!c->notice && c->notice_return)) return 0;
    if (c->phase==BTP_COMBAT_NOTICE && c->notice_return!=BTP_COMBAT_MENU && c->notice_return!=BTP_COMBAT_CONTROL) return 0;
    unsigned phase=c->notice ? c->notice_return : c->phase;
    if ((phase==BTP_COMBAT_CONTROL || phase==BTP_COMBAT_GRAPHICS) && c->selected>1) return 0;
    if (phase==BTP_COMBAT_MESSAGES && c->selected>2) return 0;
    if (c->phase==BTP_COMBAT_TARGET && c->weapon_selected>=btp_combat_weapon_count(&c->unit[0])) return 0;
    if (c->weapon_selected>btp_combat_weapon_count(&c->unit[0])) return 0;
    if (c->phase==BTP_COMBAT_ROUND && (c->step>12 || (c->step==12 && !s->effects.count))) return 0;
    if (c->goal_active && c->movement>2) return 0;
    if (c->waypoint_count>11 || (c->waypoint_count && !c->goal_active) ||
        (c->phase==BTP_COMBAT_REPLACE && (c->selected>2 || c->target_selected>1))) return 0;
    for (unsigned i=0;i<11;++i) {
        if (i<c->waypoint_count ? c->waypoint_x[i]>125 || c->waypoint_y[i]>127 :
            c->waypoint_x[i] || c->waypoint_y[i]) return 0;
    }
    for (unsigned i=0;i<12;++i) {
        unsigned id=i==11 ? c->kick_target : c->orders[i];
        if (id!=255 && (btp_combat_target(c,id)<1 || btp_combat_target(c,id)>=c->count)) return 0;
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
        if ((u->record[0]!=255 && (u->x>(u->infantry ? 127u : 125u) || u->y>127)) || u->direction>7 || u->heat>30 || u->burning>3 ||
            (u->cover!=0 && u->cover!=(u->infantry ? 2 : 8) && u->cover!=(u->infantry ? 4 : 16)) || c->moved[i]>12 || c->path_index[i]>12 ||
            c->walk[i]>15 || c->plan_direction[i]>7 || c->fallback[i]>7 || u->infantry>1 ||
            (i && !s->campaign.encounter && u->infantry!=(s->mission.assignment==3)) || btp_combat_weapon_count(u)>11 || u->record[117]>3 || u->record[118]>2 || u->record[119]>2) return 0;
        if (u->infantry && (u->record[1]<2 || u->record[1]>12 || u->record[11]>13 || u->record[15]>120)) return 0;
        if (i) {
            if (i>=(c->friends ? c->friends : 1u)) alive+=u->record[0]!=255;
            unsigned movement=i==1 ? c->enemy_movement : c->enemy_modes[i-2];
            if ((movement>(i<c->friends ? 2u : 1u) && movement!=255) || c->enemy_fired[i-1]>=4096) return 0;
            for (unsigned w=0;w<12;++w) if (c->enemy_orders[i-1][w]!=255 && (c->friends ? btp_combat_target(c,c->enemy_orders[i-1][w])>=c->count : c->enemy_orders[i-1][w]!=0)) return 0;
        }
        for (unsigned j=0;j<12;++j) for (unsigned k=0;k<2;++k) if (c->path[i][j][k]<-1 || c->path[i][j][k]>2) return 0;
    }
    unsigned jason=btp_combat_target(c,4);
    int lost=s->campaign.encounter ? jason<c->count && c->unit[jason].record[0]==255 : c->unit[0].record[0]==255;
    return lost==(c->lost!=0 || s->effects.pending==2) &&
        (!alive)==(c->won!=0 || s->effects.pending==1);
}
