#include "core/combat.h"
#include "core/npc.h"
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
static int occupied(const BtpCombatUnit *other, int x, int y)
{
    return other && other->record[0] != 255 && y == other->y && abs(x-other->x) < 3;
}
void btp_combat_plan(const BtpMap *m, unsigned gate, const BtpCombatUnit *u,
    const BtpCombatUnit *other, int tx, int ty, unsigned movement, int computer, int8_t steps[12][2])
{
    memset(steps,2,24);
    int x=u->x, y=u->y, points=btp_combat_points(u,movement), stopped=0;
    unsigned heading=computer ? u->direction : btp_combat_direction(x,y,tx,ty);
    for (unsigned i=0; i<12 && points>0 && !stopped && (x!=tx || y!=ty); ++i) {
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
            if (tile_at(m,u->x,u->y,at)>=gate || tile_at(m,u->x,u->y,at+(nx&1 ? -1 : 1))>=gate) continue;
            if (occupied(other,nx,ny)) { if (nx==tx && ny==ty) stopped=1; continue; }
            steps[i][0]=dx[d]; steps[i][1]=dy[d]; x=nx; y=ny; heading=d; break;
        }
        unsigned mask, tile=tile_at(m,u->x,u->y,grid(u->x,u->y,x,y,1,&mask));
        int cost=movement==2 || tile>=64 || !(tile&mask) ? 1 : (tile&240u)==32 ? 3 : 2;
        points-=cost;
    }
}
unsigned btp_combat_cover(const BtpMap *m, const BtpCombatUnit *u, unsigned *terrain)
{
    unsigned tile=btp_map_tile(m,(u->x+1)/2,u->y/2), mask=(u->y&1u) ? 4u : 1u;
    *terrain=tile;
    if (tile>=48 || !(tile&mask)) return 0;
    return (tile&15u)==15 && ((tile&48u)==0 || (tile&48u)==32) ? 16u : 8u;
}
static void menu(BtpCombatState *c)
{
    c->phase=BTP_COMBAT_MENU; c->selected=9;
}
static void notice(BtpCombatState *c, unsigned id, unsigned back)
{
    c->notice=(uint8_t)id;c->notice_return=(uint8_t)back;c->phase=BTP_COMBAT_NOTICE;
}
void btp_combat_begin(BtpState *s, const BtpResources *r)
{
    BtpCombatState *c=&s->combat;
    *c=(BtpCombatState){.phase=BTP_COMBAT_CONTROL,.selected=1,.messages=2,.graphics=1,
        .movement=255,.walk={6,15},.plan_direction={0,6},.enemy_movement=255};
    memset(c->orders,255,sizeof c->orders);
    memcpy(c->unit[0].record,r->combat.loans[s->story_flags[2]],125);
    memcpy(c->unit[1].record,r->combat.loans[0],125);
    c->unit[0].x=64;c->unit[0].y=77;c->unit[0].direction=2;
    (void)btp_rng_next(s->npc.rng);
    c->unit[1].x=114;c->unit[1].y=(uint8_t)(89+(btp_rng_next(s->npc.rng)&7u));c->unit[1].direction=6;
    c->unit[1].record[36]=c->unit[1].record[37]=0;
    memset(c->unit[1].record+39,0,12);
}
static void finish(BtpState *s)
{
    BtpCombatState *c=&s->combat;
    s->x_half=c->unit[0].x;s->y_half=(uint16_t)(c->unit[0].y+2u);
    s->mission.corner=1;s->mission.idle=0;s->mission.walk=c->walk[0];
    s->mission.direction=c->unit[0].direction;c->phase=BTP_COMBAT_NONE;
}
static void begin_round(BtpState *s, const BtpResources *r)
{
    BtpCombatState *c=&s->combat;
    memset(c->path,2,sizeof c->path);
    if (c->goal_active) btp_combat_plan(&r->map,s->gate,&c->unit[0],&c->unit[1],
        c->goal_x,c->goal_y,c->movement,0,c->path[0]);
    /* 0E31:03AB: the weapon-component range scan intentionally uses the
       component value as the table index, even when ammunition is empty. */
    BtpCombatUnit enemy=c->unit[1];enemy.direction=c->plan_direction[1];
    int ex=enemy.x,ey=enemy.y,px=c->unit[0].x,py=c->unit[0].y;
    unsigned distance=btp_combat_distance(ex,ey,px,py),preferred=255;
    int visible=btp_combat_los(&r->map,s->gate,ex,ey,px,py)>0;
    for (unsigned i=51;i<86;++i) {
        unsigned component=enemy.record[i];
        if (component>=16 && component<=32) {
            unsigned value=(r->combat.weapons[component][14]&224u)>>3;
            if (value<preferred) preferred=value;
        }
    }
    if (preferred==255) preferred=0;
    int close=visible && abs(px-ex)<=3 && abs(py-ey)<2;
    c->enemy_movement=255;
    if (close) {
        c->plan_direction[1]=(uint8_t)btp_combat_direction(ex,ey,px,py);
        c->unit[1].direction=c->fallback[1];
    } else if (!visible || !preferred || distance>preferred) {
        int tx=px,ty=py;
        if (visible && preferred) {
            int sx=(px>ex)-(px<ex),sy=(py>ey)-(py<ey);
            tx=ex+sx*(int)(distance-preferred);ty=ey+sy*(int)(distance-preferred);
        }
        c->enemy_movement=enemy.heat ? 0 : 1;
        btp_combat_plan(&r->map,s->gate,&enemy,&c->unit[0],tx,ty,c->enemy_movement,1,c->path[1]);
    }
    memset(c->moved,0,2);memset(c->path_index,0,2);
    c->fired=0;c->step=0;c->delay=0;c->last_event=0;c->phase=BTP_COMBAT_ROUND;
    ++c->round;
}
static void advance(BtpCombatState *c, unsigned index)
{
    BtpCombatUnit *u=&c->unit[index];unsigned p=c->path_index[index];
    if (p>=12) return;
    int mx=c->path[index][p][0], my=c->path[index][p][1];
    if (mx==2 || my==2 || (!mx && !my)) return;
    int x=u->x+mx,y=u->y+my;
    if (occupied(&c->unit[1-index],x,y)) return;
    static const uint8_t frames[8][4]={{0,1,2,3},{4,5,6,7},{6,7,4,5},{5,6,7,4},
        {8,9,10,11},{12,13,14,15},{15,12,13,14},{14,15,12,13}};
    unsigned direction=btp_combat_direction(u->x,u->y,x,y), next=0;
    if (direction==u->direction) for (unsigned i=0;i<4;++i)
        if (frames[direction][i]==c->walk[index]) next=(i+1u)%4u;
    u->direction=(uint8_t)direction;c->plan_direction[index]=(uint8_t)direction;c->walk[index]=frames[direction][next];
    u->x=(uint8_t)x;u->y=(uint8_t)y;++c->moved[index];++c->path_index[index];
}
static void round_tick(BtpState *s, const BtpResources *r)
{
    BtpCombatState *c=&s->combat;
    if (c->delay) { --c->delay;return; } c->delay=2;
    advance(c,0);advance(c,1);
    unsigned terrain[2];
    for (unsigned i=0;i<2;++i) c->unit[i].cover=(uint8_t)btp_combat_cover(&r->map,&c->unit[i],&terrain[i]);
    for (unsigned i=0;i<11;++i) if (c->orders[i]==12 && !(c->fired&(1u<<i))) {
        unsigned w=btp_combat_weapon(&c->unit[0],i);
        if (w>=33) { c->orders[i]=255;continue; }
        if (c->unit[0].heat>=30 || btp_combat_range(&r->combat,w,c->unit[0].x,c->unit[0].y,c->unit[1].x,c->unit[1].y)>=3) continue;
        int los=btp_combat_los(&r->map,s->gate,c->unit[0].x,c->unit[0].y,c->unit[1].x,c->unit[1].y);
        if (!los) { c->last_event=3;continue; }
        if (los<0) { c->last_event=4;continue; }
        /* Terrain ignition is an explicit boundary, before ammo/RNG mutation. */
        if (c->unit[1].cover && terrain[1]>=16 && terrain[1]<=63 && w>=16 && w<=18) { c->last_event=5;continue; }
        c->shot=btp_combat_shoot(&c->unit[0],&c->unit[1],&r->combat,i,
            c->goal_active ? c->movement : -1,c->moved[1],s->mech_skills[0],s->npc.rng);
        c->last_weapon=(uint8_t)i;c->last_event=c->shot.hit ? 1 : 2;c->fired|=(uint16_t)(1u<<i);
        if (c->shot.destroyed) { c->unit[1].record[0]=255;c->unit[1].x=c->unit[1].y=127;c->won=1;finish(s);return; }
        break; /* Original permits one shot per unit per microstep. */
    }
    if (c->goal_active && c->unit[0].x==c->goal_x && c->unit[0].y==c->goal_y) {
        c->goal_active=0;c->movement=255;
    }
    s->x_half=c->unit[0].x;s->y_half=(uint16_t)(c->unit[0].y+2u);
    s->mission.walk=c->walk[0];s->mission.direction=c->unit[0].direction;
    if (++c->step==12) {
        btp_combat_cool(&c->unit[0],c->goal_active ? c->movement : -1,c->moved[0],terrain[0]);
        btp_combat_cool(&c->unit[1],c->enemy_movement==255 ? -1 : c->enemy_movement,c->moved[1],terrain[1]);
        c->delay=0;menu(c);
    }
}
void btp_combat_tick(BtpState *s, const BtpResources *r, BtpAction a)
{
    BtpCombatState *c=&s->combat;
    unsigned count=btp_combat_weapon_count(&c->unit[0]);
    if (c->phase==BTP_COMBAT_ROUND) { round_tick(s,r);return; }
    if (c->phase==BTP_COMBAT_NOTICE) {
        if (a==BTP_ACCEPT || a==BTP_CANCEL) { c->phase=c->notice_return;c->notice=c->notice_return=0; }
        return;
    }
    if (c->phase==BTP_COMBAT_MOVE) {
        if (btp_action_moves(a)) {
            int x=c->cursor_x+btp_action_dx(a), y=c->cursor_y+btp_action_dy(a);
            if (x>=0 && x<2*r->map.width-2 && y>=0 && y<2*r->map.height-2) { c->cursor_x=(uint8_t)x;c->cursor_y=(uint8_t)y; }
        }
        if (a==BTP_ACCEPT) { c->goal_x=c->cursor_x;c->goal_y=c->cursor_y;c->movement=c->selected;c->goal_active=1;menu(c); }
        if (a==BTP_CANCEL) menu(c);
        return;
    }
    if (c->phase==BTP_COMBAT_SCAN) {
        if (a==BTP_LEFT || a==BTP_RIGHT || a==BTP_UP || a==BTP_DOWN) c->scan_unit^=1;
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
    if (c->phase==BTP_COMBAT_TARGET) {
        if (a==BTP_UP) c->target_selected=(uint8_t)((c->target_selected+2u)%3u);
        if (a==BTP_DOWN) c->target_selected=(uint8_t)((c->target_selected+1u)%3u);
        if (a==BTP_CANCEL || (a==BTP_ACCEPT && c->target_selected==2)) {
            c->orders[c->weapon_selected]=255;c->phase=BTP_COMBAT_WEAPONS;
        } else if (a==BTP_ACCEPT && c->target_selected==0) {
            c->orders[c->weapon_selected]=12;++c->weapon_selected;c->phase=BTP_COMBAT_WEAPONS;
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
            if (!btp_combat_points(&c->unit[0],c->selected)) { notice(c,2,BTP_COMBAT_MENU);return; }
            c->cursor_x=c->unit[0].x;c->cursor_y=c->unit[0].y;c->phase=BTP_COMBAT_MOVE;
        } else if (c->selected==3) { c->phase=BTP_COMBAT_WEAPONS;c->weapon_selected=0; }
        else if (c->selected==4 || c->selected==5) notice(c,1,BTP_COMBAT_MENU);
        else if (c->selected==6) { c->scan_unit=0;c->phase=BTP_COMBAT_SCAN; }
        else if (c->selected==7) menu(c);
        else if (c->selected==8) { c->fled=1;finish(s); }
        else begin_round(s,r);
    }
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
    for (;p<BTP_COMBAT_SAVE_BYTES;++p) if (b[p]) return 0;
    return 1;
}
#undef COMBAT_FIELDS
int btp_combat_valid(const BtpState *s)
{
    const BtpCombatState *c=&s->combat;
    if (s->mission.assignment!=2 || !s->mission.phase) {
        uint8_t b[BTP_COMBAT_SAVE_BYTES];btp_combat_encode(c,b);
        for (unsigned i=0;i<sizeof b;++i) if (b[i]) return 0;
        return 1;
    }
    if (c->phase>BTP_COMBAT_NOTICE || c->selected>9 || c->messages>2 || c->graphics>1 ||
        (c->movement>2 && c->movement!=255) || c->goal_active>1 || c->goal_x>125 || c->goal_y>125 ||
        c->cursor_x>125 || c->cursor_y>125 || c->weapon_selected>11 || c->target_selected>2 ||
        c->scan_unit>1 || c->step>12 || c->delay>2 || c->notice>2 || c->notice_return>BTP_COMBAT_SCAN ||
        c->fled>1 || c->won>1 || (c->fled && c->won) || c->last_weapon>10 || c->last_event>5 || c->fired>=2048 ||
        c->shot.hit>1 || c->shot.location>35 || c->shot.destroyed>1 || c->shot.toppled>1 ||
        c->shot.needed < -4 || c->shot.needed>30 || (c->enemy_movement>1 && c->enemy_movement!=255)) return 0;
    if ((!c->phase && !c->fled && !c->won) || (c->phase && (c->fled || c->won || s->mode!=BTP_MISSION))) return 0;
    if ((c->phase==BTP_COMBAT_NOTICE)!=(c->notice!=0) || (!c->notice && c->notice_return)) return 0;
    if (c->phase==BTP_COMBAT_NOTICE && c->notice_return!=BTP_COMBAT_MENU && c->notice_return!=BTP_COMBAT_CONTROL) return 0;
    unsigned phase=c->notice ? c->notice_return : c->phase;
    if ((phase==BTP_COMBAT_CONTROL || phase==BTP_COMBAT_GRAPHICS) && c->selected>1) return 0;
    if (phase==BTP_COMBAT_MESSAGES && c->selected>2) return 0;
    if (c->phase==BTP_COMBAT_TARGET && c->weapon_selected>=btp_combat_weapon_count(&c->unit[0])) return 0;
    if (c->weapon_selected>btp_combat_weapon_count(&c->unit[0])) return 0;
    if (c->phase==BTP_COMBAT_ROUND && c->step>=12) return 0;
    if (c->goal_active && c->movement>2) return 0;
    for (unsigned i=0;i<11;++i) if (c->orders[i]!=12 && c->orders[i]!=255) return 0;
    for (unsigned i=0;i<2;++i) {
        const BtpCombatUnit *u=&c->unit[i];
        if ((u->record[0]!=255 && (u->x>125 || u->y>125)) || u->direction>7 || u->heat>30 || u->burning>3 ||
            (u->cover!=0 && u->cover!=8 && u->cover!=16) || c->moved[i]>12 || c->path_index[i]>12 ||
            c->walk[i]>15 || c->plan_direction[i]>7 || c->fallback[i]>7 || btp_combat_weapon_count(u)>11 || u->record[117]>3 || u->record[118]>2 || u->record[119]>2) return 0;
        for (unsigned j=0;j<12;++j) for (unsigned k=0;k<2;++k) if (c->path[i][j][k]<-1 || c->path[i][j][k]>2) return 0;
    }
    return c->unit[0].record[0]!=255 && (c->unit[1].record[0]==255)==(c->won!=0);
}
