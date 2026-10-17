#include "data/content.h"
#include "data/portraits.h"
#include "data/anm.h"
#include "data/save.h"
#include "core/animation.h"
#include "core/party.h"
#include "core/npc.h"
#include "core/training.h"
#include "frontend/pixels.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"FAIL %s:%d: %s\n",__FILE__,__LINE__,#x);exit(1); } } while (0)
static BtpError error;
static const struct { unsigned building;const char *name; } cases[]={
    {0,"training"},{7,"lounge"},{13,"prison"},{21,"inventor"},
    {16,"cinema"},{9,"hospital"},{2,"comstar"}
};

static void enter(BtpState *s,const BtpResources *r,unsigned building)
{
    btp_start(s);s->credits=1000;s->story_flags[20]=1;
    if (building<8) {
        /* The real Citadel-area doorway, after the prerequisite mech quiz. */
        s->x_half=(uint16_t)((r->map.entrance_x[building]&127u)-1u);
        s->y_half=r->map.entrance_y[building]&127u;
        btp_game_tick(s,r,BTP_RIGHT);CHECK(s->mode==BTP_ENTRY);
        btp_game_tick(s,r,BTP_ACCEPT);
    } else {
        /* Controlled outdoor prerequisites at real MTP doors. Enter through
           normal movement so checkpoints carry valid map and party context. */
        s->map_id=(uint8_t)(building==13 ? 3 : building==21 ? 12 : building==16 ? 6 : 2);
        s->story_flags[4]=1;s->story_flags[36]=127;s->weapon=9;s->mech_skills[1]=1;
        const BtpMap *map=btp_active_map(r,s);unsigned slot=0;
        while (slot<16 && map->room_map[slot]!=building) ++slot;
        CHECK(slot<16);
        s->x_half=map->entrance_x[slot]&127u;s->y_half=(uint16_t)((map->entrance_y[slot]&127u)+1u);
        s->campaign.world_x=(uint16_t)((map->entrance_x[0]>>8)*128u+s->x_half);
        s->campaign.world_y=(uint16_t)((map->entrance_y[0]>>12)*128u+s->y_half);
        btp_npc_enter(s,map);btp_party_init(s);
        btp_game_tick(s,r,BTP_UP);CHECK(s->mode==BTP_ENTRY);
        btp_game_tick(s,r,BTP_ACCEPT);
    }
    CHECK(s->mode==BTP_BUILDING && s->script.status!=BTP_SCRIPT_ERROR);
    CHECK(btp_building_kind(r,s)==building);
}

static void compare(const BtpResources *updated,const BtpResources *original,
    const BtpState *s,uint32_t *frame,uint32_t *baseline,int has_art)
{
    btp_render(updated,s,0,frame);btp_render(original,s,0,baseline);
    unsigned differences=0;
    for (unsigned y=0;y<200;++y) for (unsigned x=0;x<320;++x) {
        int inside=x>=8 && x<96 && y>=8 && y<96;
        if (has_art && inside) differences+=frame[y*320+x]!=baseline[y*320+x];
        else CHECK(frame[y*320+x]==baseline[y*320+x]);
    }
    if (has_art) CHECK(differences>100);
}

int main(int argc,char **argv)
{
    CHECK(argc==6 || argc==7);
    BtpOriginalContentPaths paths={argv[1],argv[2],argv[3],argv[4]};
    BtpContent content={0},original={0};
    CHECK(btp_content_load_original(&content,&paths,&error));
    CHECK(btp_content_load_original(&original,&paths,&error));
    CHECK(btp_content_select(&content,BTP_CONTENT_UPDATED,argv[5],&error));
    BtpResources *r=content.resources;
    BtpState *s=malloc(sizeof *s),*copy=malloc(sizeof *copy);CHECK(s && copy);
    uint32_t *frame=malloc(BTP_PIXELS*sizeof *frame),*baseline=malloc(BTP_PIXELS*sizeof *baseline);CHECK(frame && baseline);
    CHECK(r->roster.fingerprint==751321522u);
    for (unsigned i=0;i<sizeof cases/sizeof cases[0];++i) {
        unsigned building=cases[i].building;
        CHECK(btp_portrait_for_building(r,building)!=NULL);
        CHECK(!btp_portrait_for_building(original.resources,building));
        enter(s,r,building);compare(r,original.resources,s,frame,baseline,1);
        char path[4096];
        snprintf(path,sizeof path,"%s-%s.btp",argc==7 ? argv[6] : "btp-art-held",cases[i].name);
        if (!btp_save_write(path,s,r,&error)) { fprintf(stderr,"%s: %s\n",cases[i].name,error.text);CHECK(0); }
        CHECK(btp_save_load(path,copy,r,&error));
        uint8_t a[BTP_STATE_BYTES],b[BTP_STATE_BYTES];
        btp_state_encode(s,a);btp_state_encode(copy,b);CHECK(!memcmp(a,b,sizeof a));
        btp_render(r,copy,0,baseline);CHECK(!memcmp(frame,baseline,BTP_PIXELS*sizeof *frame));
        if (argc==7) {
            snprintf(path,sizeof path,"%s-%s.ppm",argv[6],cases[i].name);CHECK(btp_write_ppm(path,frame));
        } else CHECK(!remove(path));

        /* Cosmetic content must leave each building's actual continuations,
           money and choices identical for the same accepted input. */
        *copy=*s;
        for (unsigned step=0;step<12 && s->mode==BTP_BUILDING;++step) {
            BtpAction action=s->cutscene.active || s->audio.sound_count ? BTP_IDLE : BTP_ACCEPT;
            btp_game_tick(s,r,action);btp_game_tick(copy,original.resources,action);
            btp_state_encode(s,a);btp_state_encode(copy,b);CHECK(!memcmp(a,b,sizeof a));
            CHECK(s->script.status!=BTP_SCRIPT_ERROR);
        }
    }
    CHECK(!btp_portrait_for_building(r,1)); /* Katrina/Citadel was not replaced. */
    CHECK(!btp_portrait_for_building(r,5)); /* Original Mech-It animation. */
    CHECK(!btp_portrait_for_building(r,999));

    /* Every native cinema shot, including O0, overrides the box-office art.
       Held final frames also compare with Original after playback stops. */
    for (unsigned kind=0;kind<10;++kind) {
        enter(s,r,16);s->script.status=BTP_SCRIPT_ANIMATION;
        s->script.animation_kind=(uint8_t)kind;s->script.animation_flags=2;
        CHECK(btp_cutscene_begin(s,r,kind,1));compare(r,original.resources,s,frame,baseline,0);
        s->cutscene.active=0;s->script.status=BTP_SCRIPT_WAIT;
        compare(r,original.resources,s,frame,baseline,0);
    }
    /* A training illustration must never cover the full-screen mech quiz. */
    enter(s,r,0);btp_quiz_begin(s);compare(r,original.resources,s,frame,baseline,0);
    btp_game_tick(s,r,BTP_ACCEPT);compare(r,original.resources,s,frame,baseline,0);
    free(frame);free(baseline);free(s);free(copy);
    btp_content_close(&content);btp_content_close(&original);
    printf("PASS: %u building-art, original-panel, save and scene-priority checks\n",checks);
    return 0;
}
