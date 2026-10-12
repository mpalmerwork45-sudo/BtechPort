#include "core/story.h"
#include "core/party.h"
#include "core/animation.h"
#include "core/combat.h"
#include "core/npc.h"
#include "core/bank.h"
#include "core/training.h"
#include "core/service.h"
#include "data/save.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x);exit(1); } } while (0)
static void input(BtpState *s,const BtpResources *r,BtpAction action)
{
    uint8_t before[BTP_STATE_BYTES],after[BTP_STATE_BYTES];BtpState copy;
    btp_state_encode(s,before);
    if (!btp_state_decode(before,sizeof before,btp_active_map(r,s),btp_state_bld(r,s),&copy)) {
        fprintf(stderr,"Late building save failed: tick %u mode %u script %u PC %u building %u service %u animation %u/%u audio %u\n",
            s->tick,s->mode,s->script.status,s->script.pc,s->campaign.building,s->service.phase,s->cutscene.active,s->cutscene.kind,s->audio.sound_count);
        fprintf(stderr,"Checks combat=%d NPC=%d bank=%d training=%d service=%d coordinate=%u,%u map=%u friends=%u count=%u\n",
            btp_combat_valid(s),btp_npc_valid(s,btp_active_map(r,s)),btp_bank_valid(s),btp_training_valid(s),btp_service_valid(s),
            s->x_half,s->y_half,s->map_id,s->combat.friends,s->combat.count);
        for (unsigned i=0;i<s->combat.count;++i) fprintf(stderr,"unit %u id %u kind %u infantry %u at %u,%u health %u constitution %u weapons %u\n",
            i,btp_combat_id(&s->combat,i),s->combat.unit[i].record[0],s->combat.unit[i].infantry,s->combat.unit[i].x,s->combat.unit[i].y,
            s->combat.unit[i].record[15],s->combat.unit[i].record[1],btp_combat_weapon_count(&s->combat.unit[i]));
        CHECK(0);
    }
    btp_game_tick(s,r,action);btp_game_tick(&copy,r,action);
    btp_state_encode(s,before);btp_state_encode(&copy,after);CHECK(!memcmp(before,after,sizeof before));
}
static void prerequisite(BtpState *s,unsigned people,unsigned seed)
{
    btp_start(s);s->map_id=0;s->story_flags[4]=1;s->weapon=9;s->mech_skills[1]=1;
    s->npc=(BtpNpcState){.rng={(uint8_t)seed,(uint8_t)(seed>>8),(uint8_t)(seed>>16)}};btp_party_init(s);
    for (unsigned i=0;i<8;++i) {
        const uint8_t p[]={0,8,9,7,0,0,0,0,1,0,0,9,8,0,0,80,0};
        memcpy(s->party.people[i],p,17);s->party.people[i][0]=(uint8_t)(i<people ? i : 255);
    }
}
int main(int argc,char **argv)
{
    if (argc!=2) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError e;CHECK(r && btp_resources_load(argv[1],r,&e));
    CHECK(btp_combat_data_load("work/combat-data.bin",&r->combat,&e));
    CHECK(btp_dialogue_load("work/talk-data.bin",&r->dialogue,&e));
    CHECK(btp_world_data_load("work/world-data.bin",&r->world,&e));
    BtpBld originals[3]={r->buildings[14],r->buildings[15],r->buildings[16]};
    FILE *f=fopen("tests/fixtures/late-story-primary.txt","r");CHECK(f);char line[512];unsigned cases=0;
    while (fgets(line,sizeof line,f)) {
        BtpState s;unsigned n,seed,yes,rng;int used;
        if (line[0]=='L') {
            CHECK(sscanf(line+1,"%u %u %u %u%n",&n,&seed,&yes,&rng,&used)==4);prerequisite(&s,n,seed);
            r->buildings[15]=(BtpBld){.length=3,.bytes={0xf5,41,0xff}};btp_game_building(&s,r,15);btp_game_tick(&s,r,BTP_IDLE);
            if (n==1) { if (!yes) input(&s,r,BTP_RIGHT);input(&s,r,BTP_ACCEPT); }
            else for (unsigned i=0;i<n;++i) {
                while (s.service.selected!=i) input(&s,r,BTP_DOWN);
                input(&s,r,BTP_ACCEPT);while (s.service.selected!=n) input(&s,r,BTP_DOWN);input(&s,r,BTP_ACCEPT);
            }
            char *at=line+1+used;
            for (unsigned i=0;i<n;++i) {
                unsigned weapon,health;CHECK(sscanf(at,"%u %u%n",&weapon,&health,&used)==2);at+=used;
                CHECK(s.party.people[i][11]==weapon && s.party.people[i][15]==health);
            }
            CHECK((unsigned)s.npc.rng[0]+((unsigned)s.npc.rng[1]<<8)+((unsigned)s.npc.rng[2]<<16)==rng);
        } else if (line[0]=='M') {
            unsigned health,after;CHECK(sscanf(line+1,"%u %u",&health,&after)==2);prerequisite(&s,1,42);
            s.party.people[0][15]=(uint8_t)health;r->buildings[14]=(BtpBld){.length=3,.bytes={0xf5,47,0xff}};
            btp_game_building(&s,r,14);btp_game_tick(&s,r,BTP_IDLE);CHECK(s.party.people[0][15]==after);
        } else if (line[0]=='C') {
            unsigned x,y,after;CHECK(sscanf(line+1,"%u %u %u%n",&x,&y,&after,&used)==3);prerequisite(&s,1,42);
            s.x_half=s.campaign.world_x=(uint16_t)((x>>8)*128u+(x&127u));
            s.y_half=s.campaign.world_y=(uint16_t)((y>>12)*128u+(y&127u));
            r->buildings[16]=(BtpBld){.length=3,.bytes={0xf5,42,0xff}};
            btp_game_building(&s,r,16);btp_game_tick(&s,r,BTP_IDLE);
            CHECK(s.campaign.world_y==(after>>12)*128u+(after&127u));char *at=line+1+used;
            for (unsigned i=0;i<8;++i) {
                unsigned room,counter;CHECK(sscanf(at,"%u %u%n",&room,&counter,&used)==2);at+=used;
                CHECK(s.npc_pairs[i][0]==room && s.npc_pairs[i][1]==counter);
            }
        } else CHECK(0);
        input(&s,r,BTP_IDLE);++cases;
    }
    fclose(f);CHECK(cases==46);
    for (unsigned i=0;i<3;++i) r->buildings[14+i]=originals[i];
    const char *routes[]={"mayor-newspaper","mayor-holodisk","mayor-chow","cinema","inventor","inventor-qualified","laser-guns"};
    for (unsigned route=0;route<7;++route) {
        BtpState s;CHECK(btp_save_load(route==5 ? "Original DOS/GAME5" : "Original DOS/GAME3",&s,r,&e));
        char path[180];snprintf(path,sizeof path,"tests/fixtures/ordinary-%s.actions",routes[route]);f=fopen(path,"r");CHECK(f);
        unsigned ticks=0,films=0,house_menu=0,laser_menu=0;
        while (fgets(line,sizeof line,f)) {
            line[strcspn(line,"\r\n")]=0;BtpAction action;CHECK(btp_action_parse(line,&action));
            input(&s,r,action);++ticks;
            if (s.campaign.building==16 && s.cutscene.active) films|=1u<<s.cutscene.kind;
            house_menu|=s.mode==BTP_BUILDING && s.script.status==BTP_SCRIPT_MENU && s.script.menu_id==32;
            laser_menu|=s.service.action==41 && s.service.phase==10;
            CHECK(s.audio.sound_count<=1); /* E4 calls finish before the following film/effect. */
        }
        fclose(f);CHECK(ticks>200 && s.mode==BTP_EXPLORE);
        if (route<3) CHECK(house_menu);
        if (route==2) CHECK(s.party.people[0][15]==76);
        if (route==3) CHECK(films==927); /* THEATER.BLD uses O0..O4 and O7..O9. */
        if (route==4) CHECK(!s.story_flags[53] && !s.story_flags[54]);
        if (route==5) CHECK(s.story_flags[53] && s.story_flags[54]);
        if (route==6) { CHECK(laser_menu && s.party.people[0][11]==13);for (unsigned i=1;i<4;++i) CHECK(s.party.people[i][11]>=12); }
    }
    free(r);printf("PASS: %u late-building checks, 46 primary cases and seven saved ordinary routes\n",checks);return 0;
}
