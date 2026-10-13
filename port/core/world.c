#include "core/world.h"
#include "core/training.h"
#include "core/animation.h"
#include "core/npc.h"
#include "core/campaign.h"
#include "core/party.h"
#include "core/economy.h"
#include "core/menu.h"
#include "core/yard.h"
#include <string.h>
#include <stdlib.h>

void btp_world_reveal(BtpState *s)
{
    unsigned x=s->story_flags[4] ? s->campaign.world_x : 1536u+s->x_half;
    unsigned y=s->story_flags[4] ? s->campaign.world_y : 1536u+s->y_half;
    if (x>=2048 || y>=2048 || s->story_flags[58]) return;
    unsigned at=y/16u*16u+x/128u;
    if (s->story_flags[49]) {
        at=y/128u*128u+x/128u;
        for (unsigned i=0;i<8;++i) s->explored[at+16u*i]=255;
    } else {
        static const uint8_t masks[]={224,224,112,56,28,14,7,7};
        unsigned mask=masks[(x&127u)/16u];s->explored[at]|=(uint8_t)mask;
        if (at>=16) s->explored[at-16]|=(uint8_t)mask;
        if (at+16<2048) s->explored[at+16]|=(uint8_t)mask;
    }
}
int btp_world_seen(const BtpState *s,unsigned x,unsigned y)
{
    return x<128 && y<128 && (s->explored[y*16u+x/8u]&(128u>>(x&7u)));
}
static unsigned world_level(const BtpResources *r,const BtpState *s,int bx,int by);
static unsigned world_neighbours(const BtpResources *r,const BtpState *s,int bx,int by,unsigned level)
{
    return (world_level(r,s,bx,by-1)==level ? 1u : 0u)|
        (world_level(r,s,bx+1,by)==level ? 2u : 0u)|
        (world_level(r,s,bx,by+1)==level ? 4u : 0u)|
        (world_level(r,s,bx-1,by)==level ? 8u : 0u);
}
unsigned btp_world_mini_index(unsigned level,unsigned neighbours)
{
    /* Executed 187F:1F04: city selectors bypass terrain joining. */
    if (level>=144) return level;
    if (level==16) return 64;
    return (level>=32 ? level-16u : level)|(neighbours&15u);
}
unsigned btp_world_mini(const BtpResources *r,const BtpState *s,unsigned x,unsigned y)
{
    if (x>=128 || y>=128 || !r->world.native) return 65;
    unsigned level=world_level(r,s,(int)x,(int)y);
    unsigned mask=world_neighbours(r,s,(int)x,(int)y,level);
    return btp_world_mini_index(level,mask);
}

unsigned btp_world_device_direction(unsigned x,unsigned y)
{
    /* 0000:4405 passes packed world coordinates to 187F:0971. That
       routine narrows cross-sector deltas instead of taking the bearing
       across the whole island. Preserve its original arrow, including the
       asymmetric X word/Y byte arithmetic. */
    unsigned px=(x/128u)*256u+(x&127u),py=(y/128u)*4096u+(y&127u);
    int dx=(int16_t)(0x0a38u-px),up=(int8_t)((py&255u)-0x38u);
    if ((px>>8)<10) dx&=127;
    else if ((px>>8)>10) dx=(int16_t)((unsigned)dx|128u);
    if ((py&0xf000u)<0x8000u) up=(int16_t)((unsigned)up|0xff80u);
    else if ((py&0xf000u)>0x8000u) up&=127;
    return dx || up ? btp_combat_direction(0,0,dx,-up) : 0u;
}

