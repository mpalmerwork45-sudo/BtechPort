#include "core/events.h"
#include "core/combat.h"
#include "core/party.h"
#include "core/menu.h"
#include "core/roster_game.h"
#include "data/content.h"
#include "data/project.h"
#include "data/save.h"
#include "frontend/pixels.h"
#include "authored_walk.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static BtpError error;
static const char *capture;
static FILE *recording;
static BtpState *s;
static const BtpResources *r;
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"%s:%d: %s (%s) map=%u xy=%u,%u phase=%u node=%s combat=%u round=%u\n",__FILE__,__LINE__,#x,error.text,s?s->map_id:0,s?s->x_half:0,s?s->y_half:0,s?s->event.phase:0,s&&r?r->project->adventure.nodes[s->event.node].id:"?",s?s->combat.phase:0,s?s->combat.round:0);exit(1); } } while(0)
static void checkpoint(const char *label)
{
    /* Heap storage keeps the default Windows stack reserve sufficient. */
    BtpState *copy=malloc(sizeof *copy);uint8_t *a=malloc(BTP_STATE_BYTES),*b=malloc(BTP_STATE_BYTES);
    CHECK(copy && a && b);CHECK(btp_save_write("bt-demo-roundtrip.btp",s,r,&error));
    CHECK(btp_save_load("bt-demo-roundtrip.btp",copy,r,&error));
    btp_state_encode(s,a);btp_state_encode(copy,b);CHECK(!memcmp(a,b,BTP_STATE_BYTES));*s=*copy;
    free(copy);free(a);free(b);
    if (capture && strcmp(label,"tick")) {
        char path[4096];snprintf(path,sizeof path,"%s-%s.btp",capture,label);CHECK(btp_save_write(path,s,r,&error));
        uint32_t *pixels=malloc(BTP_PIXELS*sizeof *pixels);CHECK(pixels);btp_render(r,s,0,pixels);
        snprintf(path,sizeof path,"%s-%s.ppm",capture,label);CHECK(btp_write_ppm(path,pixels));free(pixels);
    }
}
static void input(BtpAction a)
{ if(recording)fprintf(recording,"%s\n",btp_action_name(a));btp_game_tick(s,r,a);checkpoint("tick"); }
static void route_input(BtpState *state,const BtpResources *resources,BtpAction a)
{ (void)state;(void)resources;input(a); }
static void go(const char *door) { CHECK(authored_walk_to(s,r,door,route_input)); }
static void text_pages(void)
{
    unsigned pages=0;
    while(s->event.phase==BTP_EVENT_TEXT && pages++<16)input(BTP_ACCEPT);
    CHECK(pages<16);
}
static void enter(void) { CHECK(s->event.phase==BTP_EVENT_ENTRY);input(BTP_ACCEPT); }
static void fight(const char *label)
{
    CHECK(s->combat.phase==BTP_COMBAT_CONTROL);checkpoint(label);
    input(BTP_UP);input(BTP_ACCEPT);input(BTP_ACCEPT);input(BTP_ACCEPT);
    unsigned ticks=0;
    while(s->event.phase==BTP_EVENT_FIGHTING && ticks++<60000) {
        BtpAction action=s->combat.phase==BTP_COMBAT_NOTICE ? BTP_ACCEPT : BTP_IDLE;
        unsigned phase=s->combat.phase;
        if(recording)fprintf(recording,"%s\n",btp_action_name(action));
        btp_game_tick(s,r,action);
        if(phase!=s->combat.phase || !(ticks%64))checkpoint("tick");
    }
    CHECK(ticks<60000 && s->event.phase==BTP_EVENT_TEXT);
    printf("%s completed in %u ticks.\n",label,ticks);
}
int main(int argc,char **argv)
{
    CHECK(argc==6 || argc==7);capture=argc==7?argv[6]:NULL;
    if(capture){char path[4096];snprintf(path,sizeof path,"%s.actions",capture);recording=fopen(path,"w");CHECK(recording);}
    BtpOriginalContentPaths paths={argv[1],argv[2],argv[3],argv[4]};BtpContent content={0};
    CHECK(btp_content_load_project(&content,argv[5],&paths,&error));r=content.resources;
    s=calloc(1,sizeof *s);CHECK(s);btp_start(s);s->project=1;CHECK(btp_set_combat_profile(s,r,1));btp_events_start(s,r);
    CHECK(btp_party_count(&s->party)==2 && s->credits==18000);
    CHECK(!strcmp(btp_content_party_name(r,s,0),"Rowan") && !strcmp(btp_content_party_name(r,s,1),"Mira"));
    checkpoint("welcome");text_pages();CHECK(s->event.phase==BTP_EVENT_SELECT);checkpoint("contract");
    input(BTP_ACCEPT);CHECK(s->event.flags[0]);text_pages();checkpoint("town");
    BtpState *saved=malloc(sizeof *saved);CHECK(saved);*saved=*s;
    FILE *old_recording=recording;recording=NULL;
    /* Optional recruit/purchase/crew branch is checked without making a third
       pilot a prerequisite for completing either contract. */
    go("beacon:pilot");enter();input(BTP_ACCEPT);text_pages();
    CHECK(btp_party_count(&s->party)==3 && s->event.flags[1]);
    CHECK(!strcmp(btp_content_party_name(r,s,2),"Cole"));checkpoint("recruit");
    go("beacon:exchange");enter();input(BTP_ACCEPT);
    CHECK(s->event.phase==BTP_EVENT_TRADING);checkpoint("broker");
    unsigned javelin=0;while(javelin<r->roster.count && strcmp(r->roster.mechs[javelin].id,"chi-expanded:javelin-jvn-10n"))++javelin;
    CHECK(javelin<r->roster.count && btp_broker_buy(s,r,javelin)==BTP_BROKER_BOUGHT);
    CHECK(s->credits==5000 && btp_broker_count(s)==3);btp_party_allocate(s,2,2,121);
    CHECK(s->party.people[2][12]==2);checkpoint("crew");
    *s=*saved;recording=old_recording;
    input(BTP_OPEN_MENU);input(BTP_UP);input(BTP_ACCEPT);
    CHECK(s->campaign.ui==BTP_MENU_MAP);checkpoint("overview");input(BTP_ACCEPT);
    /* The route robot avoids optional markers and emits ordinary inputs.
       Every member's ground contact can now offer the requested doorway. */
    go("beacon:east-road");enter();text_pages();CHECK(s->map_id==17);
    checkpoint("road");go("beacon:checkpoint");enter();CHECK(s->event.phase==BTP_EVENT_SELECT);
    checkpoint("road-enemies");input(BTP_ACCEPT);
    *saved=*s;old_recording=recording;recording=NULL;
    /* Declining automation then selecting Retreat exercises the actual flee
       continuation. Restore the held battle only for the independent win route. */
    input(BTP_ACCEPT);input(BTP_ACCEPT);input(BTP_ACCEPT);CHECK(s->combat.phase==BTP_COMBAT_MENU);
    input(BTP_UP);input(BTP_ACCEPT);CHECK(s->event.phase==BTP_EVENT_TEXT && !s->event.flags[2]);checkpoint("withdraw");
    *s=*saved;recording=old_recording;
    fight("road-combat");CHECK(s->event.flags[2] && s->credits==18000);checkpoint("road-victory");text_pages();
    go("beacon:road-back");enter();CHECK(s->map_id==16);
    go("beacon:office");enter();CHECK(s->event.phase==BTP_EVENT_SELECT && s->credits==26000 && s->event.flags[3]);checkpoint("second-contract");
    *saved=*s;old_recording=recording;recording=NULL;
    input(BTP_DOWN);input(BTP_ACCEPT);checkpoint("short-ending");text_pages();
    CHECK(s->event.phase==BTP_EVENT_COMPLETE && !s->event.flags[6]);input(BTP_ACCEPT);CHECK(s->menu.quit);
    *s=*saved;recording=old_recording;
    input(BTP_ACCEPT);CHECK(s->event.flags[4]);text_pages();
    /* Revisit the office: its receipt must prevent a second 8,000 payment. */
    go("beacon:office");enter();CHECK(s->credits==26000);input(BTP_CANCEL);
    go("beacon:east-road");enter();text_pages();
    go("beacon:relay-road");enter();text_pages();CHECK(s->map_id==18);checkpoint("relay");
    go("beacon:relay-fight");enter();checkpoint("relay-enemies");input(BTP_ACCEPT);
    fight("relay-combat");CHECK(s->event.flags[5] && s->credits==26000);checkpoint("relay-victory");text_pages();
    go("beacon:relay-back");enter();CHECK(s->map_id==17);
    go("beacon:road-back");enter();CHECK(s->map_id==16);
    go("beacon:office");enter();
    CHECK(s->event.flags[6] && s->credits==41000);checkpoint("ending");text_pages();
    CHECK(s->event.phase==BTP_EVENT_COMPLETE);checkpoint("complete");input(BTP_ACCEPT);CHECK(s->menu.quit);
    free(saved);CHECK(!remove("bt-demo-roundtrip.btp"));if(recording)CHECK(!fclose(recording));
    free(s);btp_content_close(&content);puts("PASS: BattleTech two-contract route, withdrawal, both endings, receipts and saved continuations.");return 0;
}
