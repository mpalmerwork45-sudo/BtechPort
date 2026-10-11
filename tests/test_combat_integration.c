#include "core/combat.h"
#include "core/npc.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x);exit(1); } } while (0)
static void step(BtpState *s,const BtpResources *r,BtpAction action)
{
    uint8_t before[BTP_STATE_BYTES],after[BTP_STATE_BYTES];BtpState copy;
    btp_state_encode(s,before);
    CHECK(btp_state_decode(before,sizeof before,&r->map,btp_building_bld(r,s->entry_slot),&copy));
    btp_game_tick(s,r,action);btp_game_tick(&copy,r,action);
    btp_state_encode(s,before);btp_state_encode(&copy,after);CHECK(!memcmp(before,after,sizeof before));
}
static void command(BtpState *s,const BtpResources *r,unsigned wanted)
{
    CHECK(s->combat.phase==BTP_COMBAT_MENU);
    while (s->combat.selected!=wanted) step(s,r,BTP_DOWN);
    step(s,r,BTP_ACCEPT);
}
static void decline(const BtpState *menu,const BtpResources *r,unsigned loan)
{
    BtpState s=*menu;
    while (s.script.selected!=loan) step(&s,r,BTP_DOWN);
    step(&s,r,BTP_ACCEPT);
    for (unsigned i=0;s.cutscene.active && i<128;++i) step(&s,r,BTP_IDLE);
    CHECK(s.combat.phase==BTP_COMBAT_CONTROL && !s.cutscene.active);
    CHECK(!memcmp(s.combat.unit[0].record,r->combat.loans[loan],125));
    step(&s,r,BTP_UP);step(&s,r,BTP_ACCEPT);CHECK(s.combat.phase==BTP_COMBAT_NOTICE);
    step(&s,r,BTP_ACCEPT);step(&s,r,BTP_DOWN);step(&s,r,BTP_ACCEPT);
    step(&s,r,BTP_ACCEPT);step(&s,r,BTP_ACCEPT);CHECK(s.combat.phase==BTP_COMBAT_MENU);
    command(&s,r,6);step(&s,r,BTP_DOWN);CHECK(s.combat.scan_unit==1);step(&s,r,BTP_CANCEL);
    command(&s,r,0);step(&s,r,BTP_RIGHT);step(&s,r,BTP_CANCEL);CHECK(!s.combat.goal_active);
    command(&s,r,4);CHECK(s.combat.notice==1);step(&s,r,BTP_CANCEL);
    command(&s,r,3);step(&s,r,BTP_ACCEPT);step(&s,r,BTP_CANCEL);CHECK(s.combat.orders[0]==255);
    step(&s,r,BTP_CANCEL);command(&s,r,8);CHECK(s.combat.fled && !s.combat.phase);
    for (unsigned i=0;i<4;++i) step(&s,r,BTP_LEFT);
    step(&s,r,BTP_IDLE);CHECK(s.mode==BTP_BUILDING && s.story_flags[0]==2 && !s.story_flags[1] && s.allowance_cap==250);
    step(&s,r,BTP_ACCEPT);CHECK(s.mode==BTP_EXPLORE && !s.mission.phase && !s.combat.fled);
}
int main(int argc,char **argv)
{
    if (argc!=5) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError error;CHECK(r);
    CHECK(btp_resources_load(argv[1],r,&error));CHECK(btp_dialogue_load(argv[2],&r->dialogue,&error));
    CHECK(btp_combat_data_load(argv[3],&r->combat,&error));
    BtpState s,menu={0};btp_start(&s);btp_npc_init(&s,&r->map);
    FILE *file=fopen(argv[4],"r");CHECK(file);char line[40];unsigned ticks=0,combat_ticks=0;
    while (fgets(line,sizeof line,file)) {
        line[strcspn(line,"\r\n")]=0;BtpAction action;CHECK(btp_action_parse(line,&action));
        if (s.story_flags[0]==2 && s.script.status==BTP_SCRIPT_MENU && s.script.menu_id==7) menu=s;
        step(&s,r,action);++ticks;combat_ticks+=s.combat.phase!=0;
        if (s.combat.phase==BTP_COMBAT_ROUND && s.combat.step==1) {
            uint8_t bad[BTP_STATE_BYTES];BtpState untouched=s;
            btp_state_encode(&s,bad);bad[896]=1;
            CHECK(!btp_state_decode(bad,sizeof bad,&r->map,&r->training,&untouched));CHECK(!memcmp(&untouched,&s,sizeof s));
            btp_state_encode(&s,bad);bad[512+125+2]=8;
            CHECK(!btp_state_decode(bad,sizeof bad,&r->map,&r->training,&untouched));CHECK(!memcmp(&untouched,&s,sizeof s));
        }
    }
    fclose(file);CHECK(s.mode==BTP_EXPLORE && s.story_flags[0]==3 && s.story_flags[1]==1 && s.allowance_cap==500);
    CHECK(menu.story_flags[0]==2 && combat_ticks>100);
    for (unsigned loan=0;loan<3;++loan) decline(&menu,r,loan);
    btp_start(&s);uint8_t old[BTP_STATE_BYTES];BtpState migrated;
    btp_state_encode(&s,old);memcpy(old,"BTPC",4);old[4]=12;
    CHECK(btp_state_decode(old,512,&r->map,&r->training,&migrated));CHECK(!memcmp(&s,&migrated,sizeof s));
    free(r);printf("PASS: %u combat integration assertions; %u input continuations, three loans and flee results\n",checks,ticks);
    return 0;
}