static const BtpMap *local(const BtpResources *r,unsigned id)
{
    return id==1 ? &r->map : id==11 ? &r->destroyed : &r->local[id-1];
}
int btp_world_populated(const BtpResources *r,const BtpState *s)
{
    int bx=(int)s->campaign.world_x/16+8,by=(int)s->campaign.world_y/16+8;
    /* The original paints town chunk descriptors into its generated sector
       before checking this neighbourhood. MTP overlays must participate,
       even when the underlying generated height is ordinary ground. */
    if (!s->story_flags[58]) for (int y=-1;y<=1;++y) for (int x=-1;x<=1;++x)
        if (btp_world_location(r,s,(int)s->campaign.world_x/2+x*8,(int)s->campaign.world_y/2+y*8)) return 1;
    if (r->world.native) {
        for (int y=by-1;y<=by+1;++y) for (int x=bx-1;x<=bx+1;++x)
            if (x>=0 && y>=0 && x<144 && y<144 && (r->world.heights[y*144+x]&128u)) return 1;
    } else for (int y=-1;y<=1;++y) for (int x=-1;x<=1;++x)
        if (btp_world_location(r,s,(int)s->campaign.world_x/2+x*8,(int)s->campaign.world_y/2+y*8)) return 1;
    return 0;
}
int btp_world_location(const BtpResources *r,const BtpState *s,int x,int y)
{
    for (unsigned id=1;id<=13;++id) {
        if (id==11) continue;
        const BtpMap *m=local(r,id);
        if (!m->entrance_x[0] || !m->entrance_y[0]) continue;
        int ox=(m->entrance_x[0]>>8)*64,oy=(m->entrance_y[0]>>12)*64;
        if (x>=ox && y>=oy && x<ox+m->width && y<oy+m->height)
            return id==1 && s->story_flags[4] ? 11 : (int)id;
    }
    return 0;
}
static unsigned world_level(const BtpResources *r,const BtpState *s,int bx,int by)
{
    if (bx<-8 || by<-8 || bx>=136 || by>=136) return 255;
    unsigned id=(unsigned)btp_world_location(r,s,8*bx,8*by);
    if (id) {
        const BtpMap *m=local(r,id==11 ? 1u : id);
        int ox=(m->entrance_x[0]>>8)*8,oy=(m->entrance_y[0]>>12)*8;
        /* 0000:3050..30BB paints 90.. chunk numbers into the generated
           height blocks. 187F:1886 then excludes these town neighbours from
           terrain joins. Overlaying tiles alone leaves cut-off forests. */
        return 144u+(unsigned)(by-oy)*(m->width/8u)+(unsigned)(bx-ox);
    }
    return r->world.heights[(unsigned)(by+8)*144u+(unsigned)(bx+8)];
}

