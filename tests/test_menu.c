#include "core/menu.h"
#include "core/party.h"
#include "core/npc.h"
#include "data/save.h"
#include "frontend/pixels.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
static unsigned checks;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x);return 1; } } while (0)
static int restore(BtpState *s,const BtpResources *r)
{
    uint8_t a[BTP_STATE_BYTES],b[BTP_STATE_BYTES];BtpState copy;
    btp_state_encode(s,a);
    if (!btp_state_decode(a,sizeof a,btp_active_map(r,s),btp_state_bld(r,s),&copy)) return 0;
    btp_state_encode(&copy,b);return !memcmp(a,b,sizeof a);
}
static void select_item(BtpState *s,const BtpResources *r,unsigned item)
{
    unsigned count=btp_actions_count(s),n=(item+count-s->campaign.selected)%count;
    for (unsigned i=0;i<n;++i) btp_game_tick(s,r,BTP_DOWN);
    btp_game_tick(s,r,BTP_ACCEPT);
}
static uint64_t crop_hash(const uint32_t *pixels,unsigned x,unsigned y,unsigned width,unsigned height)
{
    uint64_t h=UINT64_C(14695981039346656037);
    for (unsigned row=y;row<y+height;++row) for (unsigned col=x;col<x+width;++col) for (unsigned c=0;c<3;++c)
        h=(h^((pixels[row*320+col]>>(16u-8u*c))&255u))*UINT64_C(1099511628211);
    return h;
}
int main(int argc,char **argv)
{
    if (argc!=2) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError e;CHECK(r && btp_resources_load(argv[1],r,&e));
    CHECK(btp_dialogue_load("work/talk-data.bin",&r->dialogue,&e));
    CHECK(btp_combat_data_load("work/combat-data.bin",&r->combat,&e));
    CHECK(btp_world_data_load("work/world-data.bin",&r->world,&e));
    uint32_t *pixels=malloc(sizeof *pixels*BTP_PIXELS);CHECK(pixels);
    BtpState s;btp_start(&s);s.mode=BTP_TITLE;btp_render(r,&s,0,pixels);
    uint64_t hash=UINT64_C(14695981039346656037);
    for (unsigned i=0;i<BTP_PIXELS;++i) for (unsigned channel=0;channel<3;++channel)
        hash=(hash^((pixels[i]>>(16u-8u*channel))&255u))*UINT64_C(1099511628211);
    /* All 64,000 original VGA screenshot RGB pixels, title-palette.json. */
    CHECK(hash==UINT64_C(0x1640cf785a6ac07b));
    s.mode=BTP_LOGO;btp_render(r,&s,0,pixels);
    CHECK(crop_hash(pixels,0,0,320,200)==UINT64_C(0x606c4e2b814b5ad4));
    s.mode=BTP_MISSION;s.combat.phase=BTP_COMBAT_CONTROL;s.combat.selected=1;
    btp_render(r,&s,0,pixels);CHECK(crop_hash(pixels,8,104,88,88)==UINT64_C(0xea3269d891ca94ec));
    s.mode=BTP_MISSION;s.combat.phase=BTP_COMBAT_MESSAGES;s.combat.selected=2;
    btp_render(r,&s,0,pixels);CHECK(crop_hash(pixels,8,104,88,88)==UINT64_C(0xd286e3c49177864b));
    s.combat.phase=BTP_COMBAT_GRAPHICS;s.combat.selected=0;
    btp_render(r,&s,0,pixels);CHECK(crop_hash(pixels,8,104,88,88)==UINT64_C(0x3d1a9af7f445b1fa));
    btp_start(&s);s.mode=BTP_ENTRY;s.entry_slot=0;btp_render(r,&s,0,pixels);
    CHECK(crop_hash(pixels,104,72,216,56)==UINT64_C(0x0121052b10ef7ecc));
    btp_start(&s);btp_npc_init(&s,&r->map);BtpNpcState before=s.npc;
    btp_game_tick(&s,r,BTP_OPEN_MENU);CHECK(s.mode==BTP_ACTIONS && btp_actions_count(&s)==7 && restore(&s,r));
    btp_render(r,&s,0,pixels);CHECK(crop_hash(pixels,104,96,216,72)==UINT64_C(0x37428c0880329ee8));
    CHECK(!strcmp(btp_actions_label(&s,1),"Change game settings"));
    for (unsigned i=0;i<20;++i) btp_game_tick(&s,r,BTP_IDLE);
    CHECK(!memcmp(&before,&s.npc,sizeof before));select_item(&s,r,1);CHECK(s.campaign.ui==BTP_MENU_SETTINGS && restore(&s,r));
    select_item(&s,r,0);CHECK(s.campaign.ui==BTP_MENU_STEPS && restore(&s,r));
    select_item(&s,r,2);CHECK(s.menu.steps==4 && s.mode==BTP_EXPLORE && restore(&s,r));
    unsigned tick=s.tick;btp_game_tick(&s,r,BTP_UP);CHECK(s.player_walk==8);CHECK(s.y_half==21 && s.tick==tick+1 && restore(&s,r));
    btp_game_tick(&s,r,BTP_UP);CHECK(s.mode==BTP_ENTRY && s.y_half==21 && restore(&s,r));
    btp_start(&s);btp_npc_init(&s,&r->map);
    const char *base="work/menu-slot-test.btp";
    for (unsigned slot=0;slot<6;++slot) {
        s.credits=35+slot;btp_game_tick(&s,r,BTP_OPEN_MENU);select_item(&s,r,5);
        CHECK(s.campaign.ui==BTP_MENU_SAVE);select_item(&s,r,slot);
        CHECK(s.menu.io==BTP_MENU_IO_SAVE && restore(&s,r));
        CHECK(btp_save_menu(&s,r,base,1,&e) && s.mode==BTP_EXPLORE);
        char path[256];CHECK(btp_save_slot_path(base,slot,path,sizeof path,&e));
        BtpState loaded;CHECK(btp_save_load(path,&loaded,r,&e) && loaded.credits==35+slot && loaded.menu.slot==slot);
    }
    for (unsigned slot=0;slot<6;++slot) {
        btp_game_tick(&s,r,BTP_OPEN_MENU);select_item(&s,r,4);select_item(&s,r,slot);
        CHECK(s.menu.io==BTP_MENU_IO_LOAD && restore(&s,r));
        CHECK(btp_save_menu(&s,r,base,1,&e) && s.credits==35+slot && s.mode==BTP_EXPLORE && restore(&s,r));
        char path[256];CHECK(btp_save_slot_path(base,slot,path,sizeof path,&e));CHECK(remove(path)==0);
    }
    unsigned cash=s.credits;btp_game_tick(&s,r,BTP_OPEN_MENU);select_item(&s,r,4);select_item(&s,r,0);
    CHECK(!btp_save_menu(&s,r,base,1,&e) && s.menu.notice==2 && s.credits==cash && restore(&s,r));
    btp_game_tick(&s,r,BTP_ACCEPT);CHECK(s.mode==BTP_EXPLORE);
    btp_game_tick(&s,r,BTP_OPEN_MENU);select_item(&s,r,1);select_item(&s,r,2);CHECK(!s.menu.sound && restore(&s,r));
    btp_game_tick(&s,r,BTP_OPEN_MENU);select_item(&s,r,6);CHECK(s.campaign.ui==BTP_MENU_MAP && restore(&s,r));
    btp_render(r,&s,0,pixels);
    /* Actual original revealed Citadel terrain, not just a map-page state. */
    CHECK(crop_hash(pixels,152,80,40,48)==UINT64_C(0x4b2db9fe1af195cf));
    unsigned x=s.x_half,y=s.y_half;btp_game_tick(&s,r,BTP_RIGHT);CHECK(s.x_half==x && s.y_half==y && restore(&s,r));
    btp_game_tick(&s,r,BTP_CANCEL);CHECK(s.mode==BTP_EXPLORE);
    btp_menu_open(&s);select_item(&s,r,2);btp_render(r,&s,0,pixels);
    CHECK(crop_hash(pixels,104,0,216,200)==UINT64_C(0x1491c6f034c5af95));
    CHECK(btp_save_load("Original DOS/GAME3",&s,r,&e));btp_menu_open(&s);btp_render(r,&s,0,pixels);
    CHECK(crop_hash(pixels,104,88,216,80)==UINT64_C(0xe2fb8696d8944791));select_item(&s,r,2);
    CHECK(s.campaign.ui==BTP_MENU_ALLOCATE && restore(&s,r));select_item(&s,r,0);select_item(&s,r,btp_menu_mech_count(&s));
    CHECK(!s.campaign.mounted && s.party.people[0][12]==8 && restore(&s,r));
    select_item(&s,r,1);select_item(&s,r,0);CHECK(s.party.people[1][12]==0 && restore(&s,r));
    select_item(&s,r,0);select_item(&s,r,1);CHECK(s.party.people[0][12]==1 && s.campaign.mounted && restore(&s,r));
    select_item(&s,r,btp_party_count(&s.party));CHECK(s.mode==BTP_EXPLORE && restore(&s,r));
    CHECK(btp_save_write("work/crew-menu.btp",&s,r,&e));
    btp_menu_open(&s);select_item(&s,r,3);CHECK(s.campaign.ui==BTP_MENU_INSPECT_KIND && restore(&s,r));
    select_item(&s,r,1);select_item(&s,r,0);btp_game_tick(&s,r,BTP_DOWN);
    CHECK(s.campaign.ui==BTP_MENU_TRANSFER && restore(&s,r));select_item(&s,r,0);select_item(&s,r,1);
    CHECK(s.party.people[0][11]==0 && s.weapon==0 && s.party.people[1][11]==9 && restore(&s,r));
    s.story_flags[41]=0;s.party.people[1][15]=1;btp_menu_open(&s);select_item(&s,r,4);
    CHECK(s.party.people[1][15]>1 && s.story_flags[41]==63 && restore(&s,r));
    unsigned health=s.party.people[1][15];btp_menu_close(&s);btp_menu_open(&s);select_item(&s,r,4);
    CHECK(s.party.people[1][15]==health && restore(&s,r));
    /* Original eight physical slots become a compact, stable person list. */
    s.party.people[1][0]=255;btp_menu_close(&s);btp_menu_open(&s);select_item(&s,r,3);select_item(&s,r,1);
    CHECK(btp_actions_count(&s)==3 && !strcmp(btp_actions_label(&s,1),btp_party_name(&s.party,2)));
    s.campaign.selected=2;uint8_t legacy[BTP_STATE_BYTES];btp_state_encode(&s,legacy);
    memcpy(legacy,"BTPN",4);legacy[4]=23;BtpState migrated;
    CHECK(btp_state_decode(legacy,16384,btp_active_map(r,&s),btp_state_bld(r,&s),&migrated) && migrated.campaign.selected==1);
    btp_start(&s);s.mode=BTP_LOGO;
    btp_game_tick(&s,r,BTP_CREDIT_10000);CHECK(s.mode==BTP_LOGO && s.credits==10035 && restore(&s,r));
    btp_game_tick(&s,r,BTP_CANCEL);CHECK(s.mode==BTP_LOGO);
    btp_game_tick(&s,r,BTP_OPEN_MENU);CHECK(s.mode==BTP_TITLE && restore(&s,r));
    btp_game_tick(&s,r,BTP_CREDIT_10000);CHECK(s.mode==BTP_TITLE && s.credits==20035 && restore(&s,r));
    btp_game_tick(&s,r,BTP_OPEN_MENU);CHECK(s.mode==BTP_BEGIN && s.entry_selected==1 && restore(&s,r));
    btp_game_tick(&s,r,BTP_CREDIT_10000);CHECK(s.mode==BTP_BEGIN && s.credits==30035);
    btp_game_tick(&s,r,BTP_UP);btp_game_tick(&s,r,BTP_ACCEPT);
    CHECK(s.campaign.ui==BTP_MENU_LOAD && s.menu.from_intro && btp_actions_count(&s)==7 && restore(&s,r));
    btp_render(r,&s,0,pixels);CHECK(crop_hash(pixels,8,104,88,64)==UINT64_C(0xfe5314b60fa5ed83));
    btp_game_tick(&s,r,BTP_ACCEPT);CHECK(s.menu.io==BTP_MENU_IO_LOAD);
    CHECK(!btp_save_menu(&s,r,base,1,&e) && s.menu.from_intro && restore(&s,r));
    btp_game_tick(&s,r,BTP_ACCEPT);CHECK(s.mode==BTP_BEGIN && restore(&s,r));
    btp_game_tick(&s,r,BTP_DOWN);btp_game_tick(&s,r,BTP_ACCEPT);
    CHECK(s.mode==BTP_EXPLORE && s.x_half==69 && s.y_half==25 && s.credits==30035 && restore(&s,r));
    free(pixels);free(r);printf("PASS: %u checks; original title pixels, Space menu, movement rate and all six save/load slots\n",checks);return 0;
}
