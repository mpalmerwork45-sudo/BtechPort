#include "core/menu.h"
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
    btp_start(&s);btp_npc_init(&s,&r->map);BtpNpcState before=s.npc;
    btp_game_tick(&s,r,BTP_OPEN_MENU);CHECK(s.mode==BTP_ACTIONS && btp_actions_count(&s)==7 && restore(&s,r));
    CHECK(!strcmp(btp_actions_label(&s,1),"Change game settings"));
    for (unsigned i=0;i<20;++i) btp_game_tick(&s,r,BTP_IDLE);
    CHECK(!memcmp(&before,&s.npc,sizeof before));select_item(&s,r,1);CHECK(s.campaign.ui==BTP_MENU_SETTINGS && restore(&s,r));
    select_item(&s,r,0);CHECK(s.campaign.ui==BTP_MENU_STEPS && restore(&s,r));
    select_item(&s,r,2);CHECK(s.menu.steps==4 && s.mode==BTP_EXPLORE && restore(&s,r));
    unsigned tick=s.tick;btp_game_tick(&s,r,BTP_UP);CHECK(s.y_half==21 && s.tick==tick+1 && restore(&s,r));
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
    unsigned x=s.x_half,y=s.y_half;btp_game_tick(&s,r,BTP_RIGHT);CHECK(s.x_half==x && s.y_half==y && restore(&s,r));
    btp_game_tick(&s,r,BTP_CANCEL);CHECK(s.mode==BTP_EXPLORE);
    free(pixels);free(r);printf("PASS: %u checks; original title pixels, Space menu, movement rate and all six save/load slots\n",checks);return 0;
}
