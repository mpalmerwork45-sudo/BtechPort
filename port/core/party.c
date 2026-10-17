#include "core/party.h"
#include "core/roster_game.h"
#include "core/cache.h"
#include "core/combat_rules.h"
#include "core/animation.h"
#include "core/npc.h"
#include "core/combat.h"
#include "core/world.h"
#include "core/events.h"
#include <stdlib.h>
#include <string.h>
unsigned btp_party_count(const BtpPartyState *p)
{
    unsigned n=0;if (p->enabled) for (unsigned i=0;i<8;++i) n+=p->people[i][0]!=255;return n;
}
unsigned btp_party_slot(const BtpPartyState *p,unsigned ordinal)
{
    if (!p->enabled) return ordinal ? 8u : 0u;
    for (unsigned i=0;i<8;++i) if (p->people[i][0]!=255) { if (!ordinal) return i;--ordinal; }
    return 8;
}
unsigned btp_party_ordinal(const BtpPartyState *p,unsigned slot)
{
    unsigned n=0;for (unsigned i=0;i<slot && i<8;++i) n+=p->people[i][0]!=255;return n;
}
uint8_t *btp_party_mech(BtpState *s,unsigned slot)
{
    return slot<4 ? slot ? s->party.mechs[slot-1] : s->campaign.mech : NULL;
}
const char *btp_character_name(unsigned id)
{
    /* Original DS:01CA name pointers, captured from the unpacked image. */
    static const char *const names[10]={"Jason","Rex","Edward","Russ","Rick","Zeke","Possum","Marco","Rusty","Hunter"};
    return id<10 ? names[id] : "Empty";
}
const char *btp_party_name(const BtpPartyState *p,unsigned slot)
{
    return btp_character_name(slot<8 ? p->people[slot][0] : 255);
}
const char *btp_content_character_name(const BtpResources *r,unsigned id)
{
    const BtpAdventure *a=btp_adventure(r);
    if (a) for (unsigned i=0;i<a->person_count;++i)
        if (a->people[i].record[0]==id && a->people[i].name[0]) return a->people[i].name;
    return btp_character_name(id);
}
const char *btp_content_party_name(const BtpResources *r,const BtpState *s,unsigned slot)
{
    const BtpAdventure *a=btp_adventure(r);
    if (a && slot<8 && s->event.people[slot]<a->person_count && s->party.people[slot][0]!=255) {
        const char *name=a->people[s->event.people[slot]].name;
        if (*name) return name;
    }
    return btp_party_name(&s->party,slot);
}
void btp_party_init(BtpState *s)
{
    BtpPartyState *p=&s->party;if (p->enabled) return;
    *p=(BtpPartyState){.enabled=1,.next_id=1};
    for (unsigned i=0;i<8;++i) { p->people[i][0]=255;p->x[i]=s->campaign.world_x;p->y[i]=s->campaign.world_y; }
    static const uint8_t jason[17]={0,8,9,7,0,0,0,0,1,0,0,0,8,0,0,80,0};
    memcpy(p->people[0],jason,17);memset(p->mech_types,255,4);
    for (unsigned i=1;i<4;++i) { uint8_t *m=btp_party_mech(s,i);m[0]=m[121]=m[122]=255; }
    if (!s->campaign.owned) s->campaign.mech[0]=s->campaign.mech[121]=s->campaign.mech[122]=255;
    if (s->campaign.owned) p->mech_types[0]=s->campaign.mech[0];
    for (unsigned i=0;i<4;++i) { p->mech_x[i]=s->campaign.world_x;p->mech_y[i]=s->campaign.world_y; }
    btp_party_sync(s);
}
void btp_party_allocate(BtpState *s,unsigned member,unsigned slot,unsigned seat)
{
    if (member>=8 || s->party.people[member][0]==255 || slot>4 || (slot<4 && (btp_party_mech(s,slot)[0]==255 || seat<121 || seat>122 || (seat==121 && !s->party.people[member][8])))) return;
    for (unsigned i=0;i<4;++i) for (unsigned k=121;k<=122;++k) if (btp_party_mech(s,i)[k]==member) btp_party_mech(s,i)[k]=255;
    s->party.people[member][12]=8;
    if (slot<4) {
        uint8_t *m=btp_party_mech(s,slot);unsigned old=m[seat];
        if (old<8) {
            if (seat==121) {
                if (m[122]<8) s->party.people[m[122]][12]=8;
                m[122]=(uint8_t)old;
            } else s->party.people[old][12]=8;
        }
        m[seat]=(uint8_t)member;s->party.people[member][12]=(uint8_t)slot;
    }
    s->campaign.mounted=(uint8_t)(s->party.people[0][12]<4);
}
void btp_party_transfer(BtpState *s,unsigned giver,unsigned recipient,unsigned item)
{
    if (giver>=8 || recipient>=8 || giver==recipient || item>1 || s->party.people[giver][0]==255 || s->party.people[recipient][0]==255) return;
    unsigned at=item ? 13u : 11u;s->party.people[recipient][at]=s->party.people[giver][at];s->party.people[giver][at]=0;
    if (item) { s->party.people[recipient][14]=s->party.people[giver][14];s->party.people[giver][14]=0; }
    s->weapon=s->party.people[0][11];s->armor=s->party.people[0][13];s->armor_points=s->party.people[0][14];
}
static unsigned structure(const uint8_t m[125],unsigned component)
{
    static const unsigned ends[]={58,65,72,79,81,83,85,86},parts[]={28,29,33,34,30,35,32,31};
    if (m[123]==200 && !btp_roster_custom(m)) return 1;
    for (unsigned i=0;i<8;++i) if (component<ends[i]) return m[parts[i]];
    return 0;
}
unsigned btp_party_field_salvage(BtpState *s,const uint8_t wrecks[4][125],const uint8_t marked[4])
{
    unsigned skill=0,technician=0,donors=0,reward=0;
    for (unsigned i=0;i<8;++i) if (s->party.people[i][0]!=255 && s->party.people[i][9]>skill) { skill=s->party.people[i][9];technician=i; }
    if (!skill) return 0;
    for (unsigned i=0;i<4;++i) donors+=marked[i]!=0;
    for (unsigned kind=0;kind<(skill>=4 ? 2u : 1u);++kind) {
        unsigned first=kind ? 28u : 17u,last=kind ? 35u : 27u,pool=0;
        for (unsigned i=0;i<4;++i) if (marked[i]) for (unsigned j=first;j<=last;++j) pool+=wrecks[i][j];
        for (unsigned j=last+1;j-->first;) for (unsigned i=0;i<4;++i) {
            uint8_t *m=btp_party_mech(s,i);if (m[0]==255) continue;
            unsigned missing=m[j+69]>m[j] ? (unsigned)m[j+69]-m[j] : 0u,amount=missing<pool ? missing : pool;
            m[j]=(uint8_t)(m[j]+amount);pool-=amount;
        }
    }
    unsigned pool[35]={0};
    for (unsigned i=0;i<4;++i) if (marked[i]) for (unsigned j=51;j<=85;++j) {
        unsigned type=wrecks[i][j];if (type==34 || (type>=16 && type<=32)) ++pool[type];
    }
    for (unsigned kind=0;kind<2;++kind) {
        if (skill<(kind ? 3u : 2u)) continue;
        for (unsigned i=0;i<4;++i) {
            uint8_t *m=btp_party_mech(s,i);if (m[0]==255) continue;
            for (unsigned j=51;j<=85;++j) {
                unsigned type=m[j]&127u;
                if ((m[j]&128u) && (kind ? type>=16 && type<=32 : type==34) && pool[type] && structure(m,j)) { m[j]&=127u;--pool[type]; }
            }
        }
    }
    if (donors && technician) {
        for (unsigned i=0;i<donors;++i) reward+=(btp_rng_next(s->npc.rng)&127u)+90u;
        reward*=technician;s->credits+=reward;
    }
    return reward;
}
void btp_heal_character(uint8_t p[17],unsigned code,uint8_t rng[3])
{
    unsigned maximum=10u*p[1];if (p[0]==255 || p[15]==maximum) return;
    unsigned n=0;for (unsigned k=0;k<(code&15u);++k) n+=btp_combat_die(rng);
    n*=code&240u ? code>>4 : 1u;n+=p[15];p[15]=(uint8_t)(n>maximum ? maximum : n);
}
unsigned btp_party_heal(BtpState *s,const BtpResources *r,unsigned hospital)
{
    btp_party_init(s);if (s->story_flags[41]) return 0;
    unsigned skill=0,injured=0,equipment=1,changed=0;
    for (unsigned i=0;i<8;++i) if (s->party.people[i][0]!=255) {
        if (s->party.people[i][10]>skill) skill=s->party.people[i][10];
        injured|=s->party.people[i][15]!=10u*s->party.people[i][1];
    }
    s->story_flags[25]=(uint8_t)injured;if (!injured) return 0;
    if (s->party.medical_kit) equipment=2;
    if (skill>=3 && s->party.advanced_kit) equipment=3;
    if (hospital) { skill=hospital;equipment=hospital>2 ? 4u : 2u; }
    if (skill>7) return 0;
    unsigned code=r->combat.medical[skill][equipment-1];if (!code) return 0;
    for (unsigned i=0;i<8;++i) {
        uint8_t *p=s->party.people[i];unsigned before=p[15];btp_heal_character(p,code,s->npc.rng);
        if (p[15]>before) changed+=p[15]-before;
    }
    s->story_flags[41]=63;return changed;
}
void btp_party_sync(BtpState *s)
{
    if (!s->party.enabled) return;
    uint8_t *p=s->party.people[0];
    memcpy(p+4,s->skills,3);memcpy(p+7,s->mech_skills,2);p[9]=s->technician;
    p[11]=s->weapon;p[12]=(uint8_t)(s->campaign.mounted ? p[12]<4 ? p[12] : 0 : 8);p[13]=s->armor;p[14]=s->armor_points;
    p[16]=(uint8_t)((p[16]&254u)|s->apprentice);
    s->party.x[0]=s->campaign.world_x;s->party.y[0]=s->campaign.world_y;
    s->party.walk[0]=s->player_walk;s->party.direction[0]=(uint8_t)btp_player_direction(s->facing);
}
int btp_party_recruit(BtpState *s,unsigned skill)
{
    if (skill>6) return 0;
    btp_party_init(s);BtpPartyState *p=&s->party;
    unsigned slot=0;while (slot<8 && p->people[slot][0]!=255) ++slot;if (slot==8) return 0;
    uint8_t *a=p->people[slot];memset(a,0,17);
    unsigned seed=p->next_id*391u;for (unsigned i=0;i<3;++i) s->npc.rng[i]=(uint8_t)(seed>>(i*8));
    a[0]=p->next_id++;if (p->next_id>=10) p->next_id=2;
    a[1]=(uint8_t)btp_combat_dice(s->npc.rng);a[2]=(uint8_t)btp_combat_dice(s->npc.rng);a[3]=(uint8_t)btp_combat_dice(s->npc.rng);
    a[15]=(uint8_t)(a[1]*10);a[12]=8;
    for (unsigned i=0;i<7;++i) a[4+i]=(uint8_t)(btp_rng_next(s->npc.rng)&1u);
    a[8]=0;a[4+skill]=3;if (skill==4) a[15]=(uint8_t)(a[15]-2*a[1]);
    for (unsigned i=0;i<4;++i) {
        uint8_t *m=btp_party_mech(s,i);
        if (s->party.mech_types[i]!=255 && m[0]!=255 && m[122]==255) { m[122]=(uint8_t)slot;a[12]=(uint8_t)i;break; }
    }
    p->x[slot]=s->campaign.world_x;p->y[slot]=s->campaign.world_y;
    return (int)slot+1;
}
int btp_party_walkable(const BtpState *s,const BtpResources *r,int x,int y,int mech)
{
    const BtpScene *scene=btp_scene(r,s);
    if (scene) return btp_scene_stand(scene,x-(int)(2*scene->origin_x),y-(int)(2*scene->origin_y),mech);
    if (x<0 || y<0 || x>=2048 || y>=2048) return 0;
    /* Cache corridors use their own tile gate and origin. Testing the
       generated terrain underneath would hide perfectly legal followers. */
    if (s->cache.active) {
        x-=1536;y-=1536;
        return !mech && x>=0 && y>=0 && btp_cache_tile(r,s,(x+1)/2,y/2)<s->gate;
    }
    /* People sample their foot point; a vehicle occupies both ground tiles.
       Stored vehicle Y is its ground anchor, already two steps above the
       party cursor. The arena's temporary gate does not apply outdoors. */
    if (mech) return x<2046 && btp_world_tile(r,s,x/2,y/2)<85 && btp_world_tile(r,s,x/2+1,y/2)<85;
    return btp_world_tile(r,s,(x+1)/2,y/2)<85;
}
int btp_party_can_stand(const BtpState *s,const BtpResources *r,int x,int y)
{
    /* 0000:1C12 tests every compact foot/mech position before accepting a
       cursor step. An outer member hitting a wall stops the whole formation;
       letting the leader advance and sending followers around it clips roofs. */
    if (!s->party.enabled) return btp_party_walkable(s,r,x,y-(s->campaign.mounted ? 2 : 0),s->campaign.mounted);
    unsigned person=0,mech=0;
    for (unsigned i=0;i<8;++i) if (s->party.people[i][0]!=255 && s->party.people[i][12]>=8) {
        unsigned place=person++;
        if (!btp_party_walkable(s,r,x+r->combat.formation_x[place],y+r->combat.formation_y[place],0)) return 0;
    }
    for (unsigned i=0;i<4;++i) {
        const uint8_t *record=i ? s->party.mechs[i-1] : s->campaign.mech;
        if (record[0]==255) continue; /* Owned vehicles parked at Starport stay put. */
        unsigned place=mech++;
        if (!btp_party_walkable(s,r,x+r->combat.mech_formation_x[place],y+r->combat.mech_formation_y[place],1)) return 0;
    }
    return 1;
}
int btp_party_entrance(const BtpState *s,const BtpResources *r,const BtpMap *m,int x,int y)
{
    /* 0000:1DD4/2027 checks compact members in drawing order. A foot
       soldier can touch the door exactly; either side of a mech can do so.
       An earlier blocked member ends the scan, just like the DOS wall test. */
    const BtpScene *scene=btp_scene(r,s);
    int ox=scene ? (int)(2*scene->origin_x) : (m->entrance_x[0]>>8)*128;
    int oy=scene ? (int)(2*scene->origin_y) : (m->entrance_y[0]>>12)*128;
    unsigned person=0,mech=0;
    for (unsigned i=0;i<12;++i) {
        int px,py,vehicle=i>=8;
        if (!vehicle) {
            if (s->party.people[i][0]==255 || s->party.people[i][12]<8) continue;
            px=x+r->combat.formation_x[person];py=y+r->combat.formation_y[person++];
        } else {
            const uint8_t *record=i==8 ? s->campaign.mech : s->party.mechs[i-9];
            if (record[0]==255) continue;
            px=x+r->combat.mech_formation_x[mech];py=y+r->combat.mech_formation_y[mech++];
        }
        if (scene) {
            /* Authored markers use the same ground contact as DOS doors,
               including an outer mech's second tile. A recruited NPC no
               longer occupies its old marker. Do this before the member's
               wall check, preserving original first-contact ordering. */
            for (unsigned door=0;door<scene->entrance_count;++door) {
                const BtpSceneEntrance *e=&scene->entrances[door];int recruited=0;
                if (e->person!=255) for (unsigned k=0;k<8;++k)
                    if (s->party.people[k][0]!=255 && s->event.people[k]==e->person) recruited=1;
                if (!recruited && py==e->y && abs(px-e->x)<=vehicle) return (int)door;
            }
        } else {
            if (!vehicle && btp_broker_door(s,r,px,py)) return BTP_BROKER_ENTRY;
            for (unsigned door=0;door<12;++door) if (m->entrance_x[door] && m->entrance_y[door] &&
                py==(m->entrance_y[door]&127) && abs(px-(m->entrance_x[door]&127))<=vehicle) return (int)door;
        }
        if (!btp_party_walkable(s,r,ox+px,oy+py,vehicle)) return -1;
    }
    return -1;
}
static int follow_step(const BtpState *s,const BtpResources *r,int x,int y,int nx,int ny,int mech)
{
    return btp_party_walkable(s,r,nx,ny,mech) &&
        (btp_scene(r,s) || s->cache.active || btp_world_location(r,s,nx/2,ny/2) ||
         !btp_world_deep_crossing(r,s,(unsigned)x,(unsigned)y,nx-x,ny-y));
}
static void follow_position(const BtpState *s,const BtpResources *r,uint16_t *px,uint16_t *py,int gx,int gy,int mech,int initialize)
{
    int x=*px,y=*py;
    if (initialize || !btp_party_walkable(s,r,x,y,mech)) {
        /* Imported saves do not contain outdoor formation positions. Recover
           a legal position near the original formation before the first draw. */
        int best=INT32_MAX,bx=x,by=y;
        for (int dy=-8;dy<=8;++dy) for (int dx=-8;dx<=8;++dx)
            if (btp_party_walkable(s,r,gx+dx,gy+dy,mech) && dx*dx+dy*dy<best)
                { best=dx*dx+dy*dy;bx=gx+dx;by=gy+dy; }
        if (best<INT32_MAX) { *px=(uint16_t)bx;*py=(uint16_t)by; }
        return;
    }
    if (x==gx && y==gy) return;
    /* Preserve the original compact formation on clear ground, checking
       every half-step rather than teleporting a follower through a roof. */
    int tx=x,ty=y,clear=abs(gx-x)<=8 && abs(gy-y)<=8;
    while (clear && (tx!=gx || ty!=gy)) {
        int nx=tx+(gx>tx)-(gx<tx),ny=ty+(gy>ty)-(gy<ty);
        if (!follow_step(s,r,tx,ty,nx,ny,mech)) clear=0;
        else { tx=nx;ty=ny; }
    }
    if (clear) { *px=(uint16_t)tx;*py=(uint16_t)ty;return; }
    /* A small local search lets each blocked follower go around obstacles.
       Its first step is applied now; buildings never become legal positions.
       The normal unobstructed path above requires no search or allocation. */
    enum { SIDE=9,CELLS=SIDE*SIDE,CENTER=4*SIDE+4 };
    int16_t parent[CELLS],queue[CELLS];unsigned head=0,tail=0;int best=CENTER;
    for (unsigned i=0;i<CELLS;++i) parent[i]=-1;
    parent[CENTER]=CENTER;queue[tail++]=CENTER;
    int distance=abs(gx-x)+abs(gy-y);
    static const BtpAction directions[8]={BTP_UP,BTP_UP_RIGHT,BTP_RIGHT,BTP_DOWN_RIGHT,
        BTP_DOWN,BTP_DOWN_LEFT,BTP_LEFT,BTP_UP_LEFT};
    while (head<tail) {
        int at=queue[head++],cx=at%SIDE,cy=at/SIDE;
        for (unsigned direction=0;direction<8;++direction) {
            int nx=cx+btp_action_dx(directions[direction]),ny=cy+btp_action_dy(directions[direction]);
            if (nx<0 || ny<0 || nx>=SIDE || ny>=SIDE) continue;
            int next=ny*SIDE+nx;if (parent[next]>=0) continue;
            if (!follow_step(s,r,x+cx-4,y+cy-4,x+nx-4,y+ny-4,mech)) continue;
            parent[next]=(int16_t)at;queue[tail++]=(int16_t)next;
            int score=abs(gx-(x+nx-4))+abs(gy-(y+ny-4));
            if (score<distance) { best=next;distance=score; }
        }
    }
    if (best!=CENTER) {
        while (parent[best]!=CENTER) best=parent[best];
        *px=(uint16_t)(x+best%SIDE-4);*py=(uint16_t)(y+best/SIDE-4);
    }
}
static void party_follow(BtpState *s,const BtpResources *r,uint16_t old_x,uint16_t old_y,int regroup)
{
    BtpPartyState *p=&s->party;if (!p->enabled) return;
    /* 0000:0BC9..0D30 supplies the two compact formations. Each follower
       checks its own footprint before joining that formation. Passengers do
       not take a person position. Saved positions drive the visible sprites. */
    unsigned person=0,mech=0;
    int initialize=1;
    for (unsigned i=0;i<8;++i) if (p->people[i][0]!=255 && p->people[i][12]>=8 &&
        (p->x[i]!=old_x || p->y[i]!=old_y)) initialize=0;
    for (unsigned i=0;i<4;++i) if (btp_party_mech(s,i)[0]!=255 &&
        (p->mech_x[i]!=old_x || p->mech_y[i]!=old_y)) initialize=0;
    if (regroup) initialize=1;
    /* 0000:0BC9..0D30 rebuilds a compact formation, not independent paths.
       Authored movement has already checked every member at the destination.
       Place that accepted formation exactly, so followers cannot get caught
       on a generated-world water boundary or an irrelevant detour. Retain
       the documented recovery search for imported/scattered illegal states. */
    int compact=btp_scene(r,s) && btp_party_can_stand(s,r,s->campaign.world_x,s->campaign.world_y);
    for (unsigned i=0;i<8;++i) if (p->people[i][0]!=255 && p->people[i][12]>=8) {
        unsigned ox=p->x[i],oy=p->y[i],place=person++;
        int gx=(int)s->campaign.world_x+r->combat.formation_x[place];
        int gy=(int)s->campaign.world_y+r->combat.formation_y[place];
        if (compact) { p->x[i]=(uint16_t)gx;p->y[i]=(uint16_t)gy; }
        else follow_position(s,r,&p->x[i],&p->y[i],gx,gy,0,initialize);
        if (initialize && (old_x!=s->campaign.world_x || old_y!=s->campaign.world_y))
            p->direction[i]=(uint8_t)btp_player_direction(s->facing);
        if (!initialize && i && (p->x[i]!=ox || p->y[i]!=oy)) {
            unsigned dir=btp_combat_direction((int)ox,(int)oy,p->x[i],p->y[i]);
            p->walk[i]=btp_walk_next(p->walk[i],p->direction[i],dir);p->direction[i]=(uint8_t)dir;
        }
    }
    for (unsigned i=0;i<4;++i) if (btp_party_mech(s,i)[0]!=255) {
        unsigned ox=p->mech_x[i],oy=p->mech_y[i],place=mech++;
        int gx=(int)s->campaign.world_x+r->combat.mech_formation_x[place];
        int gy=(int)s->campaign.world_y+r->combat.mech_formation_y[place];
        if (compact) { p->mech_x[i]=(uint16_t)gx;p->mech_y[i]=(uint16_t)gy; }
        else follow_position(s,r,&p->mech_x[i],&p->mech_y[i],gx,gy,1,initialize);
        unsigned pilot=btp_party_mech(s,i)[121];
        if (initialize && pilot<8 && (old_x!=s->campaign.world_x || old_y!=s->campaign.world_y))
            p->direction[pilot]=(uint8_t)btp_player_direction(s->facing);
        if (!initialize && pilot<8 && (p->mech_x[i]!=ox || p->mech_y[i]!=oy)) {
            unsigned dir=btp_combat_direction((int)ox,(int)oy,p->mech_x[i],p->mech_y[i]);
            if (pilot) p->walk[pilot]=(uint8_t)btp_combat_walk_frame(p->walk[pilot],p->direction[pilot],dir,0);
            p->direction[pilot]=(uint8_t)dir;
        }
    }
    btp_party_sync(s);
}
void btp_party_follow(BtpState *s,const BtpResources *r,uint16_t old_x,uint16_t old_y)
{
    party_follow(s,r,old_x,old_y,0);
}
void btp_party_recover(BtpState *s,const BtpResources *r,int regroup)
{
    /* TEMPORARY WORKAROUND (user-requested): the 9x9 follower search can
       strand a unit behind an obstacle, making an owned mech disappear off
       screen. Regroup on returning from menus/buildings/battles, or when an
       active follower is over 12 half-steps (six tiles) from its formation
       position. This deliberately teleports; it is not original DOS behaviour.
       TODO: replace with a route search that can escape local dead ends and
       preserve reachable formation positions across scene transitions. Then
       remove this recovery and its call sites, retaining the stranded-party
       regression cases. Never revive wrecks or pull parked Starport mechs in. */
    if (!s->party.enabled || s->combat.phase || s->campaign.encounter || s->yard.active ||
        (s->mode!=BTP_EXPLORE && s->mode!=BTP_CACHE)) return;
    unsigned person=0,mech=0;
    for (unsigned i=0;i<8;++i) if (s->party.people[i][0]!=255 && s->party.people[i][12]>=8) {
        int gx=(int)s->campaign.world_x+r->combat.formation_x[person];
        int gy=(int)s->campaign.world_y+r->combat.formation_y[person++];
        if (abs((int)s->party.x[i]-gx)>12 || abs((int)s->party.y[i]-gy)>12) regroup=1;
    }
    for (unsigned i=0;i<4;++i) if (btp_party_mech(s,i)[0]!=255) {
        int gx=(int)s->campaign.world_x+r->combat.mech_formation_x[mech];
        int gy=(int)s->campaign.world_y+r->combat.mech_formation_y[mech++];
        if (abs((int)s->party.mech_x[i]-gx)>12 || abs((int)s->party.mech_y[i]-gy)>12) regroup=1;
    }
    /* Reuse footprint-checked placement: exact compact offsets on open
       ground, nearest legal tiles if an exit's walls prevent that formation.
       Records, crew, damage, inventory and RNG remain untouched. */
    if (regroup) party_follow(s,r,s->campaign.world_x,s->campaign.world_y,1);
}
void btp_party_encode(const BtpPartyState *p,uint8_t b[BTP_PARTY_BYTES])
{
    memset(b,0,BTP_PARTY_BYTES);if (!p->enabled) return;
    unsigned at=0;b[at++]=p->enabled;b[at++]=p->next_id;memcpy(b+at,p->people,136);at+=136;
    memcpy(b+at,p->mech_types,4);at+=4;memcpy(b+at,p->mechs,375);at+=375;
    for (unsigned i=0;i<8;++i) { b[at++]=(uint8_t)p->x[i];b[at++]=(uint8_t)(p->x[i]>>8);b[at++]=(uint8_t)p->y[i];b[at++]=(uint8_t)(p->y[i]>>8); }
    memcpy(b+at,p->walk,8);at+=8;memcpy(b+at,p->direction,8);at+=8;
    b[at++]=p->selected;b[at++]=p->giver;b[at++]=p->item;b[at++]=p->phase;
    b[at++]=p->medical_kit;b[at++]=p->advanced_kit;
    for (unsigned i=0;i<4;++i) { b[at++]=(uint8_t)p->mech_x[i];b[at++]=(uint8_t)(p->mech_x[i]>>8);b[at++]=(uint8_t)p->mech_y[i];b[at++]=(uint8_t)(p->mech_y[i]>>8); }
}
int btp_party_decode(const uint8_t b[BTP_PARTY_BYTES],BtpPartyState *p)
{
    BtpPartyState v={0};unsigned at=0;v.enabled=b[at++];v.next_id=b[at++];memcpy(v.people,b+at,136);at+=136;
    memcpy(v.mech_types,b+at,4);at+=4;memcpy(v.mechs,b+at,375);at+=375;
    for (unsigned i=0;i<8;++i) { v.x[i]=(uint16_t)(b[at]|(unsigned)b[at+1]<<8);at+=2;v.y[i]=(uint16_t)(b[at]|(unsigned)b[at+1]<<8);at+=2; }
    memcpy(v.walk,b+at,8);at+=8;memcpy(v.direction,b+at,8);at+=8;
    v.selected=b[at++];v.giver=b[at++];v.item=b[at++];v.phase=b[at++];
    v.medical_kit=b[at++];v.advanced_kit=b[at++];
    for (unsigned i=0;i<4;++i) { v.mech_x[i]=(uint16_t)(b[at]|(unsigned)b[at+1]<<8);at+=2;v.mech_y[i]=(uint16_t)(b[at]|(unsigned)b[at+1]<<8);at+=2;if (v.mech_x[i]>2047 || v.mech_y[i]>2047) return 0; }
    for (;at<BTP_PARTY_BYTES;++at) if (b[at]) return 0;
    if (!v.enabled) { for (unsigned i=0;i<BTP_PARTY_BYTES;++i) if (b[i]) return 0;*p=v;return 1; }
    if (v.enabled!=1 || !v.next_id || v.next_id>=10 || v.selected>7 || v.giver>7 || v.item>1 || v.phase>3 || v.medical_kit>1 || v.advanced_kit>1 || (v.people[0][0] && v.people[0][0]!=255)) return 0;
    for (unsigned i=0;i<8;++i) {
        const uint8_t *a=v.people[i];
        if (v.x[i]>2047 || v.y[i]>2047 || v.walk[i]>15 || v.direction[i]>7) return 0;
        if (a[0]==255) continue;
        if (a[0]>=10 || a[1]<2 || a[1]>12 || a[2]<2 || a[2]>12 || a[3]<2 || a[3]>12 || a[11]>13 || a[12]>8 || a[13]>5 || a[15]>120) return 0;
        for (unsigned k=4;k<=10;++k) if (a[k]>5) return 0;
        /* 09B8:0D58 wraps the name counter after Hunter. Replacement agents
           may share a name with a living agent; slots remain their identity. */
    }
    *p=v;return 1;
}
