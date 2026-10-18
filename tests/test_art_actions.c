#include "core/art_actions.h"
#include "core/effects.h"
#include "data/content.h"
#include "data/project.h"
#include "frontend/art.h"
#include <stdio.h>
#include <stdlib.h>
#define CHECK(v) do { if (!(v)) { fprintf(stderr,"line %d: %s\n",__LINE__,#v);return 1; } } while(0)
int main(int argc,char **argv)
{
    CHECK(argc==2);BtpContent c={0};BtpError error;CHECK(btp_content_load_project(&c,argv[1],NULL,&error));
    BtpResources *r=c.resources;BtpArt *a=&r->project->graphics;
    a->count=1;a->track_count=1;a->images[0]=(BtpArtImage){.width=1,.height=1,.count=2,.kind=1,.frames={0,1},.tracks={[BTP_ANIM_FIRE]=1}};
    a->pixels[0]=0xffff0000;a->pixels[1]=0xff0000ff;
    a->tracks[0]=(BtpArtTrack){.directions=1,.count={2},.ticks={{20,10}},.frames={{0,1}},.sound=3};
    CHECK(btp_art_frame(a,0,BTP_ANIM_FIRE,7,19,9)==0);
    CHECK(btp_art_frame(a,0,BTP_ANIM_FIRE,7,20,9)==1);
    CHECK(btp_art_frame(a,0,BTP_ANIM_FIRE,7,200,9)==1);
    a->images[0].tracks[BTP_ANIM_WALK]=1;CHECK(btp_art_frame(a,0,BTP_ANIM_WALK,2,30,9)==0);
    CHECK(btp_art_frame(a,0,BTP_ANIM_DAMAGE,2,30,9)==9);
    BtpState *s=calloc(1,sizeof *s);CHECK(s);s->combat.count=2;s->combat.graphics=1;s->combat.phase=BTP_COMBAT_ROUND;
    s->combat.unit[0].record[124]=192;s->combat.unit[1].record[124]=192;
    r->project->definitions.presentations[r->project->definitions.mechs[0].presentation].graphic=0;
    s->effects.count=1;s->effects.stage=BTP_EFFECT_POSES;s->effects.shots[0]=(BtpCombatEffect){.actor=0,.target=1,.weapon=8,.hit=1};
    CHECK(btp_action_duration(r,s,0,BTP_ANIM_FIRE)==30);CHECK(btp_action_sound(r,s,0,BTP_ANIM_FIRE,7)==3);
    s->effects.age=20;unsigned elapsed;CHECK(btp_actor_action(s,0,&elapsed)==BTP_ANIM_FIRE && elapsed==20);
    uint32_t *pixels=calloc(BTP_PIXELS,sizeof *pixels);CHECK(pixels);
    CHECK(btp_art_actor(r,s,0,0,0,0,0,320,200,pixels));CHECK(pixels[23*320+11]==0xff0000ff);
    s->event.people[0]=1;r->project->adventure.people[1].graphic=0;s->combat.ids[1]=4;s->combat.unit[1].infantry=1;
    CHECK(btp_actor_image(r,s,1)==0);
    /* Queued audio holds presentation time; rendering cannot enqueue cues. */
    s->audio.sound_count=1;btp_effects_tick(s,r);CHECK(s->effects.age==20 && s->audio.sound_count==1);
    free(pixels);free(s);btp_content_close(&c);puts("PASS: action timing, fallback, actor mapping, frame output and audio hold");return 0;
}
