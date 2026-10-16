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
static void setup(BtpState *s,const BtpResources *r)
{
    btp_start(s);s->story_flags[4]=1;s->story_flags[36]=127;s->map_id=2;s->x_half=105;s->y_half=94;
    s->campaign.world_x=1385;s->campaign.world_y=1118;s->credits=200000;s->mech_skills[1]=1;
    btp_npc_enter(s,&r->local[1]);btp_party_init(s);
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
static void garage(BtpState *s,BtpState *copy,const BtpResources *r,unsigned model)
{
    setup(s,r);CHECK(btp_broker_buy(s,r,model)==BTP_BROKER_BOUGHT);
    const BtpMap *map=&r->local[1];unsigned entry=0;
    while (entry<16 && map->room_map[entry]!=8) ++entry;
    CHECK(entry<16);s->x_half=map->entrance_x[entry]&127u;s->y_half=(uint16_t)((map->entrance_y[entry]&127u)+1u);
    s->campaign.world_x=(uint16_t)((map->entrance_x[0]>>8)*128u+s->x_half);
    s->campaign.world_y=(uint16_t)((map->entrance_y[0]>>12)*128u+s->y_half);
    s->party.x[0]=s->campaign.world_x;s->party.y[0]=s->campaign.world_y;
    btp_game_tick(s,r,BTP_UP);CHECK(s->mode==BTP_ENTRY);btp_game_tick(s,r,BTP_ACCEPT);
    for (unsigned i=0;i<32 && s->campaign.ui!=BTP_MENU_ALLOCATE;++i) {
        CHECK(s->mode!=BTP_SCRIPT_FAULT);save_check(s,copy,r);
        if (s->script.status==BTP_SCRIPT_CONFIRM && s->script.confirm_selected) btp_game_tick(s,r,BTP_LEFT);
        btp_game_tick(s,r,BTP_ACCEPT);
    }
    CHECK(s->campaign.ui==BTP_MENU_ALLOCATE);save_check(s,copy,r);
    btp_game_tick(s,r,BTP_ACCEPT);CHECK(s->campaign.ui==BTP_MENU_CREW);
    /* An empty cockpit takes the qualified pilot immediately; the seat
       confirmation is only needed when displacing an existing pilot. */
    btp_game_tick(s,r,BTP_ACCEPT);CHECK(s->campaign.ui==BTP_MENU_ALLOCATE);
    CHECK(s->campaign.mech[121]==0 && s->party.people[0][12]==0);
    btp_game_tick(s,r,BTP_DOWN);btp_game_tick(s,r,BTP_ACCEPT);
    for (unsigned i=0;i<32 && s->mode!=BTP_EXPLORE;++i) btp_game_tick(s,r,BTP_ACCEPT);
    CHECK(s->mode==BTP_EXPLORE && s->campaign.mounted && !s->story_flags[24]);
    CHECK(s->campaign.mech[123]==r->roster.mechs[model].record[123]);save_check(s,copy,r);
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
    CHECK(r->roster.count==3 && !memcmp(&r->combat,&original.resources->combat,sizeof r->combat));
    BtpState *s=calloc(1,sizeof *s),*copy=calloc(1,sizeof *copy),*before=calloc(1,sizeof *before);
    uint32_t *frame=malloc(BTP_PIXELS*sizeof *frame);
    CHECK(s && copy && before && frame);
    /* Optional valid Starport checkpoint for bounded SDL purchase checks. */
    if (argc==7) { setup(s,r);CHECK(btp_save_write(argv[6],s,r,&error)); }
    /* Use the real menu and purchase confirmation, including held save/load,
       then exercise the shared gameplay operations on each delivered model. */
    for (unsigned model=0;model<3;++model) {
        const BtpRosterMech *d=&r->roster.mechs[model];setup(s,r);
        s->credits=d->price-1;*before=*s;
        CHECK(btp_broker_buy(s,r,model)==BTP_BROKER_NO_FUNDS && !memcmp(s,before,sizeof *s));
        s->credits=200000;
        btp_game_tick(s,r,BTP_OPEN_MENU);CHECK(s->campaign.ui==BTP_MENU_UPDATED_ROOT);
        btp_game_tick(s,r,BTP_UP);btp_game_tick(s,r,BTP_ACCEPT);
        CHECK(s->campaign.ui==BTP_MENU_BROKER && btp_actions_count(s)==4);
        for (unsigned i=0;i<model;++i) btp_game_tick(s,r,BTP_DOWN);
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
        CHECK(s->mode==BTP_EXPLORE);
        /* The garage's restoration makes the parked record available to the
           original allocation operation; no custom pilot shortcut is used. */
        m[0]=s->party.mech_types[0];btp_party_allocate(s,0,0,121);
        CHECK(m[121]==0 && s->party.people[0][12]==0 && s->campaign.mounted);
        BtpCombatUnit attacker={0},target={0};memcpy(attacker.record,m,125);
        memcpy(target.record,r->combat.jenner,125);attacker.x=40;attacker.y=40;target.x=44;target.y=40;
        CHECK(btp_combat_points(&attacker,0)==4 && btp_combat_points(&attacker,1)==6);
        CHECK(btp_combat_points(&attacker,2)==(model==1 ? 0 : 4));
        CHECK(btp_combat_weapon_count(&attacker)==(model==0 ? 2u : model==1 ? 4u : 6u));
        CHECK(btp_mech_record_sprite(m,0)==(model==2 ? 0u : 146u));
        CHECK(btp_mech_record_sprite(m,1)==btp_mech_record_sprite(m,0));
        unsigned hits=0;uint8_t rng[3]={31,66,171};
        for (unsigned n=0;n<30;++n) {
            memcpy(target.record,r->combat.jenner,125);
            BtpShot shot=btp_combat_shoot(&attacker,&target,&r->combat,0,0,0,5,rng);
            hits+=shot.damage!=0;
        }
        CHECK(hits);attacker.heat=20;attacker.pool=0;btp_combat_cool(&attacker,-1,0,255);
        CHECK(attacker.heat==(model==2 ? 5 : 7));
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
    setup(s,r);
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
    s->campaign.owned=1;s->party.mech_types[0]='C';memcpy(s->campaign.mech,r->roster.mechs[2].record,125);
    unsigned seen=0;
    for (unsigned i=0;i<512;++i) {
        const uint8_t *m=btp_roster_enemy(s,r);if (m) seen|=1u<<(m[123]-BTP_ROSTER_CODE);
    }
    CHECK(seen==7);
    free(frame);free(before);free(copy);free(s);btp_content_close(&original);btp_content_close(&content);
    printf("PASS: %u updated roster, lifecycle, broker and edition-save checks\n",checks);return 0;
}
