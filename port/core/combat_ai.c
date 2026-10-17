#include "core/combat_ai.h"
#include "core/combat.h"
#include "core/spy.h"
#include "data/unit_data.h"
#include <limits.h>
#include <stdlib.h>
#include <string.h>

enum { TARGETS=4, DESTINATIONS=28 };
static const int dx[8]={0,1,1,1,0,-1,-1,-1},dy[8]={-1,-1,0,1,1,1,0,-1};
unsigned btp_combat_actor_skill(const BtpState *s,unsigned actor,unsigned weapon)
{
    const BtpCombatUnit *a=&s->combat.unit[actor];
    if (s->party.enabled && !a->infantry && a->record[121]<8)
        return s->party.people[a->record[121]][weapon==11 ? 8 : 7];
    return actor ? 0u : s->mech_skills[weapon==11 ? 1 : 0];
}
static int eligible(const BtpState *s,unsigned actor,unsigned target)
{
    const BtpCombatState *c=&s->combat;unsigned friends=c->friends ? c->friends : 1u;
    return target<c->count && (actor<friends)!=(target<friends) && c->unit[target].record[0]!=255 &&
        !(actor>=friends && c->unit[target].infantry && btp_spy_unit(s,target)) &&
        !(s->campaign.encounter==4 && s->yard.rental && !s->story_flags[35] && btp_combat_id(c,target)==13);
}
static int heat_cost(unsigned heat)
{
    /* Prefer sustained fire. Crossing an accuracy/slowdown threshold costs
       more than a few points of heat, and shutdown is especially expensive. */
    int cost=(int)(heat*8u);
    if (heat>=8) cost+=(int)(heat-7u)*50;
    if (heat>=13) cost+=(int)(heat-12u)*70;
    if (heat>=24) cost+=(int)(heat-23u)*150;
    if (heat>=30) cost+=10000;
    return cost;
}
static int cooling_cost(const BtpCombatUnit *a,unsigned mode,unsigned steps,unsigned terrain,unsigned heat)
{
    BtpCombatUnit copy=*a;
    unsigned pool=copy.pool+heat;if (pool>255) pool=255;copy.pool=(uint8_t)pool;
    btp_combat_cool(&copy,mode==255 ? -1 : (int)mode,steps,terrain);
    return heat_cost(copy.heat);
}
static int shot_value(BtpAttackQuery q,const BtpCombatUnit *a,unsigned mount)
{
    if (!q.valid || !q.hit36) return 0;
    int value=(int)(q.damage36*q.hit36*100u/1296u);
    if (mount<10 && a->record[39+mount]!=255) {
        unsigned ammo=a->record[39+mount];value-=ammo<4 ? 45 : 8;
    }
    return value>0 ? value : 0;
}
static int volley(const BtpState *s,const BtpResources *r,const BtpCombatUnit *a,
    const BtpCombatUnit *target,unsigned actor,unsigned mode,unsigned steps,unsigned terrain,uint8_t orders[12],unsigned id)
{
    int value[12]={0};unsigned heat[12]={0};uint16_t used=0;
    unsigned total_heat=0;int total=-cooling_cost(a,mode,steps,terrain,0);
    memset(orders,255,12);
    for (unsigned w=0;w<12;++w) {
        if (w==10) continue;
        BtpAttackQuery q=btp_combat_query(a,target,&r->combat,btp_active_combat_profile(s,r),w,
            mode==255 ? -1 : (int)mode,0,btp_combat_actor_skill(s,actor,w),btp_combat_id(&s->combat,actor),s->explored);
        value[w]=shot_value(q,a,w);heat[w]=q.heat;
    }
    /* A bounded marginal-utility selection gives position scoring a cooling-
       aware volley. Live firing rechecks eligibility as units move/die. */
    for (unsigned n=0;n<11;++n) {
        int best=0;unsigned mount=12;
        int before=cooling_cost(a,mode,steps,terrain,total_heat);
        for (unsigned w=0;w<12;++w) if (!(used&(1u<<w)) && value[w]) {
            int gain=value[w]+before-cooling_cost(a,mode,steps,terrain,total_heat+heat[w]);
            if (gain>best) { best=gain;mount=w; }
        }
        if (mount==12) break;
        used|=(uint16_t)(1u<<mount);total_heat+=heat[mount];total+=best;orders[mount]=(uint8_t)id;
    }
    return total;
}
static int inside(const BtpState *s,int x,int y)
{
    if (s->campaign.invasion) return !btp_invasion_outside((unsigned)(1472+x),(unsigned)(1472+y));
    if (s->campaign.encounter==4 && s->story_flags[35] &&
        (int)s->campaign.battle_x+x>1152 && (int)s->campaign.battle_x+x<1287) return 0;
    /* Do not turn a support reposition into the player's map-edge escape. */
    return x>=2 && x<=123 && y>=2 && y<=125;
}
static int candidate(const BtpState *s,const BtpResources *r,const BtpMap *map,unsigned actor,
    const unsigned targets[TARGETS],unsigned count,unsigned mode,int x,int y,BtpAiPlan *out)
{
    const BtpCombatState *c=&s->combat;BtpCombatUnit a=c->unit[actor];
    *out=(BtpAiPlan){.movement=(uint8_t)mode,.target=255,.score=INT_MIN};memset(out->path,2,sizeof out->path);
    if (mode!=255) btp_combat_plan_actor(map,s,actor,x,y,mode,out->path);
    for (unsigned i=0;i<12;++i) {
        int mx=out->path[i][0],my=out->path[i][1];if (mx==2 || my==2) break;
        int nx=(int)a.x+mx,ny=(int)a.y+my;
        if (!inside(s,nx,ny)) { memset(out->path+i,2,(12u-i)*2u);break; }
        if (mx || my) { ++out->steps;a.direction=(uint8_t)btp_combat_direction(a.x,a.y,nx,ny); }
        a.x=(uint8_t)nx;a.y=(uint8_t)ny;
    }
    if (!out->steps) mode=255;
    out->movement=(uint8_t)mode;out->x=a.x;out->y=a.y;out->direction=a.direction;
    unsigned terrain;a.cover=(uint8_t)btp_combat_cover(map,&a,&terrain);
    int threat=0;
    for (unsigned i=0;i<count;++i) {
        unsigned target=targets[i];BtpCombatUnit t=c->unit[target];unsigned ground;
        t.cover=(uint8_t)btp_combat_cover(map,&t,&ground);
        int visible=btp_combat_scene_los(r,s,map,a.x,a.y,t.x,t.y)>0;
        uint8_t orders[12];memset(orders,255,sizeof orders);
        unsigned distance=btp_combat_distance(a.x,a.y,t.x,t.y);
        int score=visible ? volley(s,r,&a,&t,actor,mode,out->steps,terrain,orders,btp_combat_id(c,target)) : -500;
        int armed=0;for (unsigned w=0;w<12;++w) armed|=orders[w]!=255;
        /* No useful shot: make progress toward a target/clear ray rather than
           winning by standing still forever outside every usable weapon. */
        if (!armed) score-=(int)distance*30;
        if (score>out->score) {
            out->score=score;out->target=(uint8_t)target;memcpy(out->orders,orders,12);
            if (!out->steps) {
                unsigned direction=btp_combat_direction(a.x,a.y,t.x,t.y);
                if (direction<8) out->direction=(uint8_t)direction;
            }
        }
        if (btp_combat_scene_los(r,s,map,t.x,t.y,a.x,a.y)>0) {
            /* Current observable loadout only; never inspect future enemy
               orders or draw RNG to guess the next hit. */
            for (unsigned w=0;w<10;++w) {
                BtpAttackQuery q=btp_combat_query(&t,&a,&r->combat,btp_active_combat_profile(s,r),w,0,out->steps,
                    btp_combat_actor_skill(s,target,w),btp_combat_id(c,target),s->explored);
                threat+=shot_value(q,&t,w);
            }
        }
    }
    out->score-=threat*3/4+(int)out->steps*6;
    if (!out->steps) out->score+=35; /* Stay within a useful firing band. */
    /* Avoid reserved allied destinations in addition to actual occupancy. */
    unsigned friends=c->friends ? c->friends : 1u;
    for (unsigned i=0;i<c->count;++i) if (i!=actor && (i<friends)==(actor<friends) && c->unit[i].record[0]!=255) {
        int tx=c->unit[i].x,ty=c->unit[i].y;
        for (unsigned j=0;j<12 && c->path[i][j][0]!=2 && c->path[i][j][1]!=2;++j) { tx+=c->path[i][j][0];ty+=c->path[i][j][1]; }
        if (abs((int)a.x-tx)<3 && abs((int)a.y-ty)<2) out->score-=250;
    }
    return out->target!=255;
}
int btp_combat_ai_plan(const BtpState *s,const BtpResources *r,const BtpMap *map,unsigned actor,BtpAiPlan *out)
{
    const BtpCombatState *c=&s->combat;
    if (!out || actor>=c->count || c->unit[actor].record[0]==255 || c->unit[actor].infantry || !btp_active_combat_profile(s,r)) return 0;
    unsigned targets[TARGETS],count=0;const BtpCombatUnit *a=&c->unit[actor];
    /* Nearest four eligible actors, stable original unit ID for ties. */
    for (unsigned i=0;i<c->count;++i) if (eligible(s,actor,i)) {
        unsigned at=0,d=btp_combat_distance(a->x,a->y,c->unit[i].x,c->unit[i].y);
        while (at<count) {
            unsigned j=targets[at],other=btp_combat_distance(a->x,a->y,c->unit[j].x,c->unit[j].y);
            if (d<other || (d==other && btp_combat_id(c,i)<btp_combat_id(c,j))) break;
            ++at;
        }
        if (at<TARGETS) {
            if (count<TARGETS) ++count;
            for (unsigned j=count-1;j>at;--j) targets[j]=targets[j-1];
            targets[at]=i;
        }
    }
    if (!count) return 0;
    candidate(s,r,map,actor,targets,count,255,a->x,a->y,out);unsigned examined=1;
    int destinations[DESTINATIONS][2];unsigned n=0;
    for (unsigned radius=0;radius<3;++radius) for (unsigned d=0;d<8;++d) {
        int length=radius==0 ? 2 : radius==1 ? 6 : 12;
        destinations[n][0]=a->x+length*dx[d];destinations[n++][1]=a->y+length*dy[d];
    }
    for (unsigned i=0;i<count;++i) { destinations[n][0]=c->unit[targets[i]].x;destinations[n++][1]=c->unit[targets[i]].y; }
    for (unsigned mode=0;mode<3;++mode) if (btp_combat_points(a,mode)>0) for (unsigned d=0;d<n;++d) {
        BtpAiPlan next;candidate(s,r,map,actor,targets,count,mode,destinations[d][0],destinations[d][1],&next);++examined;
        if (next.score>out->score) *out=next;
    }
    out->candidates=examined;return 1;
}
