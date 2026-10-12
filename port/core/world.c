#include "core/world.h"
#include "core/training.h"
#include "core/animation.h"
#include "core/npc.h"
#include "core/campaign.h"
#include "core/party.h"
#include "core/economy.h"
#include "core/menu.h"
#include <string.h>
#include <stdlib.h>

static const BtpMap *local(const BtpResources *r,unsigned id)
{
    return id==1 ? &r->map : id==11 ? &r->destroyed : &r->local[id-1];
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

unsigned btp_world_tile(const BtpResources *r,const BtpState *s,int x,int y)
{
    int id=btp_world_location(r,s,x,y);
    if (id) {
        const BtpMap *m=local(r,(unsigned)id);
        if (id==11) m=&r->map; /* MAP11 retains MAP1's world origin. */
        int ox=(m->entrance_x[0]>>8)*64,oy=(m->entrance_y[0]>>12)*64;
        return btp_mission_tile(s,local(r,(unsigned)id),x-ox,y-oy);
    }
    if (r->world.native) return btp_generated_tile(&r->world,x,y);
    if (!r->world.loaded || x<BTP_WORLD_ORIGIN || y<BTP_WORLD_ORIGIN ||
        x>=BTP_WORLD_ORIGIN+BTP_WORLD_SIDE || y>=BTP_WORLD_ORIGIN+BTP_WORLD_SIDE) return 255;
    return r->world.tiles[(unsigned)(y-BTP_WORLD_ORIGIN)*BTP_WORLD_SIDE+(unsigned)(x-BTP_WORLD_ORIGIN)];
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
    if (s->campaign.mounted) { s->campaign.mech_x=(uint16_t)gx;s->campaign.mech_y=(uint16_t)gy; }
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
    btp_party_follow(s,old_x,old_y);
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
