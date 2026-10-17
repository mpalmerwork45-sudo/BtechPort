#include "core/events.h"
#include "core/combat.h"
#include "core/menu.h"
#include "core/audio.h"
#include "data/content.h"
#include "data/project.h"
#include "data/save.h"
#include "frontend/pixels.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static BtpError error;
static const char *capture;
static FILE *recording;
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"%s:%d: %s (%s)\n",__FILE__,__LINE__,#x,error.text);exit(1); } } while (0)
static void pause_at(BtpState *s,const BtpResources *r,const char *label)
{
    BtpState copy;uint8_t a[BTP_STATE_BYTES],b[BTP_STATE_BYTES];
    CHECK(btp_events_valid(s,r));
    if (!btp_save_write("beacon-roundtrip.btp",s,r,&error)) { fprintf(stderr,"pause=%s mode=%u phase=%u node=%u combat=%u\n",label,s->mode,s->event.phase,s->event.node,s->combat.phase);CHECK(0); }
    CHECK(btp_save_load("beacon-roundtrip.btp",&copy,r,&error));
    btp_state_encode(s,a);btp_state_encode(&copy,b);CHECK(!memcmp(a,b,sizeof a));*s=copy;
    if (capture && strcmp(label,"tick")) {
        char path[4096];snprintf(path,sizeof path,"%s-%s.btp",capture,label);CHECK(btp_save_write(path,s,r,&error));
        uint32_t *pixels=malloc(BTP_PIXELS*sizeof *pixels);CHECK(pixels);btp_render(r,s,0,pixels);
        snprintf(path,sizeof path,"%s-%s.ppm",capture,label);CHECK(btp_write_ppm(path,pixels));free(pixels);
    }
}
static void action(BtpState *s,const BtpResources *r,BtpAction a)
{ if (recording) fprintf(recording,"%s\n",btp_action_name(a));btp_game_tick(s,r,a);pause_at(s,r,"tick"); }
static void walk(BtpState *s,const BtpResources *r,BtpAction a,unsigned n)
{ while (n--) action(s,r,a); }
int main(int argc,char **argv)
{
    CHECK(argc==2 || argc==3);capture=argc==3 ? argv[2] : NULL;
    if (capture) { char path[4096];snprintf(path,sizeof path,"%s.actions",capture);recording=fopen(path,"w");CHECK(recording); }
    BtpContent c={0};CHECK(btp_content_load_project(&c,argv[1],NULL,&error));const BtpResources *r=c.resources;
    CHECK(r->project->independent.loaded && !r->dialogue.length && !r->world.loaded && !r->map.width);
    CHECK(!btp_content_select(&c,BTP_CONTENT_ORIGINAL_DOS_103,NULL,&error) && c.resources==r);
    CHECK(!btp_content_load_project(&c,"missing-independent-project",NULL,&error) && c.resources==r);
    error.text[0]=0;
    BtpState *s=calloc(1,sizeof *s);CHECK(s);btp_start(s);s->project=1;CHECK(btp_set_combat_profile(s,r,1));btp_events_start(s,r);
    pause_at(s,r,"welcome");action(s,r,BTP_ACCEPT);pause_at(s,r,"town");
    walk(s,r,BTP_RIGHT,10);walk(s,r,BTP_UP,2);CHECK(s->event.phase==BTP_EVENT_ENTRY);pause_at(s,r,"npc");
    action(s,r,BTP_ACCEPT);CHECK(s->event.phase==BTP_EVENT_SELECT);pause_at(s,r,"choice");
    action(s,r,BTP_ACCEPT);CHECK(s->event.flags[0] && s->party.people[1][0]==1);pause_at(s,r,"recruit");action(s,r,BTP_ACCEPT);
    walk(s,r,BTP_DOWN,1);walk(s,r,BTP_RIGHT,20);CHECK(s->event.phase==BTP_EVENT_ENTRY);
    action(s,r,BTP_ACCEPT);CHECK(s->map_id==17);action(s,r,BTP_ACCEPT);pause_at(s,r,"wilderness");
    walk(s,r,BTP_RIGHT,28);CHECK(s->event.phase==BTP_EVENT_ENTRY);action(s,r,BTP_ACCEPT);action(s,r,BTP_ACCEPT);
    CHECK(s->combat.phase==BTP_COMBAT_CONTROL);pause_at(s,r,"combat");
    BtpState *checkpoint=malloc(sizeof *checkpoint);CHECK(checkpoint);*checkpoint=*s;
    FILE *saved_recording=recording;recording=NULL;
    action(s,r,BTP_ACCEPT);action(s,r,BTP_ACCEPT);action(s,r,BTP_ACCEPT);
    action(s,r,BTP_DOWN);action(s,r,BTP_ACCEPT);CHECK(s->combat.phase==BTP_COMBAT_MOVE);
    unsigned cursor=s->combat.cursor_x;action(s,r,BTP_RIGHT);CHECK(s->combat.cursor_x==cursor+1);
    pause_at(s,r,"manual-move");action(s,r,BTP_CANCEL);
    *s=*checkpoint;free(checkpoint);recording=saved_recording;
    /* Real menu input enables the shared computer planner. This route never
       edits health, forces a result, teleports or patches a story flag. */
    action(s,r,BTP_UP);action(s,r,BTP_ACCEPT);action(s,r,BTP_ACCEPT);action(s,r,BTP_ACCEPT);
    unsigned ticks=0,samples=0;
    while (s->event.phase==BTP_EVENT_FIGHTING && ticks++<30000) {
        BtpAction input=s->combat.phase==BTP_COMBAT_NOTICE ? BTP_ACCEPT : BTP_IDLE;
        int16_t pcm[BTP_AUDIO_TICK_SAMPLES];unsigned phase=s->combat.phase;
        if (recording) fprintf(recording,"%s\n",btp_action_name(input));
        btp_game_tick_audio(s,r,input,pcm);
        for (unsigned i=0;i<BTP_AUDIO_TICK_SAMPLES;++i) samples+=(pcm[i]!=0);
        if (phase!=s->combat.phase || !(ticks%32)) pause_at(s,r,"tick");
    }
    CHECK(ticks<30000 && s->event.flags[1] && !s->event.flags[2] && s->credits==2000 && samples);pause_at(s,r,"victory");
    action(s,r,BTP_ACCEPT);walk(s,r,BTP_LEFT,29);CHECK(s->event.phase==BTP_EVENT_ENTRY);
    action(s,r,BTP_ACCEPT);CHECK(s->map_id==16);walk(s,r,BTP_LEFT,10);walk(s,r,BTP_UP,6);
    CHECK(s->event.phase==BTP_EVENT_ENTRY);action(s,r,BTP_ACCEPT);
    CHECK(s->event.phase==BTP_EVENT_TEXT && s->event.flags[2] && s->credits==4500);pause_at(s,r,"ending");
    action(s,r,BTP_ACCEPT);CHECK(s->event.phase==BTP_EVENT_COMPLETE && s->mode==BTP_ENDING);pause_at(s,r,"complete");
    action(s,r,BTP_ACCEPT);CHECK(s->menu.quit);
    CHECK(!remove("beacon-roundtrip.btp"));if (recording) CHECK(!fclose(recording));free(s);btp_content_close(&c);
    printf("PASS: independent complete quest, Lua, saved dialogue/combat/ending, authored PCM (%u nonzero samples).\n",samples);return 0;
}
