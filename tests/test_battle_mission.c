#include "core/battle_mission.h"
#include "core/combat.h"
#include "core/campaign.h"
#include "core/audio.h"
#include "data/content.h"
#include "data/project.h"
#include "data/save.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static BtpError error;
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"%s:%d: %s (%s)\n",__FILE__,__LINE__,#x,error.text);exit(1); } } while (0)
static void checkpoint(BtpState *s,const BtpResources *r)
{
    BtpState *copy=malloc(sizeof *copy);uint8_t before[BTP_STATE_BYTES],after[BTP_STATE_BYTES];CHECK(copy);
    CHECK(btp_combat_valid(s));CHECK(btp_events_valid(s,r));
    CHECK(btp_save_write("battle-mission-roundtrip.btp",s,r,&error));
    CHECK(btp_save_load("battle-mission-roundtrip.btp",copy,r,&error));
    btp_state_encode(s,before);btp_state_encode(copy,after);
    CHECK(before[4]==51 && !memcmp(before,after,sizeof before));*s=*copy;free(copy);
    CHECK(remove("battle-mission-roundtrip.btp")==0);
}
static void input(BtpState *s,const BtpResources *r,BtpAction action)
{ btp_game_tick(s,r,action);CHECK(s->event.phase!=BTP_EVENT_FAULT);checkpoint(s,r); }
int main(int argc,char **argv)
{
    CHECK(argc==2);BtpContent content={0};CHECK(btp_content_load_project(&content,argv[1],NULL,&error));
    BtpResources *r=content.resources;BtpAdventure *a=&r->project->adventure;
    BtpState *s=calloc(1,sizeof *s),*old=malloc(sizeof *old);CHECK(s && old);
    a->combat_missions=a->mission_state=1;a->region_count=0;a->variable_count=2;
    a->variables[0]=(BtpMissionVariable){.maximum=100};a->variables[1]=a->variables[0];
    a->objective_count=0;a->battle_count=1;a->group_count=1;a->hook_count=4;
    a->battles[0]=(BtpSceneBattle){.map=0,.x=12,.y=24,.count=1,.scripted=1,
        .enemies={{.x=42,.y=24,.definition=0}}};
    a->groups[0]=(BtpCombatGroup){.battle=0,.count=2,.reserve=1,
        .actors={{{.x=38,.y=28,.definition=0}},{{.x=38,.y=28,.definition=0}}}};
    a->hooks[0]=(BtpCombatHook){.battle=0,.when=BTP_HOOK_START,.group=BTP_COMBAT_GROUPS,.event=6};
    a->hooks[1]=(BtpCombatHook){.battle=0,.when=BTP_HOOK_ROUND_START,.first=2,.group=BTP_COMBAT_GROUPS,.event=7};
    a->hooks[2]=(BtpCombatHook){.battle=0,.when=BTP_HOOK_ROUND_END,.first=1,.every=1,.repeat=1,.group=BTP_COMBAT_GROUPS,.event=8};
    a->hooks[3]=(BtpCombatHook){.battle=0,.when=BTP_HOOK_DESTROYED,.repeat=1,.group=0,.event=9};
    a->nodes[0]=(BtpEventNode){.op=BTP_EVENT_BATTLE,.argument=0,.next={1,2,3,4}};
    a->nodes[1]=(BtpEventNode){.op=BTP_EVENT_SAY,.text="Victory.",.next={5}};
    a->nodes[2]=(BtpEventNode){.op=BTP_EVENT_SAY,.text="Defeat.",.next={5}};
    a->nodes[3]=(BtpEventNode){.op=BTP_EVENT_SAY,.text="Retreated.",.next={5}};
    a->nodes[4]=(BtpEventNode){.op=BTP_EVENT_SAY,.text="Deployment failed.",.next={5}};
    a->nodes[5]=(BtpEventNode){.op=BTP_EVENT_END};
    a->nodes[6]=(BtpEventNode){.op=BTP_EVENT_SAY,.text="Hold the relay for three rounds.",.next={5}};
    a->nodes[7]=(BtpEventNode){.op=BTP_EVENT_REINFORCE,.argument=0,.value=2,.next={5,4}};
    a->nodes[8]=(BtpEventNode){.op=BTP_EVENT_VARIABLE,.argument=0,.x=1,.value=1,.next={10,4}};
    a->nodes[9]=(BtpEventNode){.op=BTP_EVENT_VARIABLE,.argument=1,.x=1,.value=1,.next={5,4}};
    a->nodes[10]=(BtpEventNode){.op=BTP_EVENT_CHECK,.count=1,.conditions={{.kind=BTP_CONDITION_COMBAT_ROUND,.compare=5,.value=3}},.next={11,5}};
    a->nodes[11]=(BtpEventNode){.op=BTP_EVENT_BATTLE_END,.value=0,.next={5,4}};
    a->node_count=12;a->start_event=0;a->start_map=0;a->start_x=12;a->start_y=24;
    memset(a->maps[0].rules.tiles,0,sizeof a->maps[0].rules.tiles);
    a->maps[0].entrance_count=0;
    btp_start(s);s->project=1;CHECK(btp_set_combat_profile(s,r,1));btp_events_start(s,r);
    CHECK(s->event.phase==BTP_EVENT_FIGHTING && s->battle_mission.active);checkpoint(s,r);
    input(s,r,BTP_IDLE);CHECK(s->event.node==6 && s->battle_mission.in_hook);
    input(s,r,BTP_ACCEPT);CHECK(s->event.phase==BTP_EVENT_FIGHTING && !s->battle_mission.in_hook);
    /* Failure cannot consume or partially place a two-unit wave. Radius two
       finds distinct legal anchors in deterministic distance/row order. */
    *old=*s;CHECK(!btp_battle_reinforce(s,r,0,0) && !memcmp(s,old,sizeof *s));
    CHECK(btp_battle_reinforce(s,r,0,2));checkpoint(s,r);
    CHECK(btp_battle_group_value(s,a,0,BTP_CONDITION_GROUP_ALIVE)==2);
    CHECK(!btp_battle_reinforce(s,r,0,2));
    /* A casualty is observable only after the presentation queue drains.
       Check the real serialized audio queue, not a second timing model. */
    btp_campaign_destroy(s,btp_combat_target(&s->combat,13));btp_audio_effect(s,8);
    CHECK(s->audio.sound_count);checkpoint(s,r);
    btp_events_tick(s,r,BTP_IDLE);
    CHECK(btp_battle_group_value(s,a,0,BTP_CONDITION_GROUP_ALIVE)==2 && !s->event.variables[1]);
    for (unsigned tick=0;tick<10000 && !s->event.variables[1];++tick) btp_game_tick(s,r,BTP_IDLE);
    CHECK(s->event.variables[1]==1 && btp_battle_group_value(s,a,0,BTP_CONDITION_GROUP_DESTROYED)==1);
    checkpoint(s,r);*s=*old;
    /* Ordinary settings/menu input starts rounds. Hold all actors stationary
       for this lifecycle fixture; gameplay scenarios exercise real weapons. */
    for (unsigned i=0;i<s->combat.count;++i) {
        memset(s->combat.unit[i].record+51,0,35);s->combat.unit[i].heat=30;
    }
    input(s,r,BTP_ACCEPT); /* manual control */
    input(s,r,BTP_ACCEPT); /* message selection */
    input(s,r,BTP_ACCEPT); /* graphics */
    CHECK(s->combat.phase==BTP_COMBAT_MENU);
    for (unsigned ticks=0;ticks<500 && s->battle_mission.active;++ticks) {
        BtpAction action=s->mode==BTP_EVENT ? BTP_ACCEPT : s->combat.phase==BTP_COMBAT_MENU ? BTP_ACCEPT : BTP_IDLE;
        input(s,r,action);
        /* Destroy both reserve units together, after they have really been
           deployed. Hooks must keep both notifications through reload. */
        if (s->battle_mission.deployed && !s->battle_mission.seen_dead) {
            for (unsigned id=13;id<15;++id) btp_campaign_destroy(s,btp_combat_target(&s->combat,id));
        }
    }
    CHECK(!s->battle_mission.active && s->event.node==1);
    CHECK(s->event.variables[0]==3 && s->event.variables[1]==2);
    CHECK(btp_battle_group_value(s,a,0,BTP_CONDITION_GROUP_DESTROYED)==2);
    input(s,r,BTP_ACCEPT);CHECK(s->mode==BTP_EXPLORE);
    uint8_t bytes[BTP_BATTLE_MISSION_BYTES];btp_battle_mission_encode(s,bytes);bytes[511]=1;
    CHECK(!btp_battle_mission_decode(old,bytes));
    *old=*s;s->battle_mission.pending[31]=1;CHECK(!btp_events_valid(s,r));*s=*old;
    free(old);free(s);btp_content_close(&content);puts("combat mission lifecycle, deployment and saved hooks passed");return 0;
}
