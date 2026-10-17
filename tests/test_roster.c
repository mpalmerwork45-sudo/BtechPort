#include "data/content.h"
#include "data/save.h"
#include "data/unit_data.h"
#include "core/roster_game.h"
#include "core/menu.h"
#include "core/party.h"
#include "core/campaign.h"
#include "core/service.h"
#include "core/npc.h"
#include "frontend/pixels.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"FAIL %s:%d: %s\n",__FILE__,__LINE__,#x);exit(1); } } while (0)
static BtpError error;
/* Mass, walking/jumping, cooling and weapon counts cross-checked against the
   source records listed in content/updated/README.md (not computed from JSON). */
static const unsigned specs[][6]={
    {35,4,4,13,2,146},{50,4,0,13,4,146},{65,4,4,15,6,0},
    {50,4,0,10,4,146},{50,5,0,10,5,146},{55,5,5,12,2,146},
    {55,5,3,12,4,146},{55,5,5,12,3,146},{60,4,0,10,6,146},
    {65,4,0,15,8,146},{70,4,0,10,6,146},{70,4,0,18,9,146},
    {75,4,0,16,5,0},{80,4,0,17,5,146},{100,3,0,20,7,146},
    {65,4,0,10,8,146},{65,4,0,18,8,146},
    {45,6,6,10,5,146},{60,5,0,10,4,146},{70,4,4,22,6,146},
    {90,3,3,13,5,146},{85,3,0,20,10,0},{35,7,5,10,5,0}
};
static void save_check(BtpState *s,BtpState *copy,const BtpResources *r);
static void setup(BtpState *s,const BtpResources *r)
{
    btp_start(s);s->story_flags[4]=1;s->story_flags[36]=127;s->map_id=2;s->x_half=54;s->y_half=51;
    s->campaign.world_x=1334;s->campaign.world_y=1075;s->credits=200000;s->mech_skills[1]=1;
    btp_npc_enter(s,&r->local[1]);btp_party_init(s);
}
static void enter_broker(BtpState *s,BtpState *copy,const BtpResources *r)
{
    btp_game_tick(s,r,BTP_UP);
    CHECK(s->mode==BTP_ENTRY && s->entry_slot==BTP_BROKER_ENTRY && btp_building_kind(r,s)==BTP_BROKER_BUILDING);
    save_check(s,copy,r);btp_game_tick(s,r,BTP_ACCEPT);
    CHECK(s->campaign.ui==BTP_MENU_BROKER_HUB && btp_broker_available(s,r));save_check(s,copy,r);
}
static void save_check(BtpState *s,BtpState *copy,const BtpResources *r)
{
    if (!btp_save_write("btp-roster-held.btp",s,r,&error)) fprintf(stderr,"%s (ui %u)\n",error.text,s->campaign.ui);
    else {
        CHECK(btp_save_load("btp-roster-held.btp",copy,r,&error));
        uint8_t a[BTP_STATE_BYTES],b[BTP_STATE_BYTES];btp_state_encode(s,a);btp_state_encode(copy,b);
        CHECK(!memcmp(a,b,sizeof a));CHECK(!remove("btp-roster-held.btp"));return;
    }
    CHECK(0);
}
static void services(BtpState *s,BtpState *copy,const BtpResources *r,const char *directory,unsigned model)
{
    /* Enter the real REPAIR.BLD from the existing GAME3 test context. Check
       each held repair/ammo/refit step, not just the underlying arithmetic. */
    char path[4096];snprintf(path,sizeof path,"%s/GAME3",directory);
    FILE *f=fopen(path,"rb");uint8_t raw[BTP_ORIGINAL_BYTES];CHECK(f);
    CHECK(fread(raw,1,sizeof raw,f)==sizeof raw && !fclose(f));
    raw[0xf45]=20;raw[0xf46]=10;raw[0xf47]=69;raw[0xf48]=128;
    raw[0xcf9+24]=0;raw[0xcf9+36]=127;raw[0xcf9+39]=0;
    for (unsigned i=0;i<8;++i) raw[1+17*i+12]=8;
    for (unsigned menu=1;menu<=3;++menu) {
        CHECK(btp_original_decode(raw,sizeof raw,s,r,&error));
        memcpy(s->campaign.mech,r->roster.mechs[model].record,125);
        s->party.mech_types[0]=s->campaign.mech[0];s->credits=100000;
        uint8_t *m=s->campaign.mech;
        if (menu==2) { --m[17];for (unsigned i=51;i<86;++i) if (m[i]>=16 && m[i]<=32) { m[i]|=128;break; } }
        if (menu==3) for (unsigned i=0;i<10;++i) if (r->roster.mechs[model].ammo_cost[i]) m[39+i]=0;
        btp_game_tick(s,r,BTP_UP);btp_game_tick(s,r,BTP_ACCEPT);
        CHECK(s->script.status==BTP_SCRIPT_MENU);
        for (unsigned i=0;i<menu;++i) btp_game_tick(s,r,BTP_DOWN);
        btp_game_tick(s,r,BTP_ACCEPT);
        /* The refit description pauses before asking which mech to improve. */
        for (unsigned i=0;i<24 && !s->service.phase;++i) btp_game_tick(s,r,BTP_ACCEPT);
        CHECK(s->service.phase==1);save_check(s,copy,r);btp_game_tick(s,r,BTP_ACCEPT);
        for (unsigned i=0;i<128 && (s->service.phase || s->script.status!=BTP_SCRIPT_MENU);++i) {
            CHECK(s->mode!=BTP_SCRIPT_FAULT);save_check(s,copy,r);
            if (s->service.phase==5) btp_game_tick(s,r,BTP_DIGIT_3);
            btp_game_tick(s,r,BTP_ACCEPT);
        }
        CHECK(!s->service.phase && s->script.status==BTP_SCRIPT_MENU);
        CHECK(m[123]==r->roster.mechs[model].record[123]);
        if (menu==1) CHECK(s->credits==100000 && !memcmp(m,r->roster.mechs[model].record,125));
        if (menu==2) {
            CHECK(m[17]==m[86]);
            for (unsigned i=51;i<86;++i) CHECK(!(m[i]&128u));
        }
        if (menu==3) for (unsigned i=0;i<10;++i) if (r->roster.mechs[model].ammo_cost[i]) CHECK(m[39+i]==3);
    }
}
static void checkout(BtpState *s,BtpState *copy,const BtpResources *r,unsigned bay)
{
    unsigned code=bay<4 ? btp_party_mech(s,bay)[123] : 0;
    btp_game_tick(s,r,BTP_CANCEL);CHECK(s->mode==BTP_EXPLORE);
    const BtpMap *map=&r->local[1];unsigned entry=0;
    while (entry<16 && map->room_map[entry]!=8) ++entry;
    CHECK(entry<16);s->x_half=map->entrance_x[entry]&127u;s->y_half=(uint16_t)((map->entrance_y[entry]&127u)+1u);
    s->campaign.world_x=(uint16_t)((map->entrance_x[0]>>8)*128u+s->x_half);
    s->campaign.world_y=(uint16_t)((map->entrance_y[0]>>12)*128u+s->y_half);
    s->party.x[0]=s->campaign.world_x;s->party.y[0]=s->campaign.world_y;
    btp_game_tick(s,r,BTP_UP);CHECK(s->mode==BTP_ENTRY);btp_game_tick(s,r,BTP_ACCEPT);
    for (unsigned i=0;i<32 && s->campaign.ui!=BTP_MENU_ALLOCATE && s->mode!=BTP_EXPLORE;++i) {
        CHECK(s->mode!=BTP_SCRIPT_FAULT);save_check(s,copy,r);
        if (s->script.status==BTP_SCRIPT_CONFIRM && s->script.confirm_selected) btp_game_tick(s,r,BTP_LEFT);
        btp_game_tick(s,r,BTP_ACCEPT);
    }
    if (bay<4) {
        CHECK(s->campaign.ui==BTP_MENU_ALLOCATE);save_check(s,copy,r);
        btp_game_tick(s,r,BTP_ACCEPT);CHECK(s->campaign.ui==BTP_MENU_CREW);
        CHECK(btp_menu_mech_count(s)==btp_broker_count(s));
        unsigned choice=0;while (choice<4 && btp_menu_mech_slot(s,choice)!=bay) ++choice;CHECK(choice<4);
        for (unsigned i=0;i<choice;++i) btp_game_tick(s,r,BTP_DOWN);
        /* An empty cockpit takes the qualified pilot immediately, including
           a later bay after an earlier owned vehicle has been sold. */
        btp_game_tick(s,r,BTP_ACCEPT);CHECK(s->campaign.ui==BTP_MENU_ALLOCATE);
        CHECK(btp_party_mech(s,bay)[121]==0 && s->party.people[0][12]==bay);
    }
    if (s->campaign.ui==BTP_MENU_ALLOCATE) { btp_game_tick(s,r,BTP_DOWN);btp_game_tick(s,r,BTP_ACCEPT); }
    for (unsigned i=0;i<32 && s->mode!=BTP_EXPLORE;++i) btp_game_tick(s,r,BTP_ACCEPT);
    CHECK(s->mode==BTP_EXPLORE && s->campaign.mounted==(bay<4) && !s->story_flags[24]);
    if (bay<4) CHECK(btp_party_mech(s,bay)[123]==code);
    save_check(s,copy,r);
}
static void garage(BtpState *s,BtpState *copy,const BtpResources *r,unsigned model)
{
    setup(s,r);enter_broker(s,copy,r);CHECK(btp_broker_buy(s,r,model)==BTP_BROKER_BOUGHT);
    checkout(s,copy,r,0);
}
static void sales(BtpState *s,BtpState *copy,BtpState *before,const BtpResources *r)
{
    setup(s,r);enter_broker(s,copy,r);
    for (unsigned i=0;i<4;++i) CHECK(btp_broker_buy(s,r,i%3)==BTP_BROKER_BOUGHT);
    CHECK(btp_broker_count(s)==4);
    /* Two further purchases through the UI must leave all four records and
       the wallet unchanged. Full capacity is a held, saveable result. */
    btp_game_tick(s,r,BTP_ACCEPT);
    for (unsigned attempt=0;attempt<2;++attempt) {
        *before=*s;btp_game_tick(s,r,BTP_ACCEPT);btp_game_tick(s,r,BTP_UP);btp_game_tick(s,r,BTP_ACCEPT);
        CHECK(s->menu.notice==BTP_BROKER_FULL && s->credits==before->credits);
        CHECK(!memcmp(s->campaign.mech,before->campaign.mech,125) && !memcmp(s->party.mechs,before->party.mechs,375));
        save_check(s,copy,r);btp_game_tick(s,r,BTP_ACCEPT);
    }
    btp_game_tick(s,r,BTP_CANCEL);btp_game_tick(s,r,BTP_DOWN);btp_game_tick(s,r,BTP_ACCEPT);
    CHECK(s->campaign.ui==BTP_MENU_BROKER_SELL && btp_actions_count(s)==5);save_check(s,copy,r);
    CHECK(btp_broker_offer(s,r,1)==r->roster.mechs[1].price/2);
    uint8_t *m=btp_party_mech(s,1);m[17]=0;m[117]=2;
    CHECK(btp_broker_offer(s,r,1)<r->roster.mechs[1].price/2);
    btp_game_tick(s,r,BTP_DOWN);btp_game_tick(s,r,BTP_ACCEPT);
    CHECK(s->campaign.ui==BTP_MENU_BROKER_SELL_CONFIRM && s->menu.map_y==1 && s->campaign.selected==1);
    *before=*s;save_check(s,copy,r);btp_game_tick(s,r,BTP_ACCEPT);
    CHECK(s->campaign.ui==BTP_MENU_BROKER_SELL && s->credits==before->credits && btp_broker_count(s)==4);
    CHECK(!memcmp(m,btp_party_mech(before,1),125));
    btp_game_tick(s,r,BTP_DOWN);btp_game_tick(s,r,BTP_ACCEPT);btp_game_tick(s,r,BTP_CANCEL);
    CHECK(btp_broker_count(s)==4 && s->credits==before->credits);
    btp_game_tick(s,r,BTP_DOWN);btp_game_tick(s,r,BTP_ACCEPT);
    unsigned offer=btp_broker_offer(s,r,1),credits=s->credits;
    btp_game_tick(s,r,BTP_UP);btp_game_tick(s,r,BTP_ACCEPT);
    CHECK(s->campaign.ui==BTP_MENU_BROKER_SELL_RESULT && s->menu.notice==BTP_BROKER_SOLD);
    CHECK(s->credits==credits+offer && btp_broker_count(s)==3 && !btp_broker_owned(s,1));
    CHECK(m[0]==255 && m[121]==255 && m[122]==255 && !btp_roster_custom(m));
    for (unsigned i=0;i<4;++i) if (i!=1) CHECK(!memcmp(btp_party_mech(s,i),btp_party_mech(before,i),125));
    save_check(s,copy,r);btp_game_tick(s,r,BTP_ACCEPT);
    CHECK(btp_actions_count(s)==4 && btp_broker_slot(s,1)==2);
    CHECK(btp_broker_buy(s,r,2)==BTP_BROKER_BOUGHT && btp_broker_count(s)==4);
    CHECK(btp_roster_definition(&r->roster,m)==&r->roster.mechs[2]);save_check(s,copy,r);
    /* Overflow, original chassis and stale seat references are transactional.
       Sale never deletes the pilot/passenger or shifts another bay's record. */
    s->credits=UINT32_MAX;*before=*s;
    CHECK(btp_broker_sell(s,r,2)==BTP_BROKER_CREDIT_LIMIT && !memcmp(s,before,sizeof *s));
    s->credits=0;
    memcpy(m,r->combat.loans[0],125);s->party.mech_types[1]=m[0];m[0]=255;
    CHECK(btp_broker_offer(s,r,1)==(unsigned)m[16]*100u);
    memcpy(s->party.people[1],s->party.people[0],17);s->party.people[1][0]=1;
    s->party.people[1][12]=1;m[121]=1;*before=*s;
    CHECK(btp_broker_sell(s,r,1)==BTP_BROKER_SOLD && s->party.people[1][12]==8);
    CHECK(!memcmp(s->party.people[1],before->party.people[1],12));
    for (unsigned i=0;i<4;++i) if (btp_broker_owned(s,i)) CHECK(btp_broker_sell(s,r,i)==BTP_BROKER_SOLD);
    CHECK(!s->campaign.owned && !btp_broker_count(s) && btp_actions_count(s)==1 && s->story_flags[24]);
    save_check(s,copy,r);CHECK(btp_broker_buy(s,r,0)==BTP_BROKER_BOUGHT && btp_broker_slot(s,0)==0);
    save_check(s,copy,r);
}
static void bars(const BtpResources *r,uint32_t *frame,const char *capture)
{
    uint32_t *empty=malloc(BTP_PIXELS*sizeof *empty);CHECK(empty);
    /* Compare an empty diagram against intact, damaged and extreme records.
       Only the original eleven six-pixel wells may change; damage must reduce
       filled area, rather than rescale a damaged mech back to full height. */
    static const unsigned wells[][4]={{248,64,253,87},{208,32,213,55},{224,128,229,151},
        {192,16,197,31},{192,48,197,71},{136,64,141,87},{176,32,181,55},
        {160,128,165,151},{272,112,277,135},{288,120,293,143},{304,112,309,135}};
    for (unsigned model=0;model<=r->roster.count;++model) {
        uint8_t m[125];memcpy(m,r->roster.mechs[model%r->roster.count].record,125);
        if (model==r->roster.count) { memset(m+17,255,19);memset(m+86,255,19); }
        uint8_t blank[125];memcpy(blank,m,125);memset(blank+17,0,19);
        btp_mech_screen(r,blank,"Jason","None",0,0,empty);
        unsigned full=0;
        for (unsigned damage=0;damage<2;++damage) {
            if (damage) for (unsigned i=17;i<36;++i) m[i]/=2;
            btp_mech_screen(r,m,"Jason","None",0,0,frame);unsigned filled=0;
            if (capture && model<r->roster.count) {
                char path[4096];snprintf(path,sizeof path,"%s-inspect-%u-%u.ppm",capture,model,damage);
                CHECK(btp_write_ppm(path,frame));
            }
            for (unsigned y=0;y<200;++y) for (unsigned x=128;x<320;++x) if (frame[y*320+x]!=empty[y*320+x]) {
                int inside=0;
                for (unsigned i=0;i<11;++i) if (x>=wells[i][0] && x<=wells[i][2] && y>=wells[i][1] && y<=wells[i][3]) inside=1;
                CHECK(inside);++filled;
            }
            CHECK(filled);if (damage) CHECK(filled<full);else full=filled;
        }
    }
    free(empty);
}
static void old_save(const BtpState *s,const BtpRoster *roster,unsigned version)
{
    uint8_t bytes[112+BTP_STATE_BYTES]={0};memcpy(bytes,"BTU1",4);
    memcpy(bytes+16,roster->package,32);memcpy(bytes+48,roster->version,32);
    btp_state_encode(s,bytes+112);memcpy(bytes+112,version==41 ? "BTPf" : "BTPg",4);bytes[116]=(uint8_t)version;
    for (unsigned i=0;i<4;++i) { bytes[4+i]=(uint8_t)((sizeof bytes-16)>>(8*i));bytes[80+i]=(uint8_t)(roster->fingerprint>>(8*i)); }
    uint32_t crc=UINT32_MAX;
    for (unsigned i=16;i<sizeof bytes;++i) { crc^=bytes[i];for (unsigned bit=0;bit<8;++bit) crc=(crc>>1)^((crc&1u) ? UINT32_C(0xedb88320) : 0u); }
    crc=~crc;for (unsigned i=0;i<4;++i) bytes[8+i]=(uint8_t)(crc>>(8*i));
    FILE *f=fopen("btp-roster-legacy.btp","wb");CHECK(f && fwrite(bytes,1,sizeof bytes,f)==sizeof bytes && !fclose(f));
}
static void legacy_broker(BtpState *s,BtpState *copy,const BtpResources *r)
{
    /* Build the former BTU1/v41 wire format, including its old Space entry.
       Loading must migrate held menus while retaining choices and purchases. */
    for (unsigned ui=BTP_MENU_UPDATED_ROOT;ui<=BTP_MENU_BROKER_RESULT;++ui) {
        setup(s,r);enter_broker(s,copy,r);CHECK(btp_broker_buy(s,r,1)==BTP_BROKER_BOUGHT);
        s->campaign.building=0;s->entry_slot=0;s->campaign.ui=(uint8_t)ui;
        s->menu.map_x=(uint16_t)r->roster.count;s->menu.map_y=1;s->campaign.selected=(uint8_t)(ui==24 ? 7 : ui==27 ? 0 : 1);
        s->menu.notice=(uint8_t)(ui==27 ? BTP_BROKER_BOUGHT : 0);
        old_save(s,&r->roster,41);
        CHECK(btp_save_load("btp-roster-legacy.btp",copy,r,&error));CHECK(!remove("btp-roster-legacy.btp"));
        CHECK(copy->credits==s->credits && !memcmp(copy->campaign.mech,s->campaign.mech,125));
        CHECK(copy->campaign.ui==(ui==24 ? BTP_MENU_ROOT : ui));
        if (ui!=24) CHECK(btp_broker_available(copy,r));
        save_check(copy,s,r);
    }
}
static void extension_saves(BtpState *s,BtpState *copy,BtpState *before,BtpResources *r,const char *roster_path)
{
    BtpRoster *current=malloc(sizeof *current),*previous=malloc(sizeof *previous);CHECK(current && previous);
    *current=r->roster;char path[4096],diagnostic[256];
    size_t parent=0;
    for (size_t i=0;roster_path[i];++i) if (roster_path[i]=='/' || roster_path[i]=='\\') parent=i+1u;
    snprintf(path,sizeof path,"%.*sversions/0.1.0.json",(int)parent,roster_path);
    CHECK(btp_roster_load(path,previous,diagnostic));CHECK(previous->count==3 && previous->fingerprint==UINT32_C(4022610150));
    CHECK(!memcmp(current->mechs,previous->mechs,3*sizeof previous->mechs[0]));
    for (unsigned version=41;version<=42;++version) for (unsigned scene=0;scene<10;++scene) {
        r->roster=*previous;setup(s,r);enter_broker(s,copy,r);
        for (unsigned model=0;model<3;++model) CHECK(btp_broker_buy(s,r,model)==BTP_BROKER_BOUGHT);
        s->campaign.mech[17]-=2; /* Keep existing damage and spent ammunition. */
        btp_party_mech(s,2)[39]=2;
        s->menu.map_x=3;s->menu.map_y=2;
        if (!scene) btp_game_tick(s,r,BTP_CANCEL);
        else if (scene<=4) { s->campaign.ui=BTP_MENU_BROKER;s->campaign.selected=(uint8_t)(scene-1); }
        else if (scene<=6) { s->campaign.ui=BTP_MENU_BROKER_CONFIRM;s->campaign.selected=(uint8_t)(scene-5); }
        else if (scene==7) { s->campaign.ui=BTP_MENU_BROKER_RESULT;s->menu.notice=BTP_BROKER_BOUGHT; }
        else if (scene==8) { s->campaign.ui=BTP_MENU_ROOT;s->campaign.building=0;s->entry_slot=0; }
        else { s->campaign.ui=BTP_MENU_BROKER_HUB; }
        if (version==41 && btp_broker_page(s->campaign.ui)) {
            if (s->campaign.ui==BTP_MENU_BROKER_HUB) s->campaign.ui=BTP_MENU_UPDATED_ROOT;
            s->campaign.building=0;s->entry_slot=0;
        }
        old_save(s,previous,version);*before=*s;r->roster=*current;
        CHECK(btp_save_load("btp-roster-legacy.btp",copy,r,&error));
        CHECK(copy->credits==before->credits && !memcmp(copy->campaign.mech,before->campaign.mech,125));
        CHECK(!memcmp(copy->party.mechs,before->party.mechs,sizeof copy->party.mechs));
        CHECK(!memcmp(copy->party.people,before->party.people,sizeof copy->party.people));
        if (scene>=1 && scene<=4) {
            CHECK(copy->campaign.member+copy->campaign.selected==(scene==4 ? current->count : scene-1));
            btp_game_tick(copy,r,BTP_ACCEPT);
            CHECK(copy->campaign.ui==(scene==4 ? BTP_MENU_BROKER_HUB : BTP_MENU_BROKER_CONFIRM));
            if (scene!=4) CHECK(copy->menu.map_y==scene-1);
        } else if (scene==5 || scene==6) {
            CHECK(copy->campaign.selected==scene-5 && copy->menu.map_y==2);
            btp_game_tick(copy,r,BTP_ACCEPT);
            CHECK(copy->credits==before->credits-(scene==5 ? current->mechs[2].price : 0));
        }
        save_check(copy,s,r);
    }
    /* An old hash cannot authorize an edited old unit, a removed definition,
       a wrong package, or a record introduced after that saved catalogue. */
    r->roster=*previous;setup(s,r);enter_broker(s,copy,r);CHECK(btp_broker_buy(s,r,0)==BTP_BROKER_BOUGHT);
    old_save(s,previous,42);r->roster=*current;*before=*copy;
    for (unsigned edit=0;edit<7;++edit) {
        if (edit==0) ++r->roster.mechs[0].price;
        if (edit==1) ++r->roster.mechs[0].ammo_cost[0];
        if (edit==2) ++r->roster.mechs[0].record[17];
        if (edit==3) ++r->roster.mechs[0].id[5];
        if (edit==4) r->roster.count=2;
        if (edit==5) r->roster.package[0]='x';
        if (edit==6) r->roster.mechs[0].record[124]^=1;
        CHECK(!btp_save_load("btp-roster-legacy.btp",copy,r,&error) && !memcmp(copy,before,sizeof *copy));
        r->roster=*current;
    }
    memcpy(s->campaign.mech,current->mechs[14].record,125);old_save(s,previous,42);
    CHECK(!btp_save_load("btp-roster-legacy.btp",copy,r,&error) && !memcmp(copy,before,sizeof *copy));
    CHECK(!remove("btp-roster-legacy.btp"));
    /* The released 17-model pack already wrote v43 scrolling menus. Appending
       six models must retain scrolled choices, old Back, and pending Yes/No. */
    snprintf(path,sizeof path,"%.*sversions/0.2.0.json",(int)parent,roster_path);
    CHECK(btp_roster_load(path,previous,diagnostic));
    CHECK(previous->count==17 && previous->fingerprint==UINT32_C(751321522));
    CHECK(!memcmp(current->mechs,previous->mechs,17*sizeof previous->mechs[0]));
    static const unsigned choices[]={0,7,8,16,17};
    for (unsigned scene=0;scene<9;++scene) {
        r->roster=*previous;setup(s,r);enter_broker(s,copy,r);
        CHECK(btp_broker_buy(s,r,13)==BTP_BROKER_BOUGHT);
        CHECK(btp_broker_buy(s,r,14)==BTP_BROKER_BOUGHT);
        CHECK(btp_broker_buy(s,r,16)==BTP_BROKER_BOUGHT);
        s->campaign.mech[17]-=2;btp_party_mech(s,2)[39]=2;
        if (!scene) btp_game_tick(s,r,BTP_CANCEL);
        else if (scene<8) {
            btp_game_tick(s,r,BTP_ACCEPT);
            unsigned choice=scene<=5 ? choices[scene-1] : 16;
            for (unsigned i=0;i<choice;++i) btp_game_tick(s,r,BTP_DOWN);
            if (scene>=6) {
                btp_game_tick(s,r,BTP_ACCEPT);
                if (scene==6) btp_game_tick(s,r,BTP_UP);
            }
        }
        CHECK(btp_save_write("btp-roster-legacy.btp",s,r,&error));
        *before=*s;r->roster=*current;
        CHECK(btp_save_load("btp-roster-legacy.btp",copy,r,&error));
        CHECK(copy->credits==before->credits && !memcmp(copy->campaign.mech,before->campaign.mech,125));
        CHECK(!memcmp(copy->party.mechs,before->party.mechs,sizeof copy->party.mechs));
        CHECK(!memcmp(copy->party.people,before->party.people,sizeof copy->party.people));
        if (scene>=1 && scene<=5) {
            unsigned choice=choices[scene-1];
            CHECK(copy->campaign.member+copy->campaign.selected==(choice==17 ? current->count : choice));
            btp_game_tick(copy,r,BTP_ACCEPT);
            CHECK(copy->campaign.ui==(choice==17 ? BTP_MENU_BROKER_HUB : BTP_MENU_BROKER_CONFIRM));
            if (choice<17) CHECK(copy->menu.map_y==choice);
        } else if (scene==6 || scene==7) {
            CHECK(copy->campaign.selected==scene-6 && copy->menu.map_y==16);
            btp_game_tick(copy,r,BTP_ACCEPT);
            CHECK(copy->credits==before->credits-(scene==6 ? current->mechs[16].price : 0));
        }
        save_check(copy,s,r);
    }
    CHECK(!remove("btp-roster-legacy.btp"));free(previous);free(current);
}
static void scrolling(BtpState *s,BtpState *copy,const BtpResources *r,uint32_t *frame)
{
    setup(s,r);enter_broker(s,copy,r);btp_game_tick(s,r,BTP_ACCEPT);
    unsigned total=r->roster.count+1u;
    /* Both directions cross viewport edges, wrap, and retain the exact row
       on save/load. Rendering every row exercises the bottom border too. */
    for (unsigned direction=0;direction<2;++direction) for (unsigned step=0;step<total;++step) {
        CHECK(s->campaign.member+s->campaign.selected==(direction ? (total-step)%total : step));
        CHECK(s->campaign.selected<btp_actions_count(s));save_check(s,copy,r);btp_render(r,s,0,frame);
        btp_game_tick(s,r,direction ? BTP_UP : BTP_DOWN);
    }
    btp_game_tick(s,r,BTP_RIGHT);CHECK(s->campaign.member+s->campaign.selected==8);
    btp_game_tick(s,r,BTP_LEFT);CHECK(!s->campaign.member && !s->campaign.selected);
    btp_game_tick(s,r,BTP_UP);btp_game_tick(s,r,BTP_OPEN_MENU);
    CHECK(s->campaign.ui==BTP_MENU_BROKER_HUB);
    /* Existing large v42 packs used pages with an extra Back on each page. */
    for (unsigned first=0;first<r->roster.count;first+=7) {
        unsigned rows=r->roster.count-first;if (rows>7) rows=7;
        for (unsigned item=0;item<=rows;++item) {
            s->campaign.ui=BTP_MENU_BROKER;s->campaign.member=(uint8_t)(first/7u);
            s->campaign.selected=(uint8_t)item;old_save(s,&r->roster,42);
            CHECK(btp_save_load("btp-roster-legacy.btp",copy,r,&error));
            CHECK(copy->campaign.member+copy->campaign.selected==(item==rows ? r->roster.count : first+item));
            save_check(copy,s,r);
        }
    }
    CHECK(!remove("btp-roster-legacy.btp"));
}
int main(int argc,char **argv)
{
    CHECK(argc==6 || argc==7);
    BtpOriginalContentPaths paths={argv[1],argv[2],argv[3],argv[4]};
    BtpContent content={0},original={0};
    CHECK(btp_content_load_original(&content,&paths,&error));
    CHECK(btp_content_load_original(&original,&paths,&error));
    CHECK(btp_content_select(&content,BTP_CONTENT_UPDATED,argv[5],&error));
    BtpResources *r=content.resources;
    CHECK(r->roster.count==sizeof specs/sizeof specs[0] && !memcmp(&r->combat,&original.resources->combat,sizeof r->combat));
    BtpState *s=calloc(1,sizeof *s),*copy=calloc(1,sizeof *copy),*before=calloc(1,sizeof *before);
    uint32_t *frame=malloc(BTP_PIXELS*sizeof *frame);
    CHECK(s && copy && before && frame);
    /* Optional valid Starport checkpoint for bounded SDL purchase checks. */
    if (argc==7) { setup(s,r);CHECK(btp_save_write(argv[6],s,r,&error)); }
    setup(s,r);btp_game_tick(s,r,BTP_OPEN_MENU);
    CHECK(s->campaign.ui==BTP_MENU_ROOT && btp_actions_count(s)==7);
    setup(s,original.resources);btp_game_tick(s,original.resources,BTP_UP);
    CHECK(s->mode==BTP_EXPLORE && !btp_broker_available(s,original.resources));
    setup(s,r);btp_game_tick(s,r,BTP_UP);btp_game_tick(s,r,BTP_DOWN);btp_game_tick(s,r,BTP_ACCEPT);
    CHECK(s->mode==BTP_EXPLORE && s->campaign.building!=BTP_BROKER_BUILDING);save_check(s,copy,r);
    sales(s,copy,before,r);bars(r,frame,argc==7 ? argv[6] : NULL);legacy_broker(s,copy,r);
    extension_saves(s,copy,before,r,argv[5]);scrolling(s,copy,r,frame);
    setup(s,r);enter_broker(s,copy,r);
    for (unsigned i=0;i<4;++i) CHECK(btp_broker_buy(s,r,i%3)==BTP_BROKER_BOUGHT);
    CHECK(btp_broker_sell(s,r,0)==BTP_BROKER_SOLD);checkout(s,copy,r,3);
    setup(s,r);enter_broker(s,copy,r);CHECK(btp_broker_buy(s,r,0)==BTP_BROKER_BOUGHT);
    CHECK(btp_broker_sell(s,r,0)==BTP_BROKER_SOLD);checkout(s,copy,r,4);
    /* Use the real menu and purchase confirmation, including held save/load,
       then exercise the shared gameplay operations on each delivered model. */
    for (unsigned model=0;model<r->roster.count;++model) {
        const BtpRosterMech *d=&r->roster.mechs[model];setup(s,r);enter_broker(s,copy,r);
        s->credits=d->price-1;*before=*s;
        CHECK(btp_broker_buy(s,r,model)==BTP_BROKER_NO_FUNDS && !memcmp(s,before,sizeof *s));
        s->credits=200000;
        btp_game_tick(s,r,BTP_ACCEPT);
        CHECK(s->campaign.ui==BTP_MENU_BROKER && btp_actions_count(s)==BTP_BROKER_ROWS);
        for (unsigned i=0;i<model;++i) btp_game_tick(s,r,BTP_DOWN);
        CHECK(s->campaign.member+s->campaign.selected==model);save_check(s,copy,r);
        btp_game_tick(s,r,BTP_ACCEPT);CHECK(s->campaign.ui==BTP_MENU_BROKER_CONFIRM);
        save_check(s,copy,r);
        btp_game_tick(s,r,BTP_UP);unsigned credits=s->credits;btp_game_tick(s,r,BTP_ACCEPT);
        CHECK(s->campaign.ui==BTP_MENU_BROKER_RESULT && s->menu.notice==BTP_BROKER_BOUGHT);
        CHECK(s->credits==credits-d->price);
        uint8_t *m=btp_party_mech(s,0);
        CHECK(m[0]==255 && m[121]==255 && m[122]==255 && s->party.people[0][12]==8 && s->story_flags[24]);
        CHECK(s->party.mech_types[0]==d->record[0] && !memcmp(m+1,d->record+1,124));
        save_check(s,copy,r);btp_render(r,s,0,frame);
        btp_game_tick(s,r,BTP_ACCEPT);btp_game_tick(s,r,BTP_CANCEL);
        CHECK(s->campaign.ui==BTP_MENU_BROKER_HUB);btp_game_tick(s,r,BTP_CANCEL);
        CHECK(s->mode==BTP_EXPLORE);
        /* The garage's restoration makes the parked record available to the
           original allocation operation; no custom pilot shortcut is used. */
        m[0]=s->party.mech_types[0];btp_party_allocate(s,0,0,121);
        CHECK(m[121]==0 && s->party.people[0][12]==0 && s->campaign.mounted);
        BtpCombatUnit attacker={0},target={0};memcpy(attacker.record,m,125);
        memcpy(target.record,r->combat.jenner,125);attacker.x=40;attacker.y=40;target.x=44;target.y=40;
        CHECK(m[16]==specs[model][0]);
        CHECK(btp_combat_points(&attacker,0)==(int)specs[model][1]);
        CHECK(btp_combat_points(&attacker,1)==(int)(specs[model][1]+(specs[model][1]+1u)/2u));
        CHECK(btp_combat_points(&attacker,2)==(int)specs[model][2]);
        CHECK(btp_combat_weapon_count(&attacker)==specs[model][4]);
        CHECK(btp_mech_record_sprite(m,0)==specs[model][5]);
        CHECK(btp_mech_record_sprite(m,1)==btp_mech_record_sprite(m,0));
        uint8_t rng[3]={31,66,171};
        for (unsigned weapon=0;weapon<specs[model][4];++weapon) {
            unsigned hits=0;
            for (unsigned n=0;n<30;++n) {
                memcpy(attacker.record,m,125);attacker.heat=attacker.pool=0;
                memcpy(target.record,r->combat.jenner,125);
                BtpShot shot=btp_combat_shoot(&attacker,&target,&r->combat,weapon,0,0,5,rng);
                hits+=shot.damage!=0;
                if (d->ammo_cost[weapon]) CHECK(attacker.record[39+weapon]+1u==m[39+weapon]);
            }
            CHECK(hits);
        }
        attacker.heat=30;attacker.pool=0;btp_combat_cool(&attacker,-1,0,255);
        CHECK(attacker.heat==30u-specs[model][3]);
        /* The Grasshopper's 22 sinks must clamp low heat to zero. */
        attacker.heat=20;btp_combat_cool(&attacker,-1,0,255);
        CHECK(attacker.heat==(specs[model][3]<20 ? 20u-specs[model][3] : 0));
        m[17]-=2;s->credits=100000;CHECK(btp_mech_repair(s,0,0,0)==2 && m[17]==m[86]);
        unsigned slot=0,bin=0;
        for (unsigned i=51;i<86;++i) if ((m[i]&127u)>=16 && (m[i]&127u)<=32) { slot=i;break; }
        unsigned type=m[slot];m[slot]|=128;CHECK(btp_mech_repair(s,0,2,type)==1 && m[slot]==type);
        while (bin<10 && !d->ammo_cost[bin]) ++bin;
        CHECK(bin<10);m[39+bin]=0;credits=s->credits;
        CHECK(btp_mech_reload(s,r,0,bin,3)==3 && m[39+bin]==3 && s->credits==credits-3u*d->ammo_cost[bin]);
        credits=s->credits;CHECK(!btp_mech_refit(s,r,0) && s->credits==credits);
        btp_mech_screen(r,m,"Jason","None",0,0,frame);
        CHECK(btp_salvage_eligible(m,4));btp_salvage_copy(s,1,0,m,m[0]);
        CHECK(btp_party_mech(s,1)[123]==m[123] && btp_roster_definition(&r->roster,btp_party_mech(s,1))==d);
        CHECK(!memcmp(btp_party_mech(s,1)+86,m+86,31));
        services(s,copy,r,argv[1],model);
        garage(s,copy,r,model);
    }
    setup(s,r);enter_broker(s,copy,r);
    for (unsigned i=0;i<4;++i) CHECK(btp_broker_buy(s,r,i%3)==BTP_BROKER_BOUGHT);
    *before=*s;CHECK(btp_broker_buy(s,r,0)==BTP_BROKER_FULL && !memcmp(s,before,sizeof *s));
    save_check(s,copy,r);
    /* Separate six-slot namespaces, explicit-path protection, auto-detectable
       edition headers and strict content identity on load. */
    char path[256];
    for (unsigned slot=0;slot<6;++slot) {
        CHECK(btp_save_edition_slot_path("btp-roster-slot.btp",slot,r,path,sizeof path,&error));
        CHECK(strstr(path,"-updated") && btp_save_write(path,s,r,&error));
        CHECK(btp_save_is_updated(path));
        *before=*copy;CHECK(!btp_save_load(path,copy,original.resources,&error) && !memcmp(copy,before,sizeof *copy));
        CHECK(btp_save_load(path,copy,r,&error));CHECK(!remove(path));
    }
    CHECK(btp_save_write("btp-roster-updated.btp",s,r,&error));
    uint8_t original_bytes[BTP_ORIGINAL_BYTES];s->original.valid=1;s->original.bytes[0]=12;
    CHECK(!btp_original_encode(s,original_bytes,&error));s->original=(BtpOriginalState){0};
    setup(copy,original.resources);
    CHECK(!btp_save_write("btp-roster-updated.btp",copy,original.resources,&error));
    CHECK(btp_save_write("btp-roster-original.btp",copy,original.resources,&error));
    CHECK(!btp_save_write("btp-roster-original.btp",s,r,&error));
    CHECK(btp_save_load("btp-roster-original.btp",copy,r,&error));
    uint32_t signature=r->roster.fingerprint;r->roster.fingerprint^=1;
    CHECK(!btp_save_load("btp-roster-updated.btp",copy,r,&error));r->roster.fingerprint=signature;
    CHECK(!remove("btp-roster-original.btp") && !remove("btp-roster-updated.btp"));
    /* Generated encounters never add mech spawns inside Starport, and the
       Original profile consumes no additional random numbers. */
    setup(s,r);uint8_t rng[3];memcpy(rng,s->npc.rng,3);
    CHECK(!btp_roster_enemy(s,r) && !memcmp(rng,s->npc.rng,3));
    s->map_id=0;CHECK(!btp_roster_enemy(s,original.resources) && !memcmp(rng,s->npc.rng,3));
    for (unsigned tier=0;tier<2;++tier) {
        /* Catapult ownership excludes the new assault models; Atlas ownership
           makes the entire catalogue eligible, including Highlander/Stalker. */
        unsigned model=tier ? 14 : 2,limit=tier ? 115 : 80;
        s->campaign.owned=1;s->party.mech_types[0]=r->roster.mechs[model].record[0];
        memcpy(s->campaign.mech,r->roster.mechs[model].record,125);
        uint32_t seen=0,eligible=0;
        for (unsigned i=0;i<r->roster.count;++i) if (r->roster.mechs[i].record[16]<=limit)
            eligible|=UINT32_C(1)<<(r->roster.mechs[i].record[123]-BTP_ROSTER_CODE);
        for (unsigned i=0;i<2048;++i) {
            const uint8_t *m=btp_roster_enemy(s,r);if (m) seen|=1u<<(m[123]-BTP_ROSTER_CODE);
        }
        CHECK(seen==eligible);
    }
    free(frame);free(before);free(copy);free(s);btp_content_close(&original);btp_content_close(&content);
    printf("PASS: %u updated roster, lifecycle, broker and edition-save checks\n",checks);return 0;
}
