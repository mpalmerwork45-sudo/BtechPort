#include "core/npc.h"
#include "core/world.h"
#include "core/talk.h"
#include "core/campaign.h"
#include "core/party.h"
#include "data/save.h"
#include "frontend/pixels.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x);exit(1); } } while (0)
static void restore(BtpState *s,const BtpResources *r)
{
    uint8_t b[BTP_STATE_BYTES],again[BTP_STATE_BYTES];BtpState restored;
    btp_state_encode(s,b);CHECK(btp_state_decode(b,sizeof b,btp_active_map(r,s),btp_state_bld(r,s),&restored));
    btp_state_encode(&restored,again);CHECK(!memcmp(b,again,sizeof b));*s=restored;
}
int main(int argc,char **argv)
{
    CHECK(argc==2);BtpResources *r=calloc(1,sizeof *r);BtpError e;
    CHECK(r && btp_resources_load(argv[1],r,&e));
    CHECK(btp_world_data_load("work/world-data.bin",&r->world,&e));
    CHECK(btp_combat_data_load("work/combat-data.bin",&r->combat,&e));
    CHECK(btp_dialogue_load("work/talk-data.bin",&r->dialogue,&e));
    uint8_t source[BTP_ORIGINAL_BYTES];FILE *f=fopen("Original DOS/GAME3","rb");CHECK(f);
    CHECK(fread(source,1,sizeof source,f)==sizeof source && !fclose(f));
    f=fopen("tests/fixtures/town-npcs-primary.txt","r");CHECK(f);
    unsigned town,seed,expected,cases=0;BtpState s;
    while (fscanf(f," N %u %u %u",&town,&seed,&expected)==3) {
        const BtpMap *m=town==1 ? &r->map : &r->local[town-1];
        uint8_t raw[BTP_ORIGINAL_BYTES];memcpy(raw,source,sizeof raw);
        unsigned px=m->entrance_x[0],py=m->entrance_y[0];
        raw[0xf45]=(uint8_t)px;raw[0xf46]=(uint8_t)(px>>8);
        raw[0xf47]=(uint8_t)py;raw[0xf48]=(uint8_t)(py>>8);
        CHECK(btp_original_decode(raw,sizeof raw,&s,r,&e));s.map_id=(uint8_t)town;
        for (unsigned i=0;i<3;++i) s.npc.rng[i]=(uint8_t)(seed>>(8*i));
        btp_npc_enter(&s,m);
        for (unsigned i=0;i<3;++i) btp_npc_advance(&s,m);
        CHECK((s.npc.rng[0]|(unsigned)s.npc.rng[1]<<8|(unsigned)s.npc.rng[2]<<16)==expected);
        CHECK(s.npc.enabled==2 && !s.npc.fault);
        for (unsigned i=0;i<8;++i) {
            unsigned pair,timer,x,y;CHECK(fscanf(f,"%u %u %u %u",&pair,&timer,&x,&y)==4);
            CHECK(s.npc_pairs[i][0]==pair && s.npc_pairs[i][1]==timer && s.npc.actor[i].x==x && s.npc.actor[i].y==y);
        }
        restore(&s,r);++cases;
    }
    CHECK(!ferror(f) && !fclose(f) && cases==50);
    f=fopen("tests/fixtures/town-talk-primary.txt","r");CHECK(f);cases=0;
    unsigned building,room;
    while (fscanf(f," T %u %u %u",&town,&building,&room)==3) {
        CHECK(btp_original_decode(source,sizeof source,&s,r,&e));s.map_id=(uint8_t)town;
        s.story_flags[13]=(uint8_t)building;
        for (unsigned i=0;i<8;++i) { s.npc_pairs[i][0]=(uint8_t)(i<<4);s.npc_pairs[i][1]=1; }
        btp_talk_begin(&s,r);CHECK(s.talk.room==room && s.talk.count==(room<8));
        CHECK(s.talk.mask==(room<8 ? 1u<<room : 0u));++cases;
    }
    CHECK(!ferror(f) && !fclose(f) && cases==45);
    /* Ordinary idle input restores old town saves, visibly walks NPCs and
       suspends their room timers while the player is using a menu. */
    uint8_t raw[BTP_ORIGINAL_BYTES];memcpy(raw,source,sizeof raw);
    raw[0xf45]=44;raw[0xf46]=10;raw[0xf47]=76;raw[0xf48]=128;raw[0xcf9+58]=1;
    CHECK(btp_original_decode(raw,sizeof raw,&s,r,&e));CHECK(s.map_id==2 && !s.npc.enabled);
    for (unsigned i=0;i<12;++i) { btp_game_tick(&s,r,BTP_IDLE);restore(&s,r); }
    CHECK(s.npc.enabled==2);BtpNpcState old=s.npc;unsigned moved=0,arrived=0;
    for (unsigned frame=0;frame<2400;++frame) {
        btp_game_tick(&s,r,BTP_IDLE);restore(&s,r);
        CHECK(s.mode==BTP_EXPLORE && !s.npc.fault);
        for (unsigned i=0;i<8;++i) {
            if (s.npc.actor[i].x && (s.npc.actor[i].x!=old.actor[i].x || s.npc.actor[i].y!=old.actor[i].y)) ++moved;
            if (old.actor[i].x && !s.npc.actor[i].x) ++arrived;
        }
        old=s.npc;
    }
    if (!(moved>10 && arrived)) fprintf(stderr,"Town updates: %u moves, %u arrivals\n",moved,arrived);
    CHECK(moved>10 && arrived);btp_game_tick(&s,r,BTP_OPEN_MENU);old=s.npc;
    for (unsigned i=0;i<24;++i) btp_game_tick(&s,r,BTP_IDLE);
    CHECK(!memcmp(&old,&s.npc,sizeof old));restore(&s,r);
    btp_game_tick(&s,r,BTP_CANCEL);CHECK(s.mode==BTP_EXPLORE);
    uint32_t *visible=malloc(BTP_PIXELS*sizeof *visible),*empty=malloc(BTP_PIXELS*sizeof *empty);CHECK(visible && empty);
    /* Centre near an actor on legal ground and confirm the actual town sheet
       renders its original human sprite without exposing it inside a roof. */
    unsigned actor=0;while (actor<8 && !s.npc.actor[actor].x) ++actor;CHECK(actor<8);
    s.x_half=s.npc.actor[actor].x&127u;s.y_half=s.npc.actor[actor].y&127u;
    s.campaign.world_x=(uint16_t)(1280u+s.x_half);s.campaign.world_y=(uint16_t)(1024u+s.y_half);
    btp_render(r,&s,0,visible);s.npc.enabled=0;btp_render(r,&s,0,empty);
    CHECK(memcmp(visible,empty,BTP_PIXELS*sizeof *visible));
    /* Hospital's actual BLD passes conversation category 5. An occupied
       matching doorway must open Talk, survive saving and show a reply even
       though the hospital is entrance 4 and the matching waypoint is 3. */
    memcpy(raw,source,sizeof raw);raw[0xf45]=116;raw[0xf46]=10;raw[0xf47]=115;raw[0xf48]=128;
    for (unsigned i=0;i<8;++i) raw[1+17*i+12]=8;
    CHECK(btp_original_decode(raw,sizeof raw,&s,r,&e));
    btp_game_tick(&s,r,BTP_UP);CHECK(s.mode==BTP_ENTRY);btp_game_tick(&s,r,BTP_ACCEPT);
    for (unsigned i=0;i<32 && s.script.status!=BTP_SCRIPT_MENU;++i) btp_game_tick(&s,r,BTP_ACCEPT);
    CHECK(s.mode==BTP_BUILDING && s.campaign.building==9);
    s.npc_pairs[1][0]=0x35;s.npc_pairs[1][1]=20;s.npc.actor[1]=(BtpNpc){0};
    for (unsigned i=0;i<3;++i) btp_game_tick(&s,r,BTP_DOWN);
    btp_game_tick(&s,r,BTP_ACCEPT);CHECK(s.talk.phase==BTP_TALK_MENU && s.talk.room==3 && s.talk.count);
    restore(&s,r);btp_game_tick(&s,r,BTP_ACCEPT);CHECK(s.talk.phase==BTP_TALK_REPLY && s.talk.reply);
    uint8_t text[BTP_BLD_MAX+1];size_t length;CHECK(btp_game_text(&s,r,text,sizeof text,&length) && length);restore(&s,r);
    btp_game_tick(&s,r,BTP_ACCEPT);CHECK(s.mode==BTP_BUILDING && s.script.status==BTP_SCRIPT_MENU);restore(&s,r);
    /* Even an imported active garage must not create enemy mechs inside
       Starport. Arena actor setup is covered separately by arena outcomes. */
    BtpCombatUnit units[12];uint8_t ids[12];int dx,dy;unsigned outside_mechs=0;
    for (unsigned i=0;i<4;++i) {
        uint8_t *mech=btp_party_mech(&s,i);memcpy(mech,r->combat.commando,125);
        s.party.mech_types[i]=mech[0];CHECK(mech[0]!=255);
    }
    for (unsigned candidate_seed=1;candidate_seed<=64;++candidate_seed) {
        s.map_id=2;s.npc.rng[0]=(uint8_t)candidate_seed;s.npc.rng[1]=54;s.npc.rng[2]=210;
        unsigned n=btp_campaign_candidates(&s,r,units,ids,&dx,&dy);
        for (unsigned i=0;i<n;++i) CHECK(units[i].infantry && ids[i]>=16);
        /* The same active garage still permits mech opposition elsewhere. */
        s.map_id=3;s.npc.rng[0]=(uint8_t)candidate_seed;s.npc.rng[1]=54;s.npc.rng[2]=210;
        n=btp_campaign_candidates(&s,r,units,ids,&dx,&dy);
        for (unsigned i=0;i<n;++i) outside_mechs+=!units[i].infantry;
    }
    CHECK(outside_mechs);
    s.map_id=11;btp_npc_enter(&s,&r->destroyed);CHECK(!s.npc.enabled);
    s.map_id=0;btp_npc_enter(&s,&r->map);CHECK(!s.npc.enabled);
    /* This complete visit imports GAME2, waits for a real room arrival and
       walks to the hospital. No actor, timer or random state is injected. */
    CHECK(btp_save_load("Original DOS/GAME2",&s,r,&e));
    f=fopen("tests/fixtures/ordinary-hospital-talk.actions","r");CHECK(f);
    char line[80];unsigned menu=0,reply=0,ticks=0;
    while (fgets(line,sizeof line,f)) {
        line[strcspn(line,"\r\n")]=0;BtpAction action;CHECK(btp_action_parse(line,&action));
        btp_game_tick(&s,r,action);restore(&s,r);++ticks;
        menu|=s.talk.phase==BTP_TALK_MENU && s.talk.count!=0;
        reply|=s.talk.phase==BTP_TALK_REPLY && s.talk.reply!=0;
    }
    CHECK(!ferror(f) && !fclose(f) && ticks>500 && menu && reply);
    CHECK(s.mode==BTP_BUILDING && s.campaign.building==9 && s.script.status==BTP_SCRIPT_MENU && !s.talk.phase);
    free(visible);free(empty);free(r);
    printf("PASS: %u checks; 95 primary town/Talk cases, roaming, hospital visit and Starport infantry encounters\n",checks);return 0;
}
