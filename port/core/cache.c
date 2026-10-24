#include "data/chi_missions.h"
#include "core/cache.h"
#include "core/party.h"
#include "core/animation.h"
#include "core/audio.h"
#include "core/menu.h"
#include <string.h>
#include <stdio.h>
_Static_assert(sizeof(BtpCacheState)==809,"Cache save layout must remain byte packed");

static unsigned normalized(unsigned raw)
{
    return ((raw/64u)/4u*8u+(raw%64u)/8u)*32u+(raw/64u)%4u*8u+raw%8u;
}
static void position_party(BtpState *s,const BtpResources *r)
{
    /* All people enter each cache room together. No vehicle can enter;
       initialize legal foot positions using the ordinary compact formation. */
    s->campaign.world_x=(uint16_t)(1536+s->x_half);
    s->campaign.world_y=(uint16_t)(1536+s->y_half);
    for (unsigned i=0;i<8;++i) {
        s->party.x[i]=s->campaign.world_x;s->party.y[i]=s->campaign.world_y;
    }
    btp_party_follow(s,r,s->campaign.world_x,s->campaign.world_y);
}
static void notice(BtpState *s,unsigned id)
{
    s->cache.phase=BTP_CACHE_NOTICE;s->cache.notice=(uint8_t)id;
}
void btp_cache_restore_party(BtpState *s,const BtpResources *r)
{
    /* Earlier native saves left world/follower coordinates at the cave or
       previous room. The leader can already be correct while a follower is
       outside this room. Recover only demonstrably invalid positions; a
       legal formation and its walk frames must survive loading unchanged. */
    if (!s->cache.active) return;
    int stale=s->campaign.world_x!=1536u+s->x_half || s->campaign.world_y!=1536u+s->y_half;
    for (unsigned i=0;i<8;++i) if (s->party.people[i][0]!=255 &&
        !btp_party_walkable(s,r,s->party.x[i],s->party.y[i],0)) stale=1;
    if (stale) position_party(s,r);
}
unsigned btp_cache_tile(const BtpResources *r,const BtpState *s,int x,int y)
{
    if (s->story_flags[66]) return x>=0 && x<32 && y>=0 && y<24 ? s->cache.maproom[(unsigned)y*32u+(unsigned)x] : 255u;
    if (x<0 || x>=64 || y<0 || y>=64) return 255;
    int hall_x=(int)btp_chi_mission(r,BTP_MIS_CACHE_HALL_X),hall_y=(int)btp_chi_mission(r,BTP_MIS_CACHE_HALL_Y);
    if (s->cache.hall && x>=hall_x && x<hall_x+3 && y>=hall_y && y<hall_y+6)
        return r->combat.cache_secret[(unsigned)(y-hall_y)*3u+(unsigned)(x-hall_x)];
    for (unsigned i=0;i<12;++i) {
        int dx=r->combat.cache_dx[i]/2,dy=r->combat.cache_dy[i]/2;
        if ((s->story_flags[67+i] || (s->cache.phase==BTP_CACHE_DOOR && s->cache.door==i)) &&
            y==dy && x>=dx && x<dx+4) {
            unsigned step=s->cache.phase==BTP_CACHE_DOOR && s->cache.door==i ? s->cache.door_step : 2u;
            return r->combat.cache_door_tiles[step*4u+(unsigned)(x-dx)];
        }
    }
    return btp_map_tile(&r->local[13],x,y);
}
int btp_cache_terminal(BtpState *s,const BtpResources *r,unsigned x,unsigned y)
{
    x=(x+1u)&127u;y&=127u;
    for (unsigned i=0;i<33;++i) if (y==r->combat.cache_ty[i] && x>=r->combat.cache_tx[i] && x<r->combat.cache_tx[i]+3u) {
        s->cache.terminal=(uint8_t)i;s->cache.selected=0;
        if (s->cache.used[i]) notice(s,122);
        else { s->cache.phase=BTP_CACHE_TERMINAL;s->cache.notice=0; }
        return 1;
    }
    return 0;
}
int btp_cache_door(BtpState *s,const BtpResources *r,unsigned x,unsigned y,int door)
{
    x=((x+1u)&126u);y&=126u;
    if (door<0) {
        for (unsigned i=0;i<12;++i) if (x==r->combat.cache_dx[i] && y==r->combat.cache_dy[i]) { door=(int)i;break; }
    }
    if (door<0 || door>=12) return 0;
    unsigned i=(unsigned)door;
    unsigned required[]={r->combat.cache_red[i],r->combat.cache_blue[i],r->combat.cache_yellow[i]};
    unsigned missing=0;
    if (i!=11) for (unsigned color=0;color<3;++color) if (!required[color] || s->story_flags[59+color]!=required[color]-1u) missing|=1u<<color;
    if (missing) { s->cache.notice=(uint8_t)missing;s->cache.phase=BTP_CACHE_NOTICE;s->cache.terminal=255;return 0; }
    if (i==11) memset(s->story_flags+59,255,3);
    else for (unsigned color=0;color<3;++color) s->cache.used[required[color]-1u]=1;
    s->story_flags[67+i]=1;s->cache.door=(uint8_t)i;s->cache.door_step=0;
    s->cache.phase=BTP_CACHE_DOOR;s->cache.notice=0;
    btp_audio_effect(s,10);return 1;
}
void btp_cache_toggle(BtpState *s,unsigned x,unsigned y)
{
    x=(x+1u)&127u;
    unsigned raw=((y&112u)<<4)+((y&14u)<<2)+((x/2u)&7u)+((x&112u)<<2);
    if (raw>=768) return;
    uint8_t *tile=&s->cache.maproom[normalized(raw)];
    *tile=(uint8_t)((((*tile+1u)^1u)-1u)&255u);btp_audio_effect(s,15);
}
int btp_cache_password(BtpState *s,const BtpResources *r)
{
    unsigned valid=1;
    for (unsigned i=0;i<7;++i) if (s->cache.maproom[normalized(r->combat.cache_password[i])]&1u) valid=0;
    for (unsigned i=0;i<768;++i) {
        unsigned tile=s->cache.maproom[normalized(i)],wanted=0;
        if (tile<151 || tile>240 || (tile&1u)) continue;
        for (unsigned j=0;j<7;++j) wanted|=r->combat.cache_password[j]==i;
        if (!wanted) valid=0;
    }
    if (valid) { s->story_flags[62]=1;notice(s,130);btp_audio_effect(s,16); }
    else {
        for (unsigned i=0;i<768;++i) if (s->cache.maproom[i]>=151 && s->cache.maproom[i]<=240 && !(s->cache.maproom[i]&1u)) --s->cache.maproom[i];
        notice(s,131);btp_audio_effect(s,17);
    }
    return (int)valid;
}
void btp_cache_begin(BtpState *s,const BtpResources *r)
{
    s->cache=(BtpCacheState){.active=1};s->story_flags[58]=1;
    s->story_flags[66]=0;memset(s->story_flags+59,255,3);
    s->map_id=14;s->gate=33;s->x_half=(uint16_t)btp_chi_mission(r,BTP_MIS_CACHE_START_X);s->y_half=(uint16_t)btp_chi_mission(r,BTP_MIS_CACHE_START_Y);
    s->campaign.world_x=(uint16_t)(1536+s->x_half);s->campaign.world_y=(uint16_t)(1536+s->y_half);s->campaign.mounted=0;
    btp_party_init(s);
    for (unsigned i=0;i<4;++i) { uint8_t *m=btp_party_mech(s,i);if (m[0]!=255) s->party.mech_types[i]=m[0];m[0]=255; }
    for (unsigned i=0;i<8;++i) s->party.people[i][12]=8;
    (void)btp_cache_door(s,r,3,124,11);
    /* Original initialization opens the door before INSTRUCT.BLD. */
    s->cache.phase=BTP_CACHE_WALK;s->cache.door=s->cache.door_step=0;
    position_party(s,r);
    btp_game_building(s,r,23);
}
void btp_cache_script_end(BtpState *s,const BtpResources *r)
{
    unsigned kind=s->campaign.building;
    if (!s->cache.active) { if (kind==20 && s->story_flags[btp_chi_mission(r,BTP_MIS_CACHE_ACCESS_FLAG)]) btp_cache_begin(s,r);return; }
    if (kind==25) {
        /* 0B5D:0515..0534 sets both exit flags after WINSCENE's final
           key wait returns. The native frontend consumes menu.quit. */
        s->mode=BTP_ENDING;s->menu.quit=(uint8_t)btp_chi_mission(r,BTP_MIS_CACHE_QUIT_AT_END);return;
    }
    s->script=(BtpScriptState){0};s->campaign.building=0;s->entry_slot=0;
    s->mode=BTP_CACHE;
    s->campaign.mounted=0;
}
static void room(BtpState *s,const BtpResources *r,int enter)
{
    s->story_flags[66]=(uint8_t)enter;s->gate=(uint8_t)(enter ? 139 : 33);
    s->x_half=(uint16_t)(enter ? btp_chi_mission(r,BTP_MIS_CACHE_ROOM_X) : btp_chi_mission(r,BTP_MIS_CACHE_ROOM_RETURN_X));s->y_half=(uint16_t)(enter ? btp_chi_mission(r,BTP_MIS_CACHE_ROOM_Y) : btp_chi_mission(r,BTP_MIS_CACHE_ROOM_RETURN_Y));
    if (enter) memcpy(s->cache.maproom,r->maproom.tiles,768);
    s->cache.phase=BTP_CACHE_WALK;s->cache.notice=0;
    position_party(s,r);
}
static void move_cache(BtpState *s,const BtpResources *r,BtpAction a);
void btp_cache_input(BtpState *s,const BtpResources *r,BtpAction a)
{
    ++s->tick;BtpCacheState *c=&s->cache;
    if (c->phase==BTP_CACHE_DOOR) {
        if (s->audio.sound_count) return;
        if (c->door_step<2) ++c->door_step;
        else { c->phase=BTP_CACHE_WALK;c->door=c->door_step=0; }
        return;
    }
    if (c->phase==BTP_CACHE_TERMINAL) {
        if (a==BTP_LEFT || a==BTP_UP) c->selected=0;
        if (a==BTP_RIGHT || a==BTP_DOWN) c->selected=1;
        if (a==BTP_CANCEL || a==BTP_ACCEPT || a==BTP_OPEN_MENU) {
            if (a!=BTP_CANCEL && !c->selected) s->story_flags[59+r->combat.cache_color[c->terminal]]=c->terminal;
            c->phase=BTP_CACHE_WALK;c->terminal=c->selected=c->notice=0;
        }
        return;
    }
    if (c->phase) {
        if (a!=BTP_ACCEPT && a!=BTP_OPEN_MENU && a!=BTP_CANCEL) return;
        if (s->audio.sound_count) return;
        if (c->phase==BTP_CACHE_PEER) { c->phase=BTP_CACHE_CLIMB;c->notice=128; }
        else if (c->phase==BTP_CACHE_CLIMB) room(s,r,1);
        else if (c->phase==BTP_CACHE_EXIT) room(s,r,0);
        else { c->phase=BTP_CACHE_WALK;c->notice=c->terminal=0; }
        return;
    }
    if (a==BTP_OPEN_MENU || a==BTP_ACCEPT) { btp_menu_open(s);return; }
    if (!btp_action_moves(a)) return;
    unsigned steps=s->story_flags[66] ? 1u : s->menu.steps;
    uint8_t frame=s->player_walk;unsigned before=btp_player_direction(s->facing);
    BtpPartyState party_before=s->party;
    for (unsigned i=0;i<steps;++i) {
        move_cache(s,r,a);
        if (s->blocked || s->mode!=BTP_CACHE || s->cache.phase) break;
    }
    s->player_walk=btp_walk_next(frame,before,btp_player_direction((unsigned)a));
    /* A two/four-step input still advances every moving person's gait only
       once, while collision and formation updates check each half-step. */
    for (unsigned i=1;i<8;++i) if (s->party.people[i][0]!=255 &&
        (s->party.x[i]!=party_before.x[i] || s->party.y[i]!=party_before.y[i]))
        s->party.walk[i]=btp_walk_next(party_before.walk[i],party_before.direction[i],s->party.direction[i]);
}
int btp_cache_contact(const BtpState *s,const BtpResources *r,int *x,int *y)
{
    /* 0000:1C12 scans compact foot positions in order even inside MAP14/15.
       A follower touching a terminal/door is the interaction point; the
       leader cannot advance while that follower is against a wall. */
    unsigned place=0;
    for (unsigned i=0;i<8;++i) if (s->party.people[i][0]!=255 && s->party.people[i][12]>=8) {
        int px=*x+r->combat.formation_x[place],py=*y+r->combat.formation_y[place];++place;
        unsigned tile=px<0 || py<0 ? 255u : btp_cache_tile(r,s,(px+1)/2,py/2);
        if (tile>=s->gate) { *x=px;*y=py;return (int)place-1; }
    }
    return -1;
}
static void move_cache(BtpState *s,const BtpResources *r,BtpAction a)
{
    BtpCacheState *c=&s->cache;
    int x=(int)s->x_half+btp_action_dx(a),y=(int)s->y_half+btp_action_dy(a);
    s->player_walk=btp_walk_next(s->player_walk,btp_player_direction(s->facing),btp_player_direction((unsigned)a));
    s->facing=(uint8_t)a;
    unsigned width=s->story_flags[66] ? 64u : 128u,height=s->story_flags[66] ? 48u : 128u;
    if (x<0 || y<0 || x>=(int)width-1 || y>=(int)height) { s->blocked=BTP_EDGE;return; }
    if (btp_cache_contact(s,r,&x,&y)<0) {
        uint16_t old_x=s->campaign.world_x,old_y=s->campaign.world_y;
        s->x_half=(uint16_t)x;s->y_half=(uint16_t)y;s->blocked=0;
        s->campaign.world_x=(uint16_t)(1536+x);s->campaign.world_y=(uint16_t)(1536+y);
        btp_party_follow(s,r,old_x,old_y);return;
    }
    /* A member outside the loaded room is a boundary, not a Phoenix tile.
       The out-of-range sentinel 255 must never dispatch a story interaction. */
    if (x<0 || y<0 || x>=(int)width-1 || y>=(int)height) { s->blocked=BTP_EDGE;return; }
    unsigned tile=x<0 || y<0 ? 255u : btp_cache_tile(r,s,(x+1)/2,y/2);
    s->blocked=BTP_WALL;
    if (s->story_flags[66]) {
        if (tile==148) { c->phase=BTP_CACHE_EXIT;c->notice=129; }
        else if (tile>=151 && tile<=240) btp_cache_toggle(s,(unsigned)x,(unsigned)y);
        else if (tile==140 || tile==141) (void)btp_cache_password(s,r);
        return;
    }
    if (tile>=126 && tile<=128) { (void)btp_cache_door(s,r,(unsigned)(x-2*(int)(tile-126u)),(unsigned)y,-1);return; }
    if (tile==182 || tile==183) { (void)btp_cache_terminal(s,r,(unsigned)x,(unsigned)y);return; }
    if (tile==245 && x>=(int)btp_chi_mission(r,BTP_MIS_CACHE_SECRET_X_MIN) && x<=(int)btp_chi_mission(r,BTP_MIS_CACHE_SECRET_X_MAX) && y==(int)btp_chi_mission(r,BTP_MIS_CACHE_SECRET_Y)) { c->hall=1;notice(s,119);return; }
    if (tile>=246) { if (!s->story_flags[63]) btp_game_building(s,r,22);return; }
    if (tile==131 || (tile>=165 && tile<=167)) { notice(s,120);return; }
    unsigned tx=((unsigned)x+1u)&126u,ty=(unsigned)y&126u;
    if (tile==58 || tile==61) { if (tx==btp_chi_mission(r,BTP_MIS_CACHE_SUPPLY_X) && ty>=btp_chi_mission(r,BTP_MIS_CACHE_SUPPLY_Y_MIN) && ty<=btp_chi_mission(r,BTP_MIS_CACHE_SUPPLY_Y_MAX)) { s->story_flags[64]=1;notice(s,121); }return; }
    if (tile==40) {
        if (tx==btp_chi_mission(r,BTP_MIS_CACHE_FIND_X) && ty==btp_chi_mission(r,BTP_MIS_CACHE_FIND_Y)) { btp_game_building(s,r,24);s->story_flags[65]=1; }
        else if (tx==btp_chi_mission(r,BTP_MIS_CACHE_ROOM_DOOR_X) && ty==btp_chi_mission(r,BTP_MIS_CACHE_ROOM_DOOR_Y)) {
            if (s->story_flags[62]==1) notice(s,126);
            else { c->phase=BTP_CACHE_PEER;c->notice=127; }
        }
    }
    if (tile==77 && ((tx==btp_chi_mission(r,BTP_MIS_CACHE_ENDING_X1) && ty==btp_chi_mission(r,BTP_MIS_CACHE_ENDING_Y1)) || (tx==btp_chi_mission(r,BTP_MIS_CACHE_ENDING_X2) && ty==btp_chi_mission(r,BTP_MIS_CACHE_ENDING_Y2)))) {
        if (btp_chi_mission(r,BTP_MIS_CACHE_REQUIRE_SUPPLY) && !s->story_flags[64]) notice(s,123);
        else if (btp_chi_mission(r,BTP_MIS_CACHE_REQUIRE_PASSWORD) && s->story_flags[62]!=1) notice(s,124);
        else if (btp_chi_mission(r,BTP_MIS_CACHE_REQUIRE_FIND) && !s->story_flags[65]) notice(s,125);
        else btp_game_building(s,r,25);
    }
}
int btp_cache_valid_resources(const BtpState *s,const BtpResources *r)
{
    const BtpCacheState *c=&s->cache;
    if (c->active>1 || c->phase>BTP_CACHE_PHOENIX || c->selected>1 || (c->terminal>=33 && c->terminal!=255) || c->door>11 || c->door_step>2 || c->hall>1) return 0;
    for (unsigned i=0;i<33;++i) if (c->used[i]>1) return 0;
    if (!c->active) {
        if (c->phase || c->selected || c->terminal || c->notice || c->door || c->door_step || c->hall) return 0;
        for (unsigned i=0;i<33;++i) if (c->used[i]) return 0;
        for (unsigned i=0;i<768;++i) if (c->maproom[i]) return 0;
        /* Authored endings own their continuation in events.c, without
           pretending to be an original Star League cache completion. */
        return s->mode!=BTP_CACHE && (s->mode!=BTP_ENDING || s->event.enabled);
    }
    if (!s->story_flags[58] || s->map_id!=14 || s->campaign.mounted || (s->gate!=(s->story_flags[66] ? 139u : 33u)) ||
        (s->mode!=BTP_CACHE && s->mode!=BTP_BUILDING && s->mode!=BTP_ACTIONS && s->mode!=BTP_SCRIPT_FAULT && s->mode!=BTP_ENDING)) return 0;
    if (c->phase==BTP_CACHE_TERMINAL && (c->terminal>=33 || c->used[c->terminal])) return 0;
    if ((c->phase==BTP_CACHE_TERMINAL || c->phase==BTP_CACHE_DOOR || c->phase==BTP_CACHE_PEER || c->phase==BTP_CACHE_CLIMB) && s->story_flags[66]) return 0;
    if (c->phase==BTP_CACHE_EXIT && !s->story_flags[66]) return 0;
    if (c->phase==BTP_CACHE_PHOENIX && (s->mode!=BTP_BUILDING || s->campaign.building!=22 || s->script.status!=BTP_SCRIPT_NATIVE || s->script.native_action!=45)) return 0;
    if (s->mode==BTP_ENDING && (s->campaign.building!=25 || s->script.status!=BTP_SCRIPT_END || (btp_chi_mission(r,BTP_MIS_CACHE_REQUIRE_PASSWORD) && !s->story_flags[62]) || (btp_chi_mission(r,BTP_MIS_CACHE_REQUIRE_SUPPLY) && !s->story_flags[64]) || (btp_chi_mission(r,BTP_MIS_CACHE_REQUIRE_FIND) && !s->story_flags[65]))) return 0;
    if (c->notice && !(c->notice>=119 && c->notice<=137) && !(c->terminal==255 && c->notice<8)) return 0;
    for (unsigned i=59;i<=61;++i) if (s->story_flags[i]>=33 && s->story_flags[i]!=255) return 0;
    for (unsigned i=62;i<=78;++i) if (s->story_flags[i]>1) return 0;
    return 1;
}
static int append(const BtpResources *r,unsigned id,uint8_t *out,size_t cap,size_t *n)
{
    if (id>=r->dialogue.count || r->dialogue.size[id]>cap-*n) return 0;
    memcpy(out+*n,r->dialogue.bytes+r->dialogue.offset[id],r->dialogue.size[id]);*n+=r->dialogue.size[id];return 1;
}
int btp_cache_text(const BtpState *s,const BtpResources *r,uint8_t *out,size_t cap,size_t *length)
{
    *length=0;
    if (s->cache.phase==BTP_CACHE_TERMINAL) {
        char number[4];snprintf(number,sizeof number,"%u",s->cache.terminal+1u);
        if (!append(r,135,out,cap,length) || !append(r,138+r->combat.cache_color[s->cache.terminal],out,cap,length) || !append(r,136,out,cap,length)) return 0;
        size_t n=strlen(number);if (n>cap-*length) return 0;memcpy(out+*length,number,n);*length+=n;
        return append(r,137,out,cap,length);
    }
    if (s->cache.terminal==255) {
        for (unsigned i=0;i<3;++i) if ((s->cache.notice&(1u<<i)) && !append(r,132+i,out,cap,length)) return 0;
        return 1;
    }
    return s->cache.notice ? append(r,s->cache.notice,out,cap,length) : 1;
}

int btp_cache_valid(const BtpState *s) { return btp_cache_valid_resources(s,NULL); }
