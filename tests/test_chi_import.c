#include "data/content.h"
#include "data/project.h"
#include "data/save.h"
#include "core/npc.h"
#include "core/roster_game.h"
#include "frontend/pixels.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static BtpError error;
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"CHI parity %d: %s (%s)\n",__LINE__,#x,error.text);exit(1); } } while (0)
static void equal(const BtpState *a,const BtpState *b)
{
    BtpState *copy=malloc(sizeof *copy);uint8_t x[BTP_STATE_BYTES],y[BTP_STATE_BYTES];CHECK(copy);
    *copy=*a;copy->project=b->project;btp_state_encode(copy,x);btp_state_encode(b,y);free(copy);
    CHECK(!memcmp(x,y,sizeof x));
}
static void route(const char *file,const BtpResources *base,const BtpResources *imported)
{
    BtpState *a=calloc(1,sizeof *a),*b=calloc(1,sizeof *b);CHECK(a && b);
    btp_start(a);btp_start(b);b->project=1;btp_npc_init(a,&base->map);btp_npc_init(b,&imported->map);
    if (btp_resources_feature(base,BTP_FEATURE_ENHANCED)) CHECK(btp_set_combat_profile(a,base,1) && btp_set_combat_profile(b,imported,1));
    uint32_t *x=malloc(320u*200u*sizeof *x),*y=malloc(320u*200u*sizeof *y);CHECK(x && y);
    FILE *f=fopen(file,"r");CHECK(f);char line[128];unsigned ticks=0,held=0;
    equal(a,b);
    while (fgets(line,sizeof line,f)) {
        line[strcspn(line,"\r\n")]=0;if (!*line || *line=='#') continue;
        BtpAction action;CHECK(btp_action_parse(line,&action));
        btp_game_tick(a,base,action);btp_game_tick(b,imported,action);++ticks;
        equal(a,b);CHECK(!b->script.error);
        if (!held && (b->script.status==BTP_SCRIPT_WAIT || b->script.status==BTP_SCRIPT_MENU)) {
            BtpState *restored=calloc(1,sizeof *restored);CHECK(restored);
            CHECK(btp_save_write("chi-held-test.btp",b,imported,&error));
            CHECK(btp_save_load("chi-held-test.btp",restored,imported,&error));equal(b,restored);
            CHECK(!remove("chi-held-test.btp"));free(restored);held=1;
        }
        if (ticks%64u==0 || b->script.status==BTP_SCRIPT_MENU || b->script.status==BTP_SCRIPT_WAIT) {
            btp_render(base,a,0,x);btp_render(imported,b,0,y);CHECK(!memcmp(x,y,320u*200u*sizeof *x));
        }
        CHECK(ticks<120000);
    }
    CHECK(!fclose(f));CHECK(ticks);printf("Verified %u identical gameplay ticks and presentation checkpoints: %s\n",ticks,file);
    free(a);free(b);free(x);free(y);
}
int main(int argc,char **argv)
{
    if (argc==5 && !strcmp(argv[1],"--text-proof")) {
        BtpContent a={0},b={0};CHECK(btp_content_load_project(&a,argv[2],NULL,&error));
        CHECK(btp_content_load_project(&b,argv[3],NULL,&error));
        BtpState *s=calloc(1,sizeof *s);uint32_t *x=malloc(64000u*sizeof *x),*y=malloc(64000u*sizeof *y);CHECK(s && x && y);
        btp_start(s);s->project=1;s->mode=BTP_MISSION;s->combat.phase=BTP_COMBAT_CONTROL;
        btp_render(a.resources,s,0,x);btp_render(b.resources,s,0,y);CHECK(memcmp(x,y,64000u*sizeof *x));
        CHECK(btp_write_ppm(argv[4],y));puts("Native dialogue override changes the actual combat popup pixels.");
        btp_content_close(&a);btp_content_close(&b);free(s);free(x);free(y);return 0;
    }
    CHECK(argc>=9);BtpOriginalContentPaths paths={argv[1],argv[2],argv[3],argv[4]};
    BtpContent base={0},imported={0},other={0};
    CHECK(btp_content_load_original(&base,&paths,&error));
    CHECK(btp_content_load_project(&imported,argv[6],NULL,&error));
    CHECK(imported.resources->project->chi_edition==1);
    CHECK(!btp_resources_feature(imported.resources,BTP_FEATURE_BROKER));
    CHECK(!btp_resources_feature(imported.resources,BTP_FEATURE_ENHANCED));
    CHECK(btp_content_load_project(&other,argv[7],NULL,&error));
    CHECK(other.resources->project->chi_edition==2);
    for (unsigned profile=0;profile<2;++profile) {
        if (profile) {
            CHECK(btp_content_select(&base,BTP_CONTENT_UPDATED,argv[5],&error));
            BtpContent swap=imported;imported=other;other=swap;
        }
        CHECK(!memcmp(base.resources->combat.loans,imported.resources->combat.loans,sizeof base.resources->combat.loans));
        CHECK(!memcmp(&base.resources->dialogue,&imported.resources->dialogue,sizeof base.resources->dialogue));
        for (int i=8;i<argc;++i) route(argv[i],base.resources,imported.resources);
        BtpState *s=calloc(1,sizeof *s),*copy=calloc(1,sizeof *copy);CHECK(s && copy);
        btp_start(s);s->project=1;btp_npc_init(s,&imported.resources->map);
        for (unsigned slot=0;slot<6;++slot) {
            char file[4096];CHECK(btp_save_edition_slot_path("chi-parity-test.btp",slot,imported.resources,file,sizeof file,&error));
            s->credits=35+slot;CHECK(btp_save_write(file,s,imported.resources,&error));
            CHECK(btp_save_load(file,copy,imported.resources,&error));equal(s,copy);
            CHECK(!btp_save_load(file,copy,other.resources,&error));
            CHECK(!btp_save_load(file,copy,base.resources,&error));CHECK(!remove(file));
        }
        free(s);free(copy);
    }
    btp_content_close(&base);btp_content_close(&imported);btp_content_close(&other);
    puts("Verified both editions, exact templates, presentation and twelve isolated save slots.");return 0;
}
