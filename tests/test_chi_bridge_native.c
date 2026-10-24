/* Private imported fixtures supply all original data. Each held continuation
   is decoded before driving its suffix, including the complete bridge tail. */
#include "data/content.h"
#include "data/project.h"
#include "data/save.h"
#include "core/chi_bridge.h"
#include "core/events.h"
#include "core/npc.h"
#include "core/party.h"
#include "core/combat.h"
#include "frontend/pixels.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static BtpError error;static const char *prefix;
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"bridge %d: %s (%s)\n",__LINE__,#x,error.text);exit(1); } } while(0)
static void bytes(const BtpState *s,uint8_t *out)
{ btp_state_encode(s,out);btp_bridge_encode(s,out+BTP_STATE_BYTES); }
static void held(BtpState *s,const BtpResources *r,const char *label)
{
    char path[4096];snprintf(path,sizeof path,"%s-%s.btp",prefix,label);
    if(!btp_events_valid(s,r)){fprintf(stderr,"invalid bridge at %s\n",label);CHECK(0);}
    if (!btp_save_write(path,s,r,&error)) {
        fprintf(stderr,"held %s: mode%u phase%u node%u depth%u call%u script%u pc%x\n",label,s->mode,s->event.phase,s->event.node,s->bridge.depth,s->bridge.call,s->script.status,s->script.pc);CHECK(0);
    }
    BtpState *copy=calloc(1,sizeof *copy);uint8_t *a=malloc(BTP_STATE_BYTES+BTP_BRIDGE_BYTES),*b=malloc(BTP_STATE_BYTES+BTP_BRIDGE_BYTES);
    CHECK(copy && a && b && btp_save_load(path,copy,r,&error));bytes(s,a);bytes(copy,b);CHECK(!memcmp(a,b,BTP_STATE_BYTES+BTP_BRIDGE_BYTES));
    uint32_t *frame=malloc(BTP_PIXELS*sizeof *frame),*other=malloc(BTP_PIXELS*sizeof *other);CHECK(frame && other);
    btp_render(r,s,0,frame);btp_render(r,copy,0,other);CHECK(!memcmp(frame,other,BTP_PIXELS*sizeof *frame));
    snprintf(path,sizeof path,"%s-%s.ppm",prefix,label);CHECK(btp_write_ppm(path,frame));
    /* Compare the next ordinary input too, not merely an encode/decode of
       fields that could be ignored by the live interpreter. */
    btp_game_tick(s,r,BTP_IDLE);btp_game_tick(copy,r,BTP_IDLE);bytes(s,a);bytes(copy,b);CHECK(!memcmp(a,b,BTP_STATE_BYTES+BTP_BRIDGE_BYTES));
    snprintf(path,sizeof path,"%s-%s-suffix.bin",prefix,label);FILE *suffix=fopen(path,"wb");CHECK(suffix);
    CHECK(fwrite(a,1,BTP_STATE_BYTES+BTP_BRIDGE_BYTES,suffix)==BTP_STATE_BYTES+BTP_BRIDGE_BYTES);CHECK(!fclose(suffix));
    /* Drive the remaining real journey from the decoded state. Comparing one
       idle alone would not exercise later choices/returns after loading. */
    *s=*copy;
    free(frame);free(other);free(a);free(b);free(copy);
}
static void input(BtpState *s,const BtpResources *r,BtpAction action)
{ btp_game_tick(s,r,action);CHECK(!s->script.error && !s->bridge.fault); }
static void start(BtpState *s,const BtpResources *r)
{
    btp_start_content(s,r);s->project=1;btp_npc_init(s,&r->map);btp_bridge_initialize(s,r);
    if(btp_resources_feature(r,BTP_FEATURE_ENHANCED))CHECK(btp_set_combat_profile(s,r,1));
    input(s,r,BTP_RIGHT);input(s,r,BTP_RIGHT);CHECK(s->mode==BTP_ENTRY);input(s,r,BTP_ACCEPT);
    CHECK(s->event.phase==BTP_EVENT_TEXT && s->bridge.depth==1 && !s->bridge.scene);
}
static void nested(BtpState *s,const BtpResources *r)
{
    btp_start_content(s,r);s->project=1;btp_bridge_initialize(s,r);
    unsigned door=0;while(door<16 && r->map.room_map[door]!=4)++door;CHECK(door<16);
    CHECK(btp_chi_preview(s,r,"chi:map-01",(r->map.entrance_x[door]&127)-1,r->map.entrance_y[door]&127));
    input(s,r,BTP_RIGHT);input(s,r,BTP_ACCEPT);CHECK(s->bridge.depth==1 && s->event.phase==BTP_EVENT_SELECT && s->story_flags[80]==1);
    BtpState *begin=malloc(sizeof *begin);CHECK(begin);*begin=*s;held(s,r,"bld-choice");
    input(s,r,BTP_ACCEPT);CHECK(s->bank.phase==BTP_BANK_MENU && s->bridge.depth==2);held(s,r,"bld-company");
    input(s,r,BTP_ACCEPT);input(s,r,BTP_DIGIT_2);held(s,r,"bld-amount");input(s,r,BTP_ACCEPT);held(s,r,"bld-receipt");input(s,r,BTP_ACCEPT);
    CHECK(!s->bridge.depth && s->credits==133 && s->investments[0]==2 && s->story_flags[81]==1 && s->story_flags[80]==1 && s->script.status==BTP_SCRIPT_MENU);held(s,r,"bld-menu");
    *s=*begin;input(s,r,BTP_DOWN);input(s,r,BTP_ACCEPT);CHECK(s->bridge.depth==4 && s->event.phase==BTP_EVENT_TEXT);held(s,r,"four-frames");input(s,r,BTP_ACCEPT);
    CHECK(!s->bridge.depth && s->credits==135 && s->story_flags[81]==1 && s->story_flags[80]==1);held(s,r,"nested-return");
    *s=*begin;input(s,r,BTP_DOWN);input(s,r,BTP_DOWN);input(s,r,BTP_ACCEPT);
    CHECK(s->bridge.depth==4 && s->event.phase==BTP_EVENT_TEXT);held(s,r,"depth-rejected");input(s,r,BTP_ACCEPT);
    if(s->bridge.depth || s->credits!=35 || s->story_flags[81]!=2)fprintf(stderr,"depth result depth%u cash%u flag%u node%u phase%u\n",s->bridge.depth,s->credits,s->story_flags[81],s->event.node,s->event.phase);
    CHECK(!s->bridge.depth && s->credits==35 && s->story_flags[81]==2);
    *s=*begin;input(s,r,BTP_DOWN);input(s,r,BTP_DOWN);input(s,r,BTP_DOWN);input(s,r,BTP_ACCEPT);
    CHECK(s->bridge.depth==2 && s->event.phase==BTP_EVENT_TEXT);held(s,r,"cycle-rejected");input(s,r,BTP_ACCEPT);
    /* Both the rejected inner invocation and its caller take the declared
       failure label. Acknowledge each, without silently skipping dialogue. */
    CHECK(s->bridge.depth==1 && s->event.phase==BTP_EVENT_TEXT);input(s,r,BTP_ACCEPT);CHECK(!s->bridge.depth && s->story_flags[81]==2);
    *s=*begin;input(s,r,BTP_UP);btp_game_tick(s,r,BTP_ACCEPT);
    CHECK(s->bridge.fault && s->event.phase==BTP_EVENT_FAULT);held(s,r,"budget-fault");
    input(s,r,BTP_CANCEL);CHECK(!s->bridge.depth && s->story_flags[81]==2 && !s->bridge.fault);
    *s=*begin;input(s,r,BTP_CANCEL);CHECK(!s->bridge.depth && s->credits==35 && s->story_flags[81]==3);held(s,r,"bld-cancel");
    *s=*begin;s->story_flags[82]=1;input(s,r,BTP_DOWN);input(s,r,BTP_ACCEPT);
    btp_game_tick(s,r,BTP_ACCEPT);CHECK(s->mode==BTP_SCRIPT_FAULT && !s->bridge.depth && s->credits==135 && s->event.done[2]);held(s,r,"fault-after-reward");
    /* Every tail frame is validated before it is allowed to choose a PC. */
    *s=*begin;s->bridge.frames[0].script.pc=1;CHECK(!btp_events_valid(s,r));
    *s=*begin;s->bridge.frames[0].script.money_amount++;CHECK(!btp_events_valid(s,r));
    *s=*begin;s->bridge.frames[0].program=2;CHECK(!btp_events_valid(s,r));
    *s=*begin;s->bridge.frames[0].script.font=255;CHECK(!btp_events_valid(s,r));free(begin);
    puts("PASS: BLD/event/native/event/BLD, four frames, excess/cycle rejection, cancel/failure labels and committed reward after a native fault.");
}
int main(int argc,char **argv)
{
    CHECK(argc==3 || argc==4);prefix=argv[2];BtpContent content={0};CHECK(btp_content_load_project(&content,argv[1],NULL,&error));
    const BtpResources *r=content.resources;BtpState *s=calloc(1,sizeof *s),*initial=calloc(1,sizeof *initial),*fight=calloc(1,sizeof *fight);CHECK(s && initial && fight);
    if(argc==4){nested(s,r);free(s);free(initial);free(fight);btp_content_close(&content);return 0;}
    start(s,r);held(s,r,"dialogue");input(s,r,BTP_ACCEPT);held(s,r,"choice");*initial=*s;
    input(s,r,BTP_DOWN);input(s,r,BTP_ACCEPT);CHECK(s->bank.phase==BTP_BANK_MENU);held(s,r,"company");
    input(s,r,BTP_ACCEPT);input(s,r,BTP_DIGIT_1);held(s,r,"amount");input(s,r,BTP_ACCEPT);
    CHECK(s->credits==34 && s->investments[0]==1);held(s,r,"receipt");input(s,r,BTP_ACCEPT);
    CHECK(s->event.phase==BTP_EVENT_SELECT && s->bridge.depth==1 && s->credits==34);held(s,r,"service-return");
    input(s,r,BTP_CANCEL);CHECK(s->mode==BTP_EXPLORE && !s->bridge.depth && !s->bridge.scene);held(s,r,"outside");
    input(s,r,BTP_RIGHT);CHECK(s->mode==BTP_ENTRY);input(s,r,BTP_ACCEPT);input(s,r,BTP_ACCEPT);CHECK(s->event.phase==BTP_EVENT_SELECT);
    input(s,r,BTP_DOWN);input(s,r,BTP_ACCEPT);input(s,r,BTP_CANCEL);CHECK(s->event.phase==BTP_EVENT_SELECT && s->credits==34);
    *s=*initial;s->credits=0;input(s,r,BTP_DOWN);input(s,r,BTP_ACCEPT);CHECK(s->bank.outcome==BTP_BANK_NO_CASH);held(s,r,"no-cash");input(s,r,BTP_ACCEPT);
    CHECK(s->event.phase==BTP_EVENT_TEXT);input(s,r,BTP_ACCEPT);input(s,r,BTP_CANCEL);CHECK(!s->bridge.depth && !s->credits);
    *s=*initial;
    /* Prepared combat fixture: armed and trained crew, without changing the
       bridge's native startup or inventing an in-game equipment reward. */
    s->weapon=s->party.people[0][11]=7;s->skills[1]=s->party.people[0][5]=4;
    input(s,r,BTP_ACCEPT);CHECK(s->event.phase==BTP_EVENT_PRESENTATION && s->audio.sound_count);held(s,r,"sound");
    unsigned ticks=0;while(!s->cutscene.active && ticks++<2000)input(s,r,BTP_IDLE);
    CHECK(s->cutscene.active==8 && !s->audio.sound_count);held(s,r,"film");
    while(s->event.phase==BTP_EVENT_PRESENTATION && ticks++<5000)input(s,r,BTP_IDLE);
    CHECK(s->event.phase==BTP_EVENT_FIGHTING && s->bridge.scene);held(s,r,"battle");*fight=*s;
    s->bridge.parked_npc.actor[0].direction=9;CHECK(!btp_events_valid(s,r));*s=*fight;
    s->bridge.native_marks[0].sprite=1;CHECK(!btp_events_valid(s,r));*s=*fight;
    while(s->event.phase==BTP_EVENT_FIGHTING && ticks++<30000) {
        BtpAction action=BTP_IDLE;
        if(s->combat.phase==BTP_COMBAT_CONTROL)s->combat.selected=0;
        if(s->combat.phase==BTP_COMBAT_CONTROL || s->combat.phase==BTP_COMBAT_MESSAGES || s->combat.phase==BTP_COMBAT_GRAPHICS || s->combat.phase==BTP_COMBAT_NOTICE)action=BTP_ACCEPT;
        input(s,r,action);
    }
    if (!(ticks<30000 && s->event.flags[0])) fprintf(stderr,"battle ticks%u phase%u node%u combat%u round%u flags%u credits%u scene%u\n",ticks,s->event.phase,s->event.node,s->combat.phase,s->combat.round,s->event.flags[0],s->credits,s->bridge.scene);
    CHECK(ticks<30000 && s->event.phase==BTP_EVENT_TEXT && s->event.flags[0] && s->credits==285 && !s->bridge.scene);
    CHECK(!memcmp(s->explored,fight->bridge.native_explored,2048));
    CHECK(!memcmp(s->terrain_marks,fight->bridge.native_marks,sizeof s->terrain_marks));
    CHECK(s->x_half==initial->x_half && s->y_half==initial->y_half && s->map_id==initial->map_id);
    held(s,r,"reward");input(s,r,BTP_ACCEPT);CHECK(s->mode==BTP_EXPLORE && !s->bridge.depth);held(s,r,"finished");
    input(s,r,BTP_RIGHT);input(s,r,BTP_ACCEPT);input(s,r,BTP_ACCEPT);input(s,r,BTP_ACCEPT);
    CHECK(s->event.phase==BTP_EVENT_TEXT && s->credits==285 && !s->combat.phase);held(s,r,"repeat");
    *s=*fight;input(s,r,BTP_ACCEPT);input(s,r,BTP_ACCEPT);input(s,r,BTP_ACCEPT);CHECK(s->combat.phase==BTP_COMBAT_MENU);
    input(s,r,BTP_UP);input(s,r,BTP_ACCEPT);CHECK(s->event.phase==BTP_EVENT_TEXT && !s->event.flags[0] && !s->bridge.scene);
    held(s,r,"retreat");input(s,r,BTP_ACCEPT);CHECK(!s->bridge.depth && s->credits==35);
    /* A declared fragile-crew fixture loses through live combat, rather
       than assigning an outcome flag and bypassing the battle interpreter. */
    *s=*fight;s->combat.unit[0].record[15]=1;s->combat.unit[0].record[14]=0;s->combat.unit[0].record[11]=0;
    s->combat.unit[s->combat.friends].record[11]=7;s->combat.unit[s->combat.friends].record[5]=4;ticks=0;
    while(s->event.phase==BTP_EVENT_FIGHTING && ticks++<30000) {
        BtpAction action=BTP_IDLE;
        if(s->combat.phase==BTP_COMBAT_CONTROL)s->combat.selected=0;
        if(s->combat.phase==BTP_COMBAT_CONTROL || s->combat.phase==BTP_COMBAT_MESSAGES || s->combat.phase==BTP_COMBAT_GRAPHICS || s->combat.phase==BTP_COMBAT_NOTICE)action=BTP_ACCEPT;
        input(s,r,action);
    }
    CHECK(ticks<30000 && s->event.phase==BTP_EVENT_TEXT && !s->event.flags[0] && !s->bridge.scene && s->credits==35);
    held(s,r,"defeat");input(s,r,BTP_ACCEPT);CHECK(!s->bridge.depth && s->mode==BTP_GAME_OVER);held(s,r,"defeat-return");
    *s=*initial;s->bridge.depth=5;CHECK(!btp_events_valid(s,r));*s=*initial;s->bridge.frames[0].position.native_map=99;CHECK(!btp_events_valid(s,r));
    free(s);free(initial);free(fight);btp_content_close(&content);
    puts("PASS: entrance, bank, cancellation/failure, map preservation, sequential presentation, live battle, reward/reentry and held save suffixes.");return 0;
}
