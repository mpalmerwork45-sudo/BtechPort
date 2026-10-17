#include "core/events.h"
#include "core/party.h"
#include "core/combat.h"
#include "core/campaign.h"
#include "core/menu.h"
#include "core/roster_game.h"
#include "data/content.h"
#include "data/project.h"
#include "data/save.h"
#include "frontend/pixels.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static BtpError error;
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"%s:%d: %s (%s)\n",__FILE__,__LINE__,#x,error.text);exit(1); } } while (0)
static const char *capture;
static void roundtrip(BtpState *s,const BtpResources *r,const char *label)
{
    BtpState copy;uint8_t a[BTP_STATE_BYTES],b[BTP_STATE_BYTES];
    CHECK(btp_events_valid(s,r));
    if (!btp_save_write("adventure-roundtrip.btp",s,r,&error)) {
        fprintf(stderr,"pause=%s mode=%u phase=%u node=%u combat=%u round=%u\n",label,s->mode,s->event.phase,s->event.node,s->combat.phase,s->combat.round);
        CHECK(0);
    }
    CHECK(btp_save_load("adventure-roundtrip.btp",&copy,r,&error));
    btp_state_encode(s,a);btp_state_encode(&copy,b);CHECK(!memcmp(a,b,sizeof a));*s=copy;
    if (capture && strcmp(label,"tick")) {
        char path[4096];snprintf(path,sizeof path,"%s-%s.btp",capture,label);CHECK(btp_save_write(path,s,r,&error));
    }
}
static void action(BtpState *s,const BtpResources *r,BtpAction a)
{ btp_game_tick(s,r,a);roundtrip(s,r,"tick"); }
static void walk(BtpState *s,const BtpResources *r,BtpAction a,unsigned n)
{ for (unsigned i=0;i<n;++i) action(s,r,a); }
static void start(BtpState *s,const BtpResources *r)
{ btp_start(s);s->project=1;CHECK(btp_set_combat_profile(s,r,1));btp_events_start(s,r); }
int main(int argc,char **argv)
{
    CHECK(argc==6 || argc==7);capture=argc==7 ? argv[6] : NULL;
    BtpOriginalContentPaths paths={argv[1],argv[2],argv[3],argv[4]};BtpContent c={0};
    CHECK(btp_content_load_project(&c,argv[5],&paths,&error));const BtpResources *r=c.resources;
    BtpState *s=calloc(1,sizeof *s);CHECK(s);start(s,r);
    CHECK(s->event.phase==BTP_EVENT_TEXT && s->credits==12000);roundtrip(s,r,"welcome");
    action(s,r,BTP_ACCEPT);CHECK(s->mode==BTP_EXPLORE);roundtrip(s,r,"map");
    /* A roof graphic and its collision can be edited independently. */
    const BtpScene *m=btp_scene(r,s);CHECK(!btp_scene_stand(m,24,16,0));CHECK(btp_scene_stand(m,24,20,0));
    s->menu.steps=4;walk(s,r,BTP_UP,2);CHECK(s->event.phase==BTP_EVENT_ENTRY && s->y_half==21);roundtrip(s,r,"entrance");
    action(s,r,BTP_ACCEPT);CHECK(s->event.phase==BTP_EVENT_SELECT);roundtrip(s,r,"choices");
    action(s,r,BTP_ACCEPT);CHECK(s->event.phase==BTP_EVENT_TRADING);roundtrip(s,r,"broker");
    CHECK(btp_broker_buy(s,r,0)==BTP_BROKER_UNAVAILABLE); /* Rook is deliberately absent from this shop. */
    action(s,r,BTP_ACCEPT);action(s,r,BTP_ACCEPT); /* light catalogue */
    CHECK(s->menu.map_x==1 && s->menu.map_y==1);
    action(s,r,BTP_ACCEPT);action(s,r,BTP_UP);action(s,r,BTP_ACCEPT);
    CHECK(btp_broker_count(s)==2 && s->credits==11000);roundtrip(s,r,"purchase");
    action(s,r,BTP_CANCEL);action(s,r,BTP_CANCEL);action(s,r,BTP_CANCEL);action(s,r,BTP_CANCEL);
    CHECK(s->event.phase==BTP_EVENT_SELECT);action(s,r,BTP_CANCEL);CHECK(s->mode==BTP_EXPLORE);
    s->menu.steps=1;walk(s,r,BTP_RIGHT,16);action(s,r,BTP_UP);action(s,r,BTP_ACCEPT);
    action(s,r,BTP_ACCEPT);CHECK(btp_party_count(&s->party)==2 && s->event.flags[0]);roundtrip(s,r,"recruit");
    action(s,r,BTP_ACCEPT);action(s,r,BTP_ACCEPT);CHECK(btp_party_count(&s->party)==2); /* Already recruited branch. */
    action(s,r,BTP_ACCEPT);action(s,r,BTP_CANCEL);
    /* Give the purchased mech its pilot through the existing allocation API. */
    btp_party_allocate(s,1,1,121);roundtrip(s,r,"crew");
    walk(s,r,BTP_DOWN,7);walk(s,r,BTP_RIGHT,14);CHECK(s->event.phase==BTP_EVENT_ENTRY);
    action(s,r,BTP_ACCEPT);CHECK(s->map_id==17 && s->event.phase==BTP_EVENT_TEXT);roundtrip(s,r,"transfer");
    action(s,r,BTP_ACCEPT);walk(s,r,BTP_RIGHT,10);action(s,r,BTP_ACCEPT);action(s,r,BTP_ACCEPT);
    CHECK(s->combat.phase==BTP_COMBAT_CONTROL);roundtrip(s,r,"combat");
    BtpState *battle_start=malloc(sizeof *battle_start);CHECK(battle_start);*battle_start=*s;
    /* Automated play still runs the real shared combat loop. Save during
       held reports, animation and rounds, then resume the decoded instance. */
    unsigned ticks=0;
    while (s->event.phase==BTP_EVENT_FIGHTING && ticks++<30000) {
        BtpAction a=BTP_IDLE;
        if (s->combat.phase==BTP_COMBAT_CONTROL) { s->combat.selected=0;a=BTP_ACCEPT; }
        else if (s->combat.phase==BTP_COMBAT_MESSAGES || s->combat.phase==BTP_COMBAT_GRAPHICS || s->combat.phase==BTP_COMBAT_NOTICE) a=BTP_ACCEPT;
        unsigned phase=s->combat.phase;
        btp_game_tick(s,r,a);
        if (phase!=s->combat.phase || !(ticks%32)) roundtrip(s,r,"tick");
    }
    CHECK(ticks<30000 && s->event.phase==BTP_EVENT_TEXT && s->event.flags[1] && s->credits==13500);roundtrip(s,r,"victory");
    action(s,r,BTP_ACCEPT);action(s,r,BTP_RIGHT);action(s,r,BTP_ACCEPT);
    CHECK(s->event.phase==BTP_EVENT_TEXT && s->credits==13500); /* No repeated battle/payment. */
    action(s,r,BTP_ACCEPT);action(s,r,BTP_OPEN_MENU);roundtrip(s,r,"space-menu");
    s->campaign.ui=BTP_MENU_MAP;s->campaign.selected=0;roundtrip(s,r,"overview");
    action(s,r,BTP_ACCEPT);
    /* Unknown saved node/flag/receipt cannot bypass shared validation. */
    BtpState bad=*s;bad.event.node=255;CHECK(!btp_save_write("adventure-invalid.btp",&bad,r,&error));
    bad=*s;bad.event.flags[63]=1;CHECK(!btp_save_write("adventure-invalid.btp",&bad,r,&error));
    *s=*battle_start;
    action(s,r,BTP_ACCEPT);action(s,r,BTP_ACCEPT);action(s,r,BTP_ACCEPT);
    CHECK(s->combat.phase==BTP_COMBAT_MENU);
    action(s,r,BTP_UP);action(s,r,BTP_ACCEPT);
    CHECK(s->event.phase==BTP_EVENT_TEXT && !s->event.flags[1] && s->credits==11000);
    roundtrip(s,r,"withdraw");free(battle_start);
    CHECK(!remove("adventure-roundtrip.btp"));free(s);btp_content_close(&c);
    puts("PASS: authored maps, collision, choices, stock, recruitment, transfer, combat, once-only reward and saved continuations.");return 0;
}