unsigned btp_world_tile(const BtpResources *r,const BtpState *s,int x,int y)
{
    int id=btp_world_location(r,s,x,y);
    if (id) {
        const BtpMap *m=local(r,(unsigned)id);
        if (id==11) m=&r->map; /* MAP11 retains MAP1's world origin. */
        int ox=(m->entrance_x[0]>>8)*64,oy=(m->entrance_y[0]>>12)*64;
        unsigned tile=btp_mission_tile(s,local(r,(unsigned)id),x-ox,y-oy);
        return id==2 && s->yard.active==2 ? btp_yard_tile(s,tile,x-ox,y-oy) : tile;
    }
    if (r->world.native) {
        if (x<0 || y<0 || x>=1024 || y>=1024) return 255;
        unsigned level=world_level(r,s,x/8,y/8);
        return btp_generated_joined_tile(&r->world,x,y,world_neighbours(r,s,x/8,y/8,level));
    }
    if (!r->world.loaded || x<BTP_WORLD_ORIGIN || y<BTP_WORLD_ORIGIN ||
        x>=BTP_WORLD_ORIGIN+BTP_WORLD_SIDE || y>=BTP_WORLD_ORIGIN+BTP_WORLD_SIDE) return 255;
    return r->world.tiles[(unsigned)(y-BTP_WORLD_ORIGIN)*BTP_WORLD_SIDE+(unsigned)(x-BTP_WORLD_ORIGIN)];
}
unsigned btp_world_descriptor(const BtpResources *r,const BtpState *s,int x,int y)
{
    if (x<0 || y<0 || x>=1024 || y>=1024) return 255;
    unsigned id=(unsigned)btp_world_location(r,s,x,y);
    if (id) {
        const BtpMap *m=local(r,id==11 ? 1u : id);
        int ox=(m->entrance_x[0]>>8)*64,oy=(m->entrance_y[0]>>12)*64;
        /* 0000:3084 paints consecutive 90.. town chunk descriptors. */
        return 144u+(unsigned)(y-oy)/8u*(m->width/8u)+(unsigned)(x-ox)/8u;
    }
    if (!r->world.native) return 255;
    unsigned level=world_level(r,s,x/8,y/8),mask=world_neighbours(r,s,x/8,y/8,level);
    /* 187F:1584 returns the raw height OR the joining mask. Texture and
       TINYLAND base indices are different projections of this descriptor. */
    return level|mask;
}
int btp_world_deep_crossing(const BtpWorldData *w,unsigned x,unsigned y,int dx,int dy)
{
    if (!w->native || x>=2048 || y>=2048) return 0;
    /* 0000:1C12..1CC1 checks only crossings of a 16-half-step terrain
       block. 187F:13D9 returns descriptor 0F for level-zero water joined
       to water on all four sides. People and vehicles share this check. */
    int bx=(int)(x/16u)+8,by=(int)(y/16u)+8,crossed=0;
    if (dx<0 && !(x&15u)) { --bx;crossed=1; }
    if (dx>0 && (x&15u)==15u) { ++bx;crossed=1; }
    if (dy<0 && !(y&15u)) { --by;crossed=1; }
    if (dy>0 && (y&15u)==15u) { ++by;crossed=1; }
    if (!crossed) return 0;
    unsigned at=(unsigned)by*144u+(unsigned)bx;
    return !w->heights[at] && !w->heights[at-144u] && !w->heights[at+144u] &&
        !w->heights[at-1u] && !w->heights[at+1u];
}
void btp_world_step(BtpState *s,const BtpResources *r,BtpAction a)
{
    uint16_t old_x=s->campaign.world_x,old_y=s->campaign.world_y;
    int gx=s->x_half,gy=s->y_half;
    if (s->map_id) {
        const BtpMap *m=local(r,s->map_id==11 ? 1u : s->map_id);
        gx+=(m->entrance_x[0]>>8)*128;gy+=(m->entrance_y[0]>>12)*128;
    }
    if (btp_action_moves(a)) {
        s->player_walk=btp_walk_next(s->player_walk,btp_player_direction(s->facing),btp_player_direction((unsigned)a));
        s->facing=(uint8_t)a;
        int x=gx+btp_action_dx(a),y=gy+btp_action_dy(a);
        if (x<0 || y<0 || x>=2048 || y>=2048) s->blocked=BTP_EDGE;
        else if (!btp_world_location(r,s,x/2,y/2) &&
            btp_world_deep_crossing(&r->world,(unsigned)gx,(unsigned)gy,btp_action_dx(a),btp_action_dy(a))) {
            s->blocked=BTP_WATER;btp_menu_open(s);s->campaign.ui=BTP_MENU_MESSAGE;s->menu.notice=5;
        }
        /* The arena's temporary gate 139 must not leak into town travel:
           roof/building tiles 115..138 still block ordinary movement. */
        else if (s->campaign.mounted ? btp_world_tile(r,s,x/2,(y-2)/2)>=s->gate ||
            btp_world_tile(r,s,x/2+1,(y-2)/2)>=s->gate : btp_world_tile(r,s,(x+1)/2,y/2)>=s->gate) s->blocked=BTP_WALL;
        else { gx=x;gy=y;s->blocked=BTP_CLEAR; }
        static const uint8_t frames[8][4]={{0,1,2,3},{4,5,6,7},{6,7,4,5},{5,6,7,4},
            {8,9,10,11},{12,13,14,15},{15,12,13,14},{14,15,12,13}};
        unsigned direction=btp_player_direction((unsigned)a),next=0;
        if (s->campaign.mech_direction==direction) for (unsigned i=0;i<4;++i)
            if (frames[direction][i]==s->campaign.mech_walk) next=(i+1)%4;
        s->campaign.mech_walk=frames[direction][next];s->campaign.mech_direction=(uint8_t)direction;
    }
    s->campaign.world_x=(uint16_t)gx;s->campaign.world_y=(uint16_t)gy;
    if (s->campaign.mounted) {
        unsigned mount=s->party.people[0][12];
        if (!mount) { s->campaign.mech_x=(uint16_t)gx;s->campaign.mech_y=(uint16_t)gy; }
    }
    unsigned id=(unsigned)btp_world_location(r,s,gx/2,gy/2);
    if (id!=s->map_id) {
        s->script=(BtpScriptState){0};s->entry_slot=0;s->campaign.building=0;
        s->npc=(BtpNpcState){.rng={s->npc.rng[0],s->npc.rng[1],s->npc.rng[2]}};
        memset(s->npc_walk,0,8);
        s->map_id=(uint8_t)id;
    }
    if (id) {
        const BtpMap *m=local(r,id==11 ? 1 : id);
        gx-=(m->entrance_x[0]>>8)*128;gy-=(m->entrance_y[0]>>12)*128;
    }
    s->x_half=(uint16_t)gx;s->y_half=(uint16_t)gy;
    btp_party_follow(s,r,old_x,old_y);
}
void btp_world_clock(BtpState *s,const BtpResources *r)
{
    /* Main-loop cadence remains the existing fixed four-tick approximation.
       The original draws even on indoor city terrain, with D346 excluding
       the separate area-map mode. Encounter-mask decisions are explicit. */
    if (++s->campaign.world_clock==4) {
        s->campaign.world_clock=0;
        unsigned roll=btp_rng_next(s->npc.rng);
        for (unsigned i=20;i<=22;++i) if (s->story_flags[i]) --s->story_flags[i];
        if (s->story_flags[29]) --s->story_flags[29];
        if (s->story_flags[41]) --s->story_flags[41];
        if (s->story_flags[23]--==0) btp_economy_market(s);
        if (!(roll&s->story_flags[36]) && s->story_flags[4] && !s->story_flags[58]) (void)btp_campaign_random(s,r);
    }
}
void btp_world_move(BtpState *s,const BtpResources *r,BtpAction a)
{
    ++s->tick;btp_world_step(s,r,a);btp_world_clock(s,r);
}
void btp_world_actions(BtpState *s,const BtpResources *r,BtpAction a)
{
    btp_menu_input(s,r,a);
}
