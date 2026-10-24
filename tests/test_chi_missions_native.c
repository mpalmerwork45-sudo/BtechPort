/* Private imported-project journeys. Fixture source belongs in ignored work/.
   Later-system checkpoints below are declared explicitly, never presented as
   input-only playthroughs from the game's beginning. */
#include "data/content.h"
#include "data/project.h"
#include "data/save.h"
#include "core/party.h"
#include "core/npc.h"
#include "core/combat.h"
#include "core/training.h"
#include "core/campaign.h"
#include "core/world.h"
#include "core/yard.h"
#include "core/cache.h"
#include "frontend/pixels.h"
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
static BtpError error;
static unsigned ticks,holds;
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"Mission proof line %d: %s (%s)\n",__LINE__,#x,error.text);exit(1); } } while (0)
static void tick(BtpState *s,const BtpResources *r,BtpAction a)
{ btp_game_tick(s,r,a);++ticks;CHECK(!s->script.error && s->mode!=BTP_SCRIPT_FAULT && ticks<100000); }
static void held(BtpState *s,const BtpResources *r,const char *path)
{
    BtpState *copy=calloc(1,sizeof *copy);CHECK(copy);
    if (!btp_save_write(path,s,r,&error) || !btp_save_load(path,copy,r,&error)) {
        fprintf(stderr,"held %u mode %u mission %u assignment %u combat %u count %u flags %u,%u,%u gate %u; training/combat validators %d/%d\n",holds,s->mode,s->mission.phase,s->mission.assignment,s->combat.phase,s->combat.count,s->story_flags[62],s->story_flags[64],s->story_flags[65],s->gate,btp_training_valid_resources(s,r),btp_combat_valid_resources(s,r));CHECK(0);
    }
    uint8_t a[BTP_STATE_BYTES],b[BTP_STATE_BYTES];btp_state_encode(s,a);btp_state_encode(copy,b);CHECK(!memcmp(a,b,sizeof a));*s=*copy;free(copy);
    uint32_t *frame=malloc(BTP_PIXELS*sizeof *frame);CHECK(frame);btp_render(r,s,0,frame);free(frame);++holds;
}
static void drain(BtpState *s,const BtpResources *r)
{ for (unsigned i=0;i<10000 && (s->cutscene.active || s->audio.sound_count);++i) tick(s,r,BTP_IDLE);CHECK(!s->cutscene.active && !s->audio.sound_count); }
static void entry(BtpState *s,const BtpResources *r,unsigned building)
{
    unsigned map=0,door=0;
    for (;map<13;++map) {
        const BtpMap *m=map ? &r->local[map] : &r->map;
        for (door=0;door<16;++door) if (m->room_map[door]==building && m->entrance_x[door]) break;
        if (door<16) break;
    }
    CHECK(map<13);const BtpMap *m=map ? &r->local[map] : &r->map;
    unsigned x=m->entrance_x[door]&127u,y=m->entrance_y[door]&127u;CHECK(x);
    s->story_flags[58]=1; /* Suppress unrelated random encounters in this declared doorway fixture. */
    if (!building) s->story_flags[20]=1; /* Recognition has its own proof below. */
    /* Keep the live cadet NPCs for the ruin-transition/save proof. Later
       locations use the editor's declared map checkpoint mechanism. */
    if (!map) { s->x_half=(uint16_t)(x-1);s->y_half=(uint16_t)y; }
    else CHECK(btp_chi_preview(s,r,r->project->chi_spatial->maps[map].id,x-1,y));
    tick(s,r,BTP_RIGHT);CHECK(s->mode==BTP_ENTRY);tick(s,r,BTP_ACCEPT);
    /* Training creates its rollback snapshot on the original Yes/No path. */
    if (!building && s->script.status==BTP_SCRIPT_CONFIRM) tick(s,r,BTP_ACCEPT);
}
static void options(BtpState *s,const BtpResources *r)
{
    drain(s,r);
    if (s->combat.phase==BTP_COMBAT_CONTROL) tick(s,r,BTP_ACCEPT); /* No computer, native default. */
    CHECK(s->combat.phase==BTP_COMBAT_MESSAGES);tick(s,r,BTP_ACCEPT);
    CHECK(s->combat.phase==BTP_COMBAT_GRAPHICS);tick(s,r,BTP_ACCEPT);
}
static void command(BtpState *s,const BtpResources *r,unsigned choice)
{
    CHECK(s->combat.phase==BTP_COMBAT_MENU);
    for (unsigned i=0;s->combat.selected!=choice && i<12;++i) tick(s,r,BTP_DOWN);
    CHECK(s->combat.selected==choice);tick(s,r,BTP_ACCEPT);
}
int main(int argc,char **argv)
{
    CHECK(argc==4);BtpContent content={0};CHECK(btp_content_load_project(&content,argv[2],NULL,&error));const BtpResources *r=content.resources;
    BtpState *s=calloc(1,sizeof *s);CHECK(s);btp_start_content(s,r);s->project=1;btp_npc_init(s,&r->map);
    if (btp_resources_feature(r,BTP_FEATURE_ENHANCED)) CHECK(btp_set_combat_profile(s,r,1));
    if (!strcmp(argv[1],"--start")) {
        CHECK(s->credits==77 && s->allowance_cap==123 && s->party.people[0][1]==10 && s->party.people[0][10]==2);
        held(s,r,argv[3]);tick(s,r,BTP_RIGHT);held(s,r,argv[3]);
        puts("Edited starting funds, allowance, attributes and skills survive native exploration saves.");
    } else if (!strcmp(argv[1],"--training")) {
        entry(s,r,0);CHECK(s->mode==BTP_MISSION);drain(s,r);
        CHECK(s->mission.assignment==4 && s->combat.count==3 && s->combat.phase==BTP_COMBAT_CONTROL);
        CHECK(!memcmp(s->combat.unit[1].record,btp_chi_mission_unit(r,BTP_MUNIT_TRAINING_4_ENEMY_0),125));
        CHECK(!memcmp(s->combat.unit[2].record,btp_chi_mission_unit(r,BTP_MUNIT_TRAINING_4_ENEMY_1),125));
        CHECK(s->combat.unit[0].x==68);held(s,r,argv[3]);options(s,r);held(s,r,argv[3]);
        command(s,r,8);CHECK(s->combat.fled && s->mission.phase==BTP_MISSION_RETURN);held(s,r,argv[3]);
        uint8_t text[1024];size_t n;CHECK(btp_training_text(s,r,text,sizeof text,&n) && n && strstr((char *)text,"C4.3"));
        tick(s,r,BTP_ACCEPT);tick(s,r,BTP_IDLE);CHECK(s->mode==BTP_BUILDING && s->story_flags[1] && s->story_flags[81]==43);held(s,r,argv[3]);
        tick(s,r,BTP_ACCEPT);CHECK(s->mode==BTP_EXPLORE && !s->mission.phase);
        puts("Real training doorway, edited two-enemy force/roster role, manual-control prompt, retreat-as-pass, return text and BLD outcome resume pass.");
    } else if (!strcmp(argv[1],"--invasion")) {
        entry(s,r,0);drain(s,r);CHECK(s->campaign.invasion && s->combat.count==5);
        for (unsigned i=1;i<5;++i) CHECK(s->combat.unit[i].record[0]=='J');
        options(s,r);CHECK(s->combat.phase==BTP_COMBAT_STORY);held(s,r,argv[3]);tick(s,r,BTP_ACCEPT);
        command(s,r,9);
        for (unsigned i=0;i<8000 && s->combat.phase!=BTP_COMBAT_STORY;++i) tick(s,r,BTP_IDLE);
        CHECK(s->combat.phase==BTP_COMBAT_STORY && !s->late.invasion_event);tick(s,r,BTP_ACCEPT);
        CHECK(s->late.invasion_event==1 && btp_active_map(r,s)==&r->destroyed);held(s,r,argv[3]);
        command(s,r,0);tick(s,r,BTP_LEFT);tick(s,r,BTP_LEFT);tick(s,r,BTP_ACCEPT);command(s,r,9);
        for (unsigned i=0;i<12000 && !(s->mode==BTP_BUILDING && s->script.status==BTP_SCRIPT_WAIT);++i) {
            if (s->combat.phase==BTP_COMBAT_STORY) { drain(s,r);held(s,r,argv[3]);tick(s,r,BTP_ACCEPT); }
            else tick(s,r,BTP_IDLE);
        }
        CHECK(s->mode==BTP_BUILDING && s->story_flags[4] && s->combat.fled && s->story_flags[81]==43);held(s,r,argv[3]);
        tick(s,r,BTP_ACCEPT);CHECK(s->mode==BTP_EXPLORE && !s->campaign.invasion && s->campaign.owned);
        puts("Four Jenner invasion, changed ruined-map threshold, matching collision/rendering and physical escape drain story/animation before returning to exploration.");
    } else if (!strcmp(argv[1],"--quiz")) {
        s->x_half=(uint16_t)((r->map.entrance_x[0]&127u)-1);s->y_half=r->map.entrance_y[0]&127u;
        tick(s,r,BTP_RIGHT);tick(s,r,BTP_ACCEPT);CHECK(s->mode==BTP_QUIZ);tick(s,r,BTP_ACCEPT);
        for (unsigned round=0;round<4;++round) {
            CHECK(s->quiz.round==round);held(s,r,argv[3]);unsigned answer=btp_chi_mission(r,BTP_MIS_QUIZ_POINT_0_ANSWER+s->quiz.point*3u);
            for (unsigned i=0;s->quiz.selected!=answer && i<20;++i) tick(s,r,BTP_DOWN);
            tick(s,r,BTP_ACCEPT);
        }
        CHECK(!s->quiz.phase && s->script.status==BTP_SCRIPT_CONFIRM);held(s,r,argv[3]);
        puts("Edited four-question recognition test renders its configured markers/answers and resumes the original training dialogue with held saves.");
    } else if (!strcmp(argv[1],"--arena")) {
        entry(s,r,10);CHECK(s->yard.active==2 && s->script.status==BTP_SCRIPT_WAIT);held(s,r,argv[3]);
        tick(s,r,BTP_ACCEPT);drain(s,r);tick(s,r,BTP_IDLE);CHECK(s->campaign.encounter==4 && s->combat.count==3);
        CHECK(s->yard.variant==1 && s->yard.gate_count==7);
        CHECK(s->combat.unit[0].record[0]=='C' && s->combat.unit[2].x==72);held(s,r,argv[3]);options(s,r);
        /* Declare the spectator-hit boundary; this proof checks the actual
           native alarm/reinforcement and escape continuation, not accuracy RNG. */
        btp_yard_alarm(s,r,2);CHECK(s->combat.count==4 && s->story_flags[35]);
        for (unsigned i=0;i<3000 && s->combat.phase!=BTP_COMBAT_MENU;++i) tick(s,r,BTP_ACCEPT);
        held(s,r,argv[3]);command(s,r,9);
        for (unsigned i=0;i<12000 && !(s->mode==BTP_BUILDING && s->script.status==BTP_SCRIPT_WAIT);++i) {
            tick(s,r,s->combat.phase==BTP_COMBAT_NOTICE ? BTP_ACCEPT : BTP_IDLE);
        }
        CHECK(s->mode==BTP_BUILDING && !s->yard.active && s->story_flags[81]==44);held(s,r,argv[3]);tick(s,r,BTP_ACCEPT);
        CHECK(s->mode==BTP_EXPLORE && s->campaign.owned && s->party.mech_types[0]=='C');
        puts("Real arena doorway, changed rental/spectator and one guard, declared spectator-hit alarm, configured escape and stolen-loan BLD return pass.");
    } else if (!strcmp(argv[1],"--cache")) {
        entry(s,r,20);CHECK(s->cache.active && s->map_id==14);held(s,r,argv[3]);
        for (unsigned i=0;i<5000 && s->mode==BTP_BUILDING;++i) tick(s,r,BTP_ACCEPT);
        CHECK(s->mode==BTP_CACHE && s->x_half==8);held(s,r,argv[3]);
        /* Declared secret-open checkpoint checks the edited overlay origin. */
        s->cache.hall=1;CHECK(btp_cache_tile(r,s,10,30)==r->combat.cache_secret[0]);held(s,r,argv[3]);
        CHECK(btp_cache_terminal(s,r,r->combat.cache_tx[0]-1u,r->combat.cache_ty[0]));held(s,r,argv[3]);
        tick(s,r,BTP_ACCEPT);CHECK(s->story_flags[59+r->combat.cache_color[0]]==0);
        /* A declared cache checkpoint at the final door isolates changed
           prerequisites. Move into the door normally and run WINSCENE itself. */
        s->x_half=4;s->y_half=5;s->story_flags[62]=s->story_flags[64]=s->story_flags[65]=0;
        btp_cache_restore_party(s,r);tick(s,r,BTP_UP);
        CHECK(s->mode==BTP_BUILDING && s->campaign.building==25);held(s,r,argv[3]);
        for (unsigned i=0;i<20000 && s->mode!=BTP_ENDING;++i) tick(s,r,BTP_ACCEPT);
        CHECK(s->mode==BTP_ENDING && s->menu.quit);held(s,r,argv[3]);
        puts("Real cache entry, changed start/terminal and final-door prerequisites, original ending films/text and quit behavior reload without duplicate effects.");
    } else if (!strcmp(argv[1],"--encounter")) {
        btp_party_init(s);s->story_flags[4]=1;s->map_id=0;s->campaign.world_x=1300;s->campaign.world_y=1000;
        s->x_half=1300;s->y_half=1000;btp_npc_enter(s,&r->map);
        for (unsigned i=0;i<4;++i) { memcpy(btp_party_mech(s,i),r->combat.loans[0],125);s->party.mech_types[i]='L'; }
        s->campaign.owned=1;CHECK(btp_campaign_random(s,r));CHECK(s->combat.phase==BTP_COMBAT_OFFER);held(s,r,argv[3]);
        tick(s,r,BTP_DOWN);tick(s,r,BTP_ACCEPT);CHECK(s->combat.phase==BTP_COMBAT_AVOID);held(s,r,argv[3]);tick(s,r,BTP_ACCEPT);options(s,r);
        /* Declared victorious-outcome fixture with one defeated enemy person.
           Reward/aftercare/save sequencing is the behavior under test. */
        for (unsigned i=s->combat.friends;i<s->combat.count;++i) btp_campaign_destroy_resources(s,i,r);
        s->combat.phase=0;s->combat.won=1;s->effects=(BtpEffectsState){0};
        unsigned before=s->credits,seen=0;
        for (unsigned i=0;i<500 && s->mode==BTP_ENCOUNTER;++i) {
            tick(s,r,s->aftermath.phase==4 ? BTP_CANCEL : s->aftermath.phase ? BTP_ACCEPT : BTP_IDLE);
            unsigned phase=s->aftermath.phase;
            if (phase && !(seen&(1u<<phase))) {
                if (phase==3) CHECK(s->aftermath.cash>=40);
                held(s,r,argv[3]);seen|=1u<<phase;
            }
        }
        CHECK(s->mode==BTP_EXPLORE && s->credits>=before+40);unsigned paid=s->credits;held(s,r,argv[3]);tick(s,r,BTP_IDLE);CHECK(s->credits==paid);
        puts("Encounter offer/refusal with edited avoid mask; declared victory uses edited cash and disabled salvage/aftercare, with single-payment continuation.");
    } else CHECK(0);
    printf("Verified %u logical ticks and %u exact held save/render checkpoints.\n",ticks,holds);
    free(s);btp_content_close(&content);return 0;
}
