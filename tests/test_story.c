#include "core/story.h"
#include "core/party.h"
#include "data/save.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x);exit(1); } } while (0)
static void input(BtpState *s,const BtpResources *r,BtpAction action)
{
    uint8_t a[BTP_STATE_BYTES],b[BTP_STATE_BYTES];BtpState copy;
    btp_state_encode(s,a);CHECK(btp_state_decode(a,sizeof a,btp_active_map(r,s),btp_state_bld(r,s),&copy));
    btp_game_tick(s,r,action);btp_game_tick(&copy,r,action);
    btp_state_encode(s,a);btp_state_encode(&copy,b);CHECK(!memcmp(a,b,sizeof a));
}
int main(int argc,char **argv)
{
    if (argc!=2) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError e;CHECK(r && btp_resources_load(argv[1],r,&e));
    CHECK(btp_combat_data_load("work/combat-data.bin",&r->combat,&e));
    CHECK(btp_dialogue_load("work/talk-data.bin",&r->dialogue,&e));
    FILE *f=fopen("tests/fixtures/story-primary.txt","r");CHECK(f);char line[256];unsigned cases=0;
    BtpBld hospital=r->buildings[9];
    while (fgets(line,sizeof line,f)) if (line[0]=='H') {
        unsigned action,cash,trained,after,skill,bits,flag14,flag15,injured,kit,advanced;
        CHECK(sscanf(line+1,"%u %u %u %u %u %u %u %u %u %u %u",&action,&cash,&trained,&after,&skill,&bits,&flag14,&flag15,&injured,&kit,&advanced)==11);
        BtpState s;btp_start(&s);s.story_flags[4]=1;s.map_id=2;s.entry_slot=4;s.campaign.building=9;s.npc=(BtpNpcState){.rng={31,66,171}};
        s.mode=BTP_BUILDING;s.credits=cash;btp_party_init(&s);
        static const uint8_t person[]={0,8,9,7,0,0,0,0,1,0,1,0,8,0,0,75,0};
        memcpy(s.party.people[0],person,17);s.party.people[0][16]=(uint8_t)trained;
        s.script=(BtpScriptState){.status=BTP_SCRIPT_NATIVE,.native_action=(uint8_t)action,.pc=2};
        r->buildings[9]=(BtpBld){.length=3,.bytes={0xf5,(uint8_t)action,0xff}};
        btp_game_tick(&s,r,BTP_IDLE);
        CHECK(s.mode==BTP_EXPLORE && s.credits==after && s.party.people[0][10]==skill && s.party.people[0][16]==bits);
        CHECK(s.story_flags[14]==flag14 && s.story_flags[15]==flag15 && s.story_flags[25]==injured && s.party.medical_kit==kit && s.party.advanced_kit==advanced);
        input(&s,r,BTP_IDLE);++cases;
    }
    fclose(f);CHECK(cases==40);r->buildings[9]=hospital;
    free(r);printf("PASS: %u later-story checks, original hospital effects and saved continuation\n",checks);return 0;
}
