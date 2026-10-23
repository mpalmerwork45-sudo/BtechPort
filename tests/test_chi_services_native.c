/* Private imported-project proofs. No original text/assets are embedded. */
#include "data/content.h"
#include "data/project.h"
#include "data/save.h"
#include "core/party.h"
#include "core/npc.h"
#include "core/school.h"
#include "core/service.h"
#include "core/story.h"
#include "core/roster_game.h"
#include "core/menu.h"
#include "core/events.h"
#include "core/combat.h"
#include "core/world.h"
#include "core/yard.h"
#include "frontend/pixels.h"
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
static BtpError error;
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"Native services line %d: %s (%s)\n",__LINE__,#x,error.text);exit(1); } } while (0)
static void held(BtpState *s,const BtpResources *r,const char *path)
{
    BtpState *copy=calloc(1,sizeof *copy);CHECK(copy);CHECK(btp_save_write(path,s,r,&error));CHECK(btp_save_load(path,copy,r,&error));
    uint8_t a[BTP_STATE_BYTES],b[BTP_STATE_BYTES];btp_state_encode(s,a);btp_state_encode(copy,b);CHECK(!memcmp(a,b,sizeof a));*s=*copy;free(copy);
}
int main(int argc,char **argv)
{
    CHECK(argc>=4);BtpContent content={0};CHECK(btp_content_load_project(&content,argv[2],NULL,&error));const BtpResources *r=content.resources;
    BtpState *s=calloc(1,sizeof *s);CHECK(s);btp_start_content(s,r);s->project=1;btp_npc_init(s,&r->map);
    if (btp_resources_feature(r,BTP_FEATURE_ENHANCED)) CHECK(btp_set_combat_profile(s,r,1));
    if (!strcmp(argv[1],"--mechanics")) {
        btp_party_init(s);s->credits=20;s->campaign.mech[0]='L';s->campaign.mech[17]=0;s->campaign.mech[86]=10;
        unsigned cost=btp_chi_service(r,BTP_SVC_REPAIR_ARMOUR);CHECK(cost>0 && cost<20);
        unsigned n=btp_mech_repair_resources(s,r,0,0,0);CHECK(n==20u/cost && s->credits==20u%cost);
        /* Run the existing hospital native action twice at its held page. The
           second call must leave both the paid balance and healed HP intact. */
        s->map_id=0;s->campaign.building=9;s->story_flags[4]=1;s->story_flags[26]=1;s->credits=1000;s->story_flags[41]=0;
        s->party.people[0][15]=1;s->script.native_action=24;
        CHECK(btp_later_native(s,r));CHECK(s->service.phase==12 && s->credits==1000u-r->combat.medical_prices[1]);
        unsigned hp=s->party.people[0][15];CHECK(hp>1 && s->story_flags[41]==btp_chi_service(r,BTP_SVC_MEDICAL_COOLDOWN));
        CHECK(btp_later_native(s,r));CHECK(s->party.people[0][15]==hp && s->credits==1000u-r->combat.medical_prices[1]);
        s->service=(BtpServiceState){0};CHECK(btp_party_recruit_resources(s,r,5)==2);CHECK(s->party.people[1][9]==btp_chi_service(r,BTP_SVC_RECRUIT_RANK));
        CHECK(!btp_party_recruit_resources(s,r,6));
        /* A declared no-encounter fixture checks the post-invasion market
           caller as well as the cadet caller. Company zero is configured with
           mask zero/rate 100 in this proof: 1000 * 100 / 110 = 909. */
        s->story_flags[58]=1;s->story_flags[23]=0;s->investments[0]=1000;s->campaign.world_clock=0;
        btp_world_clock(s,r,BTP_RIGHT);CHECK(s->investments[0]==909);
        if (btp_resources_feature(r,BTP_FEATURE_BROKER)) {
            s->mode=BTP_ACTIONS;s->map_id=2;s->campaign.ui=BTP_MENU_BROKER;s->campaign.building=BTP_BROKER_BUILDING;s->entry_slot=BTP_BROKER_ENTRY;
            s->combat.phase=0;s->campaign.encounter=0;s->cache.active=0;s->yard.active=0;
            for (unsigned i=0;i<r->roster.count;++i) if (!btp_chi_broker_stock(r,i)) CHECK(btp_broker_buy(s,r,i)==BTP_BROKER_UNAVAILABLE);
            unsigned indices[256],count=btp_events_catalogue(s,r,0,r->roster.count,indices);
            for (unsigned i=0;i<count;++i) CHECK(btp_chi_broker_stock(r,indices[i]));
        }
        puts("Edited repair/healing costs and cooldown, recruitment limits/ranks and broker stock reach native mechanics; healing charges once.");
    } else if (!strcmp(argv[1],"--prison")) {
        CHECK(argc==4);btp_party_init(s);s->story_flags[58]=1;
        unsigned slot=1,door=0;
        for (;slot<10;++slot) {
            const BtpMap *m=&r->local[slot];door=0;while (door<8 && m->room_map[door]!=13) ++door;if (door<8) break;
        }
        CHECK(slot<10);const BtpMap *m=&r->local[slot];unsigned x=m->entrance_x[door]&127u,y=m->entrance_y[door]&127u;
        CHECK(x && btp_chi_preview(s,r,r->project->chi_spatial->maps[slot].id,x-1,y));
        btp_game_tick(s,r,BTP_RIGHT);CHECK(s->mode==BTP_ENTRY);btp_game_tick(s,r,BTP_ACCEPT);CHECK(s->mode==BTP_YARD);
        BtpState *entry=malloc(sizeof *entry);CHECK(entry);*entry=*s;
        for (unsigned i=0;i<85;++i) btp_game_tick(s,r,BTP_RIGHT);
        CHECK(s->mode==BTP_YARD && s->yard.timer==85 && !btp_yard_valid(s));held(s,r,argv[3]);
        /* Start the second declared branch from the captured entry state. */
        *s=*entry;free(entry);
        for (unsigned i=0;i<4;++i) btp_game_tick(s,r,BTP_RIGHT);
        for (unsigned i=0;i<9;++i) btp_game_tick(s,r,BTP_DOWN);
        CHECK(s->yard.phase==BTP_YARD_CLIMB);btp_game_tick(s,r,BTP_ACCEPT);btp_game_tick(s,r,BTP_ACCEPT);
        CHECK(s->yard.phase==BTP_YARD_FOUND && s->yard.attempts==1);
        for (unsigned i=0;i<4000 && (s->cutscene.active || s->audio.sound_count);++i) btp_game_tick(s,r,BTP_IDLE);
        CHECK(!s->cutscene.active && !s->audio.sound_count);btp_game_tick(s,r,BTP_ACCEPT);
        CHECK(!s->yard.active && s->campaign.owned && s->script.status==BTP_SCRIPT_WAIT);
        CHECK(s->campaign.mech[0]==r->combat.encounter_mechs[btp_chi_service(r,BTP_SVC_PRISON_REWARD)][0]);
        btp_game_tick(s,r,BTP_ACCEPT);CHECK(s->mode==BTP_EXPLORE && s->story_flags[81]==44 && !s->script.error);
        puts("Edited prison timer reloads beyond the original 80-tick bound; first-attempt theft grants the configured mech and resumes its BLD.");
    } else if (!strcmp(argv[1],"--healing")) {
        CHECK(argc==4);btp_party_init(s);s->credits=1000;s->party.people[0][15]=1;s->story_flags[4]=1;
        s->story_flags[58]=1; /* Native encounter suppression for this doorway fixture. */
        unsigned slot=1,door=0;
        for (;slot<14;++slot) {
            const BtpMap *m=&r->local[slot];door=0;while (door<8 && m->room_map[door]!=9) ++door;
            if (door<8) break;
        }
        CHECK(slot<14);const BtpMap *m=&r->local[slot];unsigned x=m->entrance_x[door]&127u,y=m->entrance_y[door]&127u;
        CHECK(x && btp_chi_preview(s,r,r->project->chi_spatial->maps[slot].id,x-1,y));
        btp_game_tick(s,r,BTP_RIGHT);
        if (s->mode!=BTP_ENTRY) fprintf(stderr,"Hospital map %u, door %u [%u,%u]: mode %u, map %u, at [%u,%u], blocked %u, member [%u,%u]\n",slot+1,door,x,y,s->mode,s->map_id,s->x_half,s->y_half,s->blocked,s->party.people[0][0],s->party.people[0][12]);
        CHECK(s->mode==BTP_ENTRY);btp_game_tick(s,r,BTP_ACCEPT);
        CHECK(s->service.phase==12 && s->script.native_action==24 && s->credits==1000u-r->combat.medical_prices[1]);
        unsigned hp=s->party.people[0][15];CHECK(hp>1 && s->story_flags[41]==btp_chi_service(r,BTP_SVC_MEDICAL_COOLDOWN));
        held(s,r,argv[3]);btp_game_tick(s,r,BTP_ACCEPT);CHECK(!s->service.phase && s->script.status==BTP_SCRIPT_WAIT);
        held(s,r,argv[3]);CHECK(s->credits==1000u-r->combat.medical_prices[1] && s->party.people[0][15]==hp);
        btp_game_tick(s,r,BTP_ACCEPT);CHECK(s->mode==BTP_EXPLORE && s->story_flags[81]==43 && !s->script.error);
        puts("Edited hospital price and cooldown run through a real doorway and two held continuations without repeated charges or healing.");
    } else if (!strcmp(argv[1],"--purchase")) {
        CHECK(argc==4);btp_party_init(s);CHECK(btp_party_recruit_resources(s,r,5)==2);s->credits=1000;
        unsigned door=0;while (door<16 && r->map.room_map[door]!=4) ++door;CHECK(door<16);
        unsigned x=r->map.entrance_x[door]&127u,y=r->map.entrance_y[door]&127u;
        CHECK(btp_chi_preview(s,r,r->project->chi_spatial->maps[0].id,x-1,y));btp_game_tick(s,r,BTP_RIGHT);CHECK(s->mode==BTP_ENTRY);
        btp_game_tick(s,r,BTP_ACCEPT);CHECK(s->script.status==BTP_SCRIPT_MENU && s->script.menu_id==13);
        btp_game_tick(s,r,BTP_DOWN);btp_game_tick(s,r,BTP_ACCEPT);
        CHECK(s->service.phase==10 && s->service.action==9 && s->credits==1000u-btp_chi_service(r,BTP_SVC_ARMOUR_PRICE_1));
        held(s,r,argv[3]);btp_game_tick(s,r,BTP_DOWN);btp_game_tick(s,r,BTP_ACCEPT);
        CHECK(!s->service.phase && s->script.status==BTP_SCRIPT_WAIT && s->party.people[1][13]==1 && s->party.people[1][14]==25 && !s->armor);
        CHECK(s->credits==1000u-btp_chi_service(r,BTP_SVC_ARMOUR_PRICE_1));held(s,r,argv[3]);
        btp_game_tick(s,r,BTP_ACCEPT);CHECK(s->mode==BTP_EXPLORE && !s->script.error && s->story_flags[81]==42);
        uint32_t *frame=malloc(64000u*sizeof *frame);CHECK(frame);btp_render(r,s,0,frame);free(frame);
        puts("Edited price charges once through real building entry, recipient selection and reloaded native continuations.");
    } else {
        CHECK(argc==5 && !strcmp(argv[1],"--route"));FILE *f=fopen(argv[3],"r");CHECK(f);char line[128];unsigned ticks=0,holds=0;
        while (fgets(line,sizeof line,f)) {
            line[strcspn(line,"\r\n")]=0;if (!*line || *line=='#') continue;BtpAction action;CHECK(btp_action_parse(line,&action));btp_game_tick(s,r,action);++ticks;
            CHECK(!s->script.error);
            unsigned bit=s->school.phase ? 1u<<s->school.phase : s->service.phase ? 1u<<(3u+s->service.phase) : 0u;
            if (bit && !(holds&bit)) { held(s,r,argv[4]);holds|=bit; }
            CHECK(ticks<120000);
        }
        CHECK(!fclose(f) && holds);printf("Verified %u edited-service route ticks with held native service/class continuations.\n",ticks);
    }
    free(s);btp_content_close(&content);return 0;
}
