#include "data/content.h"
#include "data/project.h"
#include "data/save.h"
#include "core/npc.h"
#include "core/menu.h"
#include "core/roster_game.h"
#include "core/party.h"
#include "core/campaign.h"
#include "core/world.h"
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
    if(memcmp(x,y,sizeof x))for(unsigned i=0;i<sizeof x;++i)if(x[i]!=y[i]) {
        fprintf(stderr,"First encoded difference: tick %u, offset %u, built-in %u, imported %u\n",a->tick,i,x[i],y[i]);break;
    }
    CHECK(!memcmp(x,y,sizeof x));
}
static void intro(const BtpResources *base,const BtpResources *imported)
{
    BtpState *a=calloc(1,sizeof *a),*b=calloc(1,sizeof *b);CHECK(a && b);
    uint32_t *x=malloc(64000u*sizeof *x),*y=malloc(64000u*sizeof *y);CHECK(x && y);
    btp_start(a);btp_start(b);b->project=1;btp_npc_init(a,&base->map);btp_npc_init(b,&imported->map);
    if (btp_resources_feature(base,BTP_FEATURE_ENHANCED)) CHECK(btp_set_combat_profile(a,base,1) && btp_set_combat_profile(b,imported,1));
    a->mode=b->mode=BTP_LOGO;
    const BtpAction actions[]={BTP_IDLE,BTP_OPEN_MENU,BTP_IDLE,BTP_OPEN_MENU,BTP_ACCEPT};
    for (unsigned i=0;i<sizeof actions/sizeof *actions;++i) {
        btp_render(base,a,0,x);btp_render(imported,b,0,y);CHECK(!memcmp(x,y,64000u*sizeof *x));
        btp_game_tick(a,base,actions[i]);btp_game_tick(b,imported,actions[i]);equal(a,b);
    }
    CHECK(a->mode==BTP_EXPLORE);free(a);free(b);free(x);free(y);
}
static void same_record(uint8_t a[125],const uint8_t b[125],const BtpResources *base,const BtpResources *imported)
{
    if(!btp_roster_custom(a) && !btp_roster_custom(b))return;
    const BtpRosterMech *x=btp_roster_definition(&base->roster,a),*y=btp_roster_definition(&imported->roster,b);
    CHECK(x && y && !strcmp(x->id,y->id));
    /* Built-in roster v1 uses legacy save codes; editable definitions use
       project ordinals. Only these two identity bytes may differ. Every
       other live record byte, state field, RNG and rendered pixel is checked. */
    a[123]=b[123];a[124]=b[124];
}
static void same_route_state(const BtpState *a,const BtpState *b,const BtpResources *base,const BtpResources *imported)
{
    BtpState *v=malloc(sizeof *v);CHECK(v);*v=*a;
    same_record(v->campaign.mech,b->campaign.mech,base,imported);
    same_record(v->campaign.checkpoint_mech,b->campaign.checkpoint_mech,base,imported);
    for(unsigned i=0;i<3;++i) {
        same_record(v->party.mechs[i],b->party.mechs[i],base,imported);
        same_record(v->party_checkpoint.mechs[i],b->party_checkpoint.mechs[i],base,imported);
    }
    for(unsigned i=0;i<4;++i)same_record(v->yard.mechs[i],b->yard.mechs[i],base,imported);
    for(unsigned i=0;i<BTP_COMBAT_UNITS;++i)if(!v->combat.unit[i].infantry && !b->combat.unit[i].infantry)
        same_record(v->combat.unit[i].record,b->combat.unit[i].record,base,imported);
    equal(v,b);free(v);
}
static unsigned route(const char *file,const BtpResources *base,const BtpResources *imported,int enhanced)
{
    BtpState *a=calloc(1,sizeof *a),*b=calloc(1,sizeof *b);CHECK(a && b);
    btp_start(a);btp_start(b);b->project=1;btp_npc_init(a,&base->map);btp_npc_init(b,&imported->map);
    if (btp_resources_feature(base,BTP_FEATURE_ENHANCED)) CHECK(btp_set_combat_profile(a,base,1) && btp_set_combat_profile(b,imported,1));
    uint32_t *x=malloc(320u*200u*sizeof *x),*y=malloc(320u*200u*sizeof *y);CHECK(x && y);
    FILE *f=fopen(file,"r");CHECK(f);char line[128];unsigned ticks=0,held=0;
    uint8_t checkpoints[512]={0};unsigned resumed=0;
    equal(a,b);
    while (fgets(line,sizeof line,f)) {
        line[strcspn(line,"\r\n")]=0;if (!*line || *line=='#') continue;
        BtpAction action;CHECK(btp_action_parse(line,&action));
        btp_game_tick(a,base,action);btp_game_tick(b,imported,action);++ticks;
        if(enhanced)CHECK(a->combat_profile==1 && b->combat_profile==1);
        same_route_state(a,b,base,imported);CHECK(!b->script.error);
        unsigned checkpoint=b->combat.phase ? b->mission.assignment*32u+b->combat.phase :
            b->cache.active ? 256u+b->cache.phase : 384u+b->mode;
        CHECK(checkpoint<512);
        if ((!held && (b->script.status==BTP_SCRIPT_WAIT || b->script.status==BTP_SCRIPT_MENU)) ||
            (enhanced && !checkpoints[checkpoint])) {
            BtpState *restored=calloc(1,sizeof *restored);CHECK(restored);
            CHECK(btp_save_write("chi-held-test.btp",b,imported,&error));
            CHECK(btp_save_load("chi-held-test.btp",restored,imported,&error));equal(b,restored);
            /* Continue the actual route from each decoded Enhanced boundary,
               rather than only checking a throwaway initial-menu round trip. */
            if(enhanced) { *b=*restored;checkpoints[checkpoint]=1;++resumed; }
            CHECK(!remove("chi-held-test.btp"));free(restored);held=1;
        }
        if (ticks%64u==0 || b->script.status==BTP_SCRIPT_MENU || b->script.status==BTP_SCRIPT_WAIT) {
            btp_render(base,a,0,x);btp_render(imported,b,0,y);
            if (memcmp(x,y,320u*200u*sizeof *x)) {
                fprintf(stderr,"Render mismatch at tick %u map %u, local %u,%u, mission %u: %s\n",ticks,b->map_id,b->x_half,b->y_half,b->mission.phase,file);
                btp_write_ppm("work/chi-import/c3-parity-base.ppm",x);btp_write_ppm("work/chi-import/c3-parity-import.ppm",y);
            }
            CHECK(!memcmp(x,y,320u*200u*sizeof *x));
        }
        CHECK(ticks<120000);
    }
    CHECK(!fclose(f));CHECK(ticks);printf("Verified %u identical gameplay ticks and presentation checkpoints: %s\n",ticks,file);
    if(enhanced)printf("Enhanced remained selected after every input; resumed %u distinct held contexts.\n",resumed);
    unsigned mode=b->mode;free(a);free(b);free(x);free(y);return mode;
}
int main(int argc,char **argv)
{
    if (argc==9 && (!strcmp(argv[1],"--updated-route") || !strcmp(argv[1],"--enhanced-route"))) {
        BtpContent base={0},project={0};BtpOriginalContentPaths paths={argv[3],argv[4],argv[5],argv[6]};
        CHECK(btp_content_load_original(&base,&paths,&error));
        CHECK(btp_content_select(&base,BTP_CONTENT_UPDATED,argv[7],&error));
        CHECK(btp_content_load_project(&project,argv[2],NULL,&error));
        CHECK(route(argv[8],base.resources,project.resources,!strcmp(argv[1],"--enhanced-route"))==BTP_ENDING);
        btp_content_close(&base);btp_content_close(&project);puts("Updated route reaches its ending with identical built-in/imported state and rendered checkpoints.");return 0;
    }
    if(argc==4 && !strcmp(argv[1],"--party-proof")) {
        BtpContent content={0};CHECK(btp_content_load_project(&content,argv[2],NULL,&error));const BtpResources *r=content.resources;
        BtpState *s=calloc(1,sizeof *s),*copy=calloc(1,sizeof *copy);CHECK(s && copy);
        /* Declared post-training crew checkpoint, independent of the complete
           input-only route. Exercise a real imported Updated unit as a player. */
        btp_start_content(s,r);s->project=1;s->story_flags[4]=1;s->story_flags[36]=127;
        s->map_id=0;s->x_half=s->campaign.world_x=1300;s->y_half=s->campaign.world_y=1000;
        btp_npc_enter(s,&r->map);btp_party_init(s);
        CHECK(btp_party_recruit_resources(s,r,5)==2 && btp_party_recruit_resources(s,r,6)==3);
        for(unsigned i=0;i<2;++i) {
            uint8_t *m=btp_party_mech(s,i);memcpy(m,r->roster.count ? r->roster.mechs[i].record : r->combat.loans[i],125);
            s->party.mech_types[i]=m[0];m[121]=m[122]=255;s->party.people[i][8]=1;btp_party_allocate(s,i,i,121);
        }
        s->campaign.owned=1;s->story_flags[24]=1;s->skills[0]=s->party.people[0][4];s->mech_skills[1]=1;
        if(btp_resources_feature(r,BTP_FEATURE_ENHANCED))CHECK(btp_set_combat_profile(s,r,1));
        btp_party_recover(s,r,1);btp_world_reveal(s);CHECK(btp_party_count(&s->party)==3);
        for(unsigned i=0;i<8;++i)btp_game_tick(s,r,i&1u ? BTP_RIGHT : BTP_LEFT);
        CHECK(s->mode==BTP_EXPLORE && s->party.people[0][12]==0 && s->party.people[1][12]==1);
        CHECK(btp_save_write(argv[3],s,r,&error) && btp_save_load(argv[3],copy,r,&error));equal(s,copy);
        CHECK(btp_campaign_random(s,r) && s->combat.friends==3 && !s->combat.unit[0].infantry && !s->combat.unit[1].infantry && s->combat.unit[2].infantry);
        if(r->roster.count)CHECK(btp_roster_custom(s->combat.unit[0].record));
        CHECK(btp_save_write(argv[3],s,r,&error) && btp_save_load(argv[3],copy,r,&error));equal(s,copy);
        uint32_t *frame=malloc(BTP_PIXELS*sizeof *frame),*other=malloc(BTP_PIXELS*sizeof *other);CHECK(frame && other);
        btp_render(r,s,0,frame);btp_render(r,copy,0,other);CHECK(!memcmp(frame,other,BTP_PIXELS*sizeof *frame));
        free(frame);free(other);free(s);free(copy);btp_content_close(&content);
        puts("Prepared three-person/two-mech imported crew walks, retains assignments, enters a correctly typed force and reloads matching state/pixels; Updated uses its added player units.");return 0;
    }
    if (argc==4 && !strcmp(argv[1],"--settings-proof")) {
        BtpContent content={0};CHECK(btp_content_load_project(&content,argv[2],NULL,&error));
        BtpState *s=calloc(1,sizeof *s),*copy=calloc(1,sizeof *copy);CHECK(s && copy);
        btp_start(s);s->project=1;btp_npc_init(s,&content.resources->map);
        CHECK(btp_set_combat_profile(s,content.resources,1));
        btp_menu_open(s);btp_menu_input(s,content.resources,BTP_DOWN);btp_menu_input(s,content.resources,BTP_ACCEPT);
        CHECK(s->campaign.ui==BTP_MENU_UPDATED_SETTINGS);
        CHECK(btp_save_write(argv[3],s,content.resources,&error));
        CHECK(btp_save_load(argv[3],copy,content.resources,&error));equal(s,copy);
        btp_content_close(&content);free(s);free(copy);puts("Explicit Updated settings save independently of added roster size.");return 0;
    }
    if ((argc==5 || argc==6) && !strcmp(argv[1],"--text-proof")) {
        BtpContent a={0},b={0};CHECK(btp_content_load_project(&a,argv[2],NULL,&error));
        CHECK(btp_content_load_project(&b,argv[3],NULL,&error));
        CHECK(!memcmp(a.resources->dialogue.font,b.resources->dialogue.font,sizeof a.resources->dialogue.font));
        if (argc==6) {
            const BtpDialogue *d=&b.resources->dialogue;CHECK(strlen(argv[5])==2u*d->size[87]);
            for (unsigned i=0;i<d->size[87];++i) {
                char hex[3];snprintf(hex,sizeof hex,"%02x",d->bytes[d->offset[87]+i]);
                CHECK(!memcmp(hex,argv[5]+2u*i,2));
            }
        }
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
        intro(base.resources,imported.resources);
        for (int i=8;i<argc;++i) route(argv[i],base.resources,imported.resources,0);
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
