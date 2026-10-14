#include "core/menu.h"
#include "core/party.h"
#include "core/npc.h"
#include "core/service.h"
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
    btp_start(&s);s.mode=BTP_ENCOUNTER;s.combat.phase=BTP_COMBAT_OFFER;s.combat.friends=1;s.combat.count=2;
    s.combat.unit[1].infantry=1;s.combat.unit[1].record[0]=1;
    btp_render(r,&s,0,pixels);
    if (crop_hash(pixels,0,0,104,200)!=UINT64_C(0x199a78634f9be602)) (void)btp_write_ppm("work/m4-audit/engage-native.ppm",pixels);
    CHECK(crop_hash(pixels,0,0,104,200)==UINT64_C(0x199a78634f9be602));
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
    CHECK(btp_save_load("Original DOS/GAME3",&s,r,&e));btp_menu_open(&s);select_item(&s,r,3);
    btp_render(r,&s,0,pixels);CHECK(crop_hash(pixels,104,0,216,200)==UINT64_C(0x93675188807180be));
    select_item(&s,r,0);btp_render(r,&s,0,pixels);
    CHECK(crop_hash(pixels,104,0,216,200)==UINT64_C(0x35639aea2c8b0038));
    select_item(&s,r,0);CHECK(s.campaign.ui==BTP_MENU_MECH && restore(&s,r));
    BtpState spy_sheet=s;
    const uint8_t spy_record[17]={5,10,9,5,0,1,1,0,0,3,0,0,8,0,0,100,0};
    memcpy(spy_sheet.party.people[4],spy_record,17);
    spy_sheet.story_flags[37]=4;spy_sheet.story_flags[38]=spy_sheet.story_flags[39]=1;
    spy_sheet.campaign.ui=BTP_MENU_INSPECT;spy_sheet.campaign.member=4;
    btp_render(r,&spy_sheet,0,pixels);(void)btp_write_ppm("work/m4-audit/spy-sheet-native.ppm",pixels);
    CHECK(crop_hash(pixels,104,0,216,200)==UINT64_C(0xe49bd260b7c4f9d4));
    CHECK(restore(&spy_sheet,r));
    btp_game_tick(&s,r,BTP_OPEN_MENU);CHECK(s.mode==BTP_EXPLORE && restore(&s,r));
    btp_menu_open(&s);select_item(&s,r,2);btp_render(r,&s,0,pixels);
    CHECK(crop_hash(pixels,104,0,216,200)==UINT64_C(0x3b56096617a5b93e));
    BtpState speed=s;speed.mode=BTP_BUILDING;speed.campaign.building=5;
    speed.service=(BtpServiceState){.phase=1,.action=19};
    btp_render(r,&speed,0,pixels);CHECK(crop_hash(pixels,104,0,216,200)==UINT64_C(0x12dc86ee88e190c4));
    btp_menu_close(&s);btp_menu_open(&s);btp_render(r,&s,0,pixels);
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
    /* Original field treatment, 1791876954390161281/healing. Compare the
       complete held 216x80 message, including rank, kit, green patient and
       key prompt. The injury list must survive after health has changed. */
    {
        uint8_t raw[BTP_ORIGINAL_BYTES];FILE *source=fopen("Original DOS/GAME3","rb");CHECK(source);
        CHECK(fread(raw,1,sizeof raw,source)==sizeof raw && !fclose(source));
        raw[0xf45]=20;raw[0xf46]=10;raw[0xf47]=69;raw[0xf48]=128;
        for (unsigned i=0;i<8;++i) {
            raw[1+17*i+12]=8;
            if (raw[1+17*i]!=255) raw[1+17*i+15]=(uint8_t)(10u*raw[1+17*i+1]);
        }
        raw[1+17+15]=1;raw[1+3*17+10]=4;raw[0xcf9+41]=0;raw[1+0xd451-0xc614]=1;
        BtpState medical;CHECK(btp_original_decode(raw,sizeof raw,&medical,r,&e));
        btp_menu_open(&medical);select_item(&medical,r,4);
        CHECK(medical.service.phase==12 && medical.service.amount==2 && restore(&medical,r));
        btp_render(r,&medical,0,pixels);CHECK(btp_write_ppm("work/m4-audit/healing-native.ppm",pixels));
        CHECK(crop_hash(pixels,104,88,216,80)==UINT64_C(0x546612db066913d1));
        CHECK(btp_save_write("work/m4-audit/healing-held.btp",&medical,r,&e));
        unsigned hp=medical.party.people[1][15];btp_game_tick(&medical,r,BTP_ACCEPT);
        CHECK(!medical.service.phase && medical.mode==BTP_EXPLORE && medical.party.people[1][15]==hp);
        /* Separate live captures establish the short notice's full border,
           and the hospital's doctor/Medkit wording on the held treatment. */
        btp_menu_open(&medical);select_item(&medical,r,4);
        btp_render(r,&medical,0,pixels);CHECK(crop_hash(pixels,104,72,216,56)==UINT64_C(0x777eadbe7e85cabf));
        btp_game_tick(&medical,r,BTP_ACCEPT);medical.story_flags[41]=0;
        for (unsigned i=0;i<8;++i) if (medical.party.people[i][0]!=255)
            medical.party.people[i][15]=(uint8_t)(10u*medical.party.people[i][1]);
        btp_menu_open(&medical);select_item(&medical,r,4);
        btp_render(r,&medical,0,pixels);CHECK(crop_hash(pixels,104,72,216,56)==UINT64_C(0x2d569d958cd1a475));
        btp_game_tick(&medical,r,BTP_ACCEPT);medical.party.people[1][15]=1;medical.story_flags[41]=0;
        btp_service_heal(&medical,r,1,1);
        /* Present this controlled hospital result through the same held
           medical panel; ordinary paid clinic/save flow has its own route. */
        medical.mode=BTP_ACTIONS;medical.campaign.ui=BTP_MENU_MESSAGE;medical.menu.notice=3;
        btp_render(r,&medical,0,pixels);CHECK(crop_hash(pixels,104,88,216,80)==UINT64_C(0x9cf65a8f41a01993));
        /* A real treatment, followed immediately by Heal again, reaches
           0C31's healthy-with-active-cooldown branch. The DOS capture has
           all four people at full health and flag 41 still equal to 57. */
        raw[1+17+15]=119;CHECK(btp_original_decode(raw,sizeof raw,&medical,r,&e));
        btp_menu_open(&medical);select_item(&medical,r,4);
        CHECK(medical.service.phase==12 && !medical.service.outcome && medical.party.people[1][15]==120);
        btp_game_tick(&medical,r,BTP_ACCEPT);CHECK(medical.story_flags[41]);
        btp_menu_open(&medical);select_item(&medical,r,4);
        CHECK(medical.service.outcome==3 && !medical.service.amount && restore(&medical,r));
        btp_render(r,&medical,0,pixels);CHECK(crop_hash(pixels,104,72,216,56)==UINT64_C(0x2d569d958cd1a475));
        CHECK(btp_save_write("work/m4-audit/healing-healthy-cooldown.btp",&medical,r,&e));
        BtpState resumed;CHECK(btp_save_load("work/m4-audit/healing-healthy-cooldown.btp",&resumed,r,&e));
        uint8_t healed[136];memcpy(healed,medical.party.people,sizeof healed);
        unsigned balance=medical.credits;btp_game_tick(&medical,r,BTP_ACCEPT);
        btp_game_tick(&resumed,r,BTP_ACCEPT);
        uint8_t continued[BTP_STATE_BYTES],loaded[BTP_STATE_BYTES];
        btp_state_encode(&medical,continued);btp_state_encode(&resumed,loaded);CHECK(!memcmp(continued,loaded,sizeof loaded));
        CHECK(!medical.service.phase && medical.mode==BTP_EXPLORE && medical.credits==balance &&
            !memcmp(healed,medical.party.people,sizeof healed));
    }
    /* Original eight physical slots become a compact, stable person list. */
    s.party.people[1][0]=255;btp_menu_close(&s);btp_menu_open(&s);select_item(&s,r,3);select_item(&s,r,1);
    CHECK(btp_actions_count(&s)==3 && !strcmp(btp_actions_label(&s,1),btp_party_name(&s.party,2)));
    s.campaign.selected=2;uint8_t legacy[BTP_STATE_BYTES];btp_state_encode(&s,legacy);
    /* v23 used local map identifiers for debris, so modern sector marks do
       not belong in this synthetic legacy character-selector fixture. */
    memset(legacy+2048,0,257);
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
