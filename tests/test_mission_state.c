#include "core/mission_state.h"
#include "core/party.h"
#include "core/lua_events.h"
#include "data/content.h"
#include "data/project.h"
#include "data/save.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"%s:%d: %s (%s)\n",__FILE__,__LINE__,#x,error.text);exit(1); } } while (0)
static BtpError error;
static void checkpoint(BtpState *s,const BtpResources *r)
{
    BtpState *copy=malloc(sizeof *copy);uint8_t before[BTP_STATE_BYTES],after[BTP_STATE_BYTES];CHECK(copy);
    CHECK(btp_events_valid(s,r));CHECK(btp_save_write("mission-roundtrip.btp",s,r,&error));
    CHECK(btp_save_load("mission-roundtrip.btp",copy,r,&error));
    btp_state_encode(s,before);btp_state_encode(copy,after);
    CHECK(before[4]==50 && !memcmp(before,after,sizeof before));*s=*copy;free(copy);
}
static void input(BtpState *s,const BtpResources *r,BtpAction action)
{ btp_game_tick(s,r,action);CHECK(s->event.phase!=BTP_EVENT_FAULT);checkpoint(s,r); }
int main(int argc,char **argv)
{
    CHECK(argc==2);BtpContent content={0};CHECK(btp_content_load_project(&content,argv[1],NULL,&error));
    BtpResources *r=content.resources;BtpAdventure *a=&r->project->adventure;
    BtpState *s=calloc(1,sizeof *s),*old=malloc(sizeof *old);CHECK(s && old);
    /* Independent fixture: isolate region ordering and save boundaries from
       the legacy story. The playable example is tested separately by inputs. */
    a->mission_state=1;a->variable_count=3;a->region_count=2;a->objective_count=1;
    for (unsigned i=0;i<3;++i) a->variables[i]=(BtpMissionVariable){.maximum=100};
    a->variables[0].maximum=2;
    strcpy(a->variables[0].id,"test:count");
    a->objectives[0]=(BtpObjective){.explicit_state=1,.initial=BTP_OBJECTIVE_ACTIVE};
    strcpy(a->objectives[0].id,"test:objective");
    a->regions[0]=(BtpMissionRegion){.map=0,.x=7,.y=12,.width=1,.height=3,.enter=1,.leave=5,.repeat=0};
    a->regions[1]=a->regions[0];a->regions[1].enter=2;a->regions[1].leave=BTP_EVENT_NODES;a->regions[1].repeat=1;
    strcpy(a->regions[0].id,"test:region");
    a->nodes[0]=(BtpEventNode){.op=BTP_EVENT_END};
    a->nodes[1]=(BtpEventNode){.op=BTP_EVENT_VARIABLE,.argument=0,.value=1,.x=1,.y=1,.next={3,6}};
    a->nodes[2]=(BtpEventNode){.op=BTP_EVENT_VARIABLE,.argument=1,.value=1,.x=1,.next={4,6}};
    a->nodes[3]=(BtpEventNode){.op=BTP_EVENT_SAY,.text="First region."};
    a->nodes[4]=(BtpEventNode){.op=BTP_EVENT_SAY,.text="Second region."};
    a->nodes[5]=(BtpEventNode){.op=BTP_EVENT_VARIABLE,.argument=2,.value=1,.x=1,.next={7,6}};
    a->nodes[6]=(BtpEventNode){.op=BTP_EVENT_SAY,.text="Failure."};
    a->nodes[7]=(BtpEventNode){.op=BTP_EVENT_SAY,.text="Left first region."};
    a->node_count=8;a->start_event=0;a->start_map=0;a->start_x=12;a->start_y=24;
    for (unsigned i=0;i<a->map_count;++i) a->maps[i].entrance_count=0;
    memset(a->maps[0].rules.tiles,0,sizeof a->maps[0].rules.tiles);
    btp_start(s);s->project=1;CHECK(btp_set_combat_profile(s,r,1));btp_events_start(s,r);
    CHECK(s->mode==BTP_EXPLORE);s->menu.steps=4;
    input(s,r,BTP_RIGHT);
    CHECK(s->x_half==14 && s->event.node==3 && s->event.variables[0]==1);
    CHECK(s->event.enter_pending==2 && !s->event.variables[1]); /* Pending overlap survived reload. */
    input(s,r,BTP_ACCEPT);CHECK(s->event.node==4 && s->event.variables[1]==1);
    input(s,r,BTP_ACCEPT);CHECK(s->mode==BTP_EXPLORE);
    input(s,r,BTP_RIGHT);CHECK(s->x_half==16 && s->event.node==7 && s->event.variables[2]==1);
    input(s,r,BTP_ACCEPT);input(s,r,BTP_LEFT);
    CHECK(s->x_half==15 && s->event.node==4 && s->event.variables[0]==1 && s->event.variables[1]==2);
    input(s,r,BTP_ACCEPT); /* Once-only region/command did not grant a second cache. */
    BtpEventNode command={.op=BTP_EVENT_VARIABLE,.argument=0,.x=1,.value=2};
    *old=*s;CHECK(!btp_mission_variable(s,a,&command) && !memcmp(s,old,sizeof *s));
    command.x=2;CHECK(!btp_mission_variable(s,a,&command) && !memcmp(s,old,sizeof *s));
    command.value=1;CHECK(btp_mission_variable(s,a,&command) && !s->event.variables[0]);
    command=(BtpEventNode){.op=BTP_EVENT_OBJECTIVE,.argument=0,.value=BTP_OBJECTIVE_FAILED};
    CHECK(btp_mission_objective(s,a,&command));CHECK(btp_mission_objective(s,a,&command));
    command.value=BTP_OBJECTIVE_COMPLETE;*old=*s;
    CHECK(!btp_mission_objective(s,a,&command) && !memcmp(s,old,sizeof *s));
    BtpEventNode test={.op=BTP_EVENT_CHECK,.count=3,.conditions={
        {.kind=BTP_CONDITION_VARIABLE,.argument=1,.compare=5,.value=2},
        {.kind=BTP_CONDITION_OBJECTIVE,.argument=0,.value=BTP_OBJECTIVE_FAILED},
        {.kind=BTP_CONDITION_REGION,.argument=0,.value=1}}};
    CHECK(btp_mission_check(s,a,&test));test.conditions[0].value=3;
    CHECK(!btp_mission_check(s,a,&test));test.value=1;CHECK(btp_mission_check(s,a,&test));
    checkpoint(s,r);char text[1024];btp_journal_text(s,r,0,text);CHECK(strstr(text,"Failed."));
    /* Raw codec rejects unknown tail versions/reserved bytes; package checks
       reject undeclared slots even if a raw save is otherwise well formed. */
    uint8_t bytes[BTP_MISSION_BYTES];btp_mission_encode(s,bytes);bytes[191]=1;CHECK(!btp_mission_decode(old,bytes));
    s->event.variables[31]=1;CHECK(!btp_events_valid(s,r));s->event.variables[31]=0;
    s->event.entered|=UINT32_C(1)<<31;CHECK(!btp_events_valid(s,r));s->event.entered&=~(UINT32_C(1)<<31);
    /* Bounded Lua sees the same counter, region and objective queries. */
    BtpLuaScript *script=&r->project->scripts[0];const char *source=
        "if game.variable('test:count') == 0 and game.objective('test:objective') == 'failed' "
        "and game.in_region('test:region') then return game.command('test:ok') end";
    strcpy(script->source,source);script->length=strlen(source);
    a->nodes[6]=(BtpEventNode){.op=BTP_EVENT_LUA,.argument=0,.count=1,.next={0}};
    strcpy(a->nodes[0].id,"test:ok");s->event.node=6;unsigned next_node=255;
    CHECK(btp_lua_event(r,s,&next_node,error.text) && !next_node);
    /* Initial entry is dispatched after the start chain. Play here instead
       establishes membership quietly; subsequent crossings behave normally. */
    memset(&s->event,0,sizeof s->event);btp_mission_initialize(s,a);
    s->x_half=14;s->y_half=24;
    CHECK(btp_mission_trigger(s,a)==1 && s->event.enter_pending==2);
    s->x_half=30; /* A transfer during that first hook discards the stale entry. */
    CHECK(btp_mission_trigger(s,a)==5);
    CHECK(btp_mission_trigger(s,a)==BTP_EVENT_NODES && !s->event.enter_pending);
    memset(&s->event,0,sizeof s->event);btp_mission_initialize(s,a);
    s->x_half=14;btp_mission_preview(s,a);
    CHECK(btp_mission_trigger(s,a)==BTP_EVENT_NODES && !s->event.entered);
    /* Region rectangles remain city-local even when the leader is addressed
       through a different sector of the same composed world. A different
       planet with the same coordinates is outside the region. */
    CHECK(a->map_count>1);
    a->maps[0].world=1;a->maps[0].origin_x=20;a->maps[0].origin_y=10;
    a->maps[1].world=1;a->maps[1].origin_x=0;a->maps[1].origin_y=0;
    s->event.map=1;s->x_half=54;s->y_half=44;
    CHECK(btp_mission_region(s,a,0));
    a->maps[1].world=2;CHECK(!btp_mission_region(s,a,0));a->maps[1].world=1;
    /* A tactical unit may move far from the exploration anchor without
       leaving an extraction region; query the saved return location. */
    s->event.phase=BTP_EVENT_FIGHTING;s->event.return_map=1;
    s->campaign.return_x=54;s->campaign.return_y=44;s->x_half=s->y_half=0;
    CHECK(btp_mission_region(s,a,0));s->campaign.return_x=80;
    CHECK(!btp_mission_region(s,a,0));
    CHECK(!remove("mission-roundtrip.btp"));free(s);free(old);btp_content_close(&content);
    puts("PASS: mission crossing order, multi-step stops, once/repeat, saved pending triggers, bounded counters, terminal objectives, compound conditions, journal, Lua, transfers, preview and world/combat anchors.");return 0;
}
