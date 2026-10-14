#include "core/yard.h"
#include "core/campaign.h"
#include "core/combat.h"
#include "core/party.h"
#include "frontend/pixels.h"
#include "data/save.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>

static unsigned checks;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x);exit(1); } } while (0)
static uint64_t result_hash(const uint32_t *frame)
{
    uint64_t value=UINT64_C(14695981039346656037);
    for (unsigned y=72;y<128;++y) for (unsigned x=104;x<320;++x) for (int shift=16;shift>=0;shift-=8)
        value=(value^(uint8_t)(frame[y*320+x]>>shift))*UINT64_C(1099511628211);
    return value;
}
static void input(BtpState *s,const BtpResources *r,BtpAction action)
{
    uint8_t a[BTP_STATE_BYTES],b[BTP_STATE_BYTES];BtpState copy;btp_state_encode(s,a);
    if (!btp_state_decode(a,sizeof a,btp_active_map(r,s),btp_state_bld(r,s),&copy)) {
        fprintf(stderr,"Arena restore: tick=%u mode=%u phase=%u after=%u script=%u/%u yard=%u combat-valid=%d\n",
            s->tick,s->mode,s->combat.phase,s->aftermath.phase,s->script.status,s->script.pc,s->yard.phase,btp_combat_valid(s));CHECK(0);
    }
    btp_game_tick(s,r,action);btp_game_tick(&copy,r,action);btp_state_encode(s,a);btp_state_encode(&copy,b);CHECK(!memcmp(a,b,sizeof a));
}
int main(int argc,char **argv)
{
    if (argc!=2) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError e;
    CHECK(r && btp_resources_load(argv[1],r,&e));CHECK(btp_combat_data_load("work/combat-data.bin",&r->combat,&e));
    CHECK(btp_dialogue_load("work/talk-data.bin",&r->dialogue,&e));CHECK(btp_world_data_load("work/world-data.bin",&r->world,&e));
    uint64_t original[2]={0};FILE *panels=fopen("tests/fixtures/arena-ui-primary.txt","r");CHECK(panels);
    unsigned win;uint64_t expected;unsigned crops=0;
    while (fscanf(panels," A %u %" SCNx64,&win,&expected)==2) { CHECK(win<2);original[win]=expected;++crops; }
    fclose(panels);CHECK(crops==2 && original[0] && original[1]);
    const char *names[]={"arena-owned-loss","arena-owned-win","arena-rental-loss","arena-rental-win","prison-loss"};
    BtpState rental_start={0},rental_win={0};
    for (unsigned route=0;route<5;++route) {
        BtpState s;if (route==4) btp_start(&s);else CHECK(btp_save_load("Original DOS/GAME3",&s,r,&e));
        char path[180],line[80];snprintf(path,sizeof path,"tests/fixtures/ordinary-%s.actions",names[route]);
        FILE *f=fopen(path,"r");CHECK(f);unsigned ticks=0,held=0,waiver=0;uint32_t cash=0;
        uint8_t before_types[4]={0};
        while (fgets(line,sizeof line,f)) {
            line[strcspn(line,"\r\n")]=0;BtpAction action;CHECK(btp_action_parse(line,&action));input(&s,r,action);++ticks;
            if (route<4 && s.combat.phase==BTP_COMBAT_CONTROL) {
                cash=s.credits;memcpy(before_types,s.yard.types,4);if (route==3 && !rental_start.yard.active) rental_start=s;
            }
            if (s.mode==BTP_BUILDING && s.yard.phase==BTP_YARD_LOAN && s.script.status==BTP_SCRIPT_WAIT) waiver=1;
            if (s.aftermath.phase==11) {
                if (!held) {
                    uint32_t frame[BTP_PIXELS];btp_render(r,&s,0,frame);
                    if (result_hash(frame)!=original[route&1u]) {
                        fprintf(stderr,"Arena result %u: %016" PRIx64 " != %016" PRIx64 "\n",route,result_hash(frame),original[route&1u]);
                        CHECK(btp_write_ppm("work/arena-result-failed.ppm",frame));
                    }
                    CHECK(result_hash(frame)==original[route&1u]);
                }
                held=1;CHECK(s.credits==cash && s.story_flags[33]==(route&1u));
                CHECK(s.party.people[0][0]!=255 && !s.story_flags[40]);
                if (route==3) {
                    rental_win=s;unsigned target=btp_combat_target(&s.combat,13);CHECK(target<s.combat.count);
                    CHECK(s.combat.unit[target].record[0]==255 && !s.aftermath.wrecks[13] && !s.story_flags[35]);
                }
            }
        }
        fclose(f);
        if (route==4) { CHECK(s.mode==BTP_GAME_OVER && s.story_flags[40] && !s.yard.active);continue; }
        CHECK(ticks>1000 && held && s.mode==BTP_EXPLORE && !s.yard.active && !s.campaign.encounter);
        CHECK(s.party.people[0][0]!=255 && !s.story_flags[40]);CHECK(s.credits==cash+((route&1u) ? 500u : 0u));
        CHECK(s.campaign.world_x==1337 && s.campaign.world_y==1117);
        for (unsigned i=0;i<4;++i) {
            CHECK(s.party.mech_types[i]==(!route && !i ? 255 : before_types[i]));
            CHECK(btp_party_mech(&s,i)[0]==255);
        }
        uint16_t parked_x[4],parked_y[4];memcpy(parked_x,s.party.mech_x,sizeof parked_x);memcpy(parked_y,s.party.mech_y,sizeof parked_y);
        input(&s,r,BTP_DOWN);
        CHECK(!memcmp(parked_x,s.party.mech_x,sizeof parked_x) && !memcmp(parked_y,s.party.mech_y,sizeof parked_y));
        if (route==3) {
            /* Reproduce a pre-fix save after the arena mistakenly checked
               the parked records out. Loading repairs their active bytes
               without losing ownership, damage or the retained crew seats. */
            BtpState old=s,loaded;
            for (unsigned i=0;i<4;++i) btp_party_mech(&old,i)[0]=old.party.mech_types[i];
            CHECK(btp_save_write("work/m4-audit/arena-old-parking.btp",&old,r,&e));
            CHECK(btp_save_load("work/m4-audit/arena-old-parking.btp",&loaded,r,&e));
            for (unsigned i=0;i<4;++i) {
                CHECK(btp_party_mech(&loaded,i)[0]==255 && loaded.party.mech_types[i]==s.party.mech_types[i]);
                CHECK(!memcmp(btp_party_mech(&loaded,i)+1,btp_party_mech(&s,i)+1,124));
            }
            input(&loaded,r,BTP_DOWN);
            CHECK(!memcmp(parked_x,loaded.party.mech_x,sizeof parked_x) && !memcmp(parked_y,loaded.party.mech_y,sizeof parked_y));
        }
        if (route<2) CHECK(waiver);
        /* Inputs and saves remain responsive after the cashier's result. */
        input(&s,r,BTP_OPEN_MENU);CHECK(s.mode==BTP_ACTIONS);input(&s,r,BTP_CANCEL);CHECK(s.mode==BTP_EXPLORE);
    }
    CHECK(rental_start.yard.active && rental_win.aftermath.phase==11);
    /* Reconstruct the old stuck victory, including its still-live spectator.
       The next ordinary idle repairs it, and the award occurs exactly once. */
    BtpState stuck=rental_win;stuck.aftermath.applied=stuck.aftermath.phase=0;stuck.combat.phase=BTP_COMBAT_MENU;stuck.combat.won=0;
    unsigned spectator=btp_combat_target(&stuck.combat,13);memcpy(stuck.combat.unit[spectator].record,r->combat.arena_spectator,125);
    input(&stuck,r,BTP_IDLE);CHECK(stuck.aftermath.phase==11 && stuck.combat.won);
    uint32_t cash=stuck.credits;input(&stuck,r,BTP_OPEN_MENU);CHECK(stuck.credits==cash+500 && stuck.script.status==BTP_SCRIPT_WAIT);
    input(&stuck,r,BTP_IDLE);CHECK(stuck.credits==cash+500);input(&stuck,r,BTP_ACCEPT);CHECK(stuck.mode==BTP_EXPLORE);
    FILE *f=fopen("tests/fixtures/arena-finish-primary.txt","r");CHECK(f);char line[160];unsigned cases=0;
    while (fgets(line,sizeof line,f)) {
        BtpState s=rental_start;BtpCombatState *c=&s.combat;
        if (line[0]=='D') {
            unsigned rental,alarm,target,want[3];CHECK(sscanf(line,"D %u %u %u %u %u %u",&rental,&alarm,&target,&want[0],&want[1],&want[2])==6);
            s.yard.rental=(uint8_t)rental;s.story_flags[35]=(uint8_t)alarm;
            for (unsigned i=0;i<3;++i) memcpy(c->unit[i].record,r->combat.loans[0],125);
            btp_campaign_destroy(&s,btp_combat_target(c,target));
            for (unsigned i=0;i<3;++i) CHECK(c->unit[i].record[0]==want[i]);
        } else {
            unsigned alarm,standing[3],ended;CHECK(sscanf(line,"E %u %u %u %u %u",&alarm,&standing[0],&standing[1],&standing[2],&ended)==5);
            s.story_flags[35]=(uint8_t)alarm;c->phase=BTP_COMBAT_ROUND;c->step=12;
            for (unsigned i=0;i<3;++i) if (!standing[i]) c->unit[i].record[0]=255;
            btp_combat_tick(&s,r,BTP_IDLE);CHECK((c->phase==BTP_COMBAT_NONE)==(ended!=0));
        }
        ++cases;
    }
    fclose(f);CHECK(cases==28);free(r);
    printf("PASS: %u arena checks, two original result crops, 28 termination cases, four arena journeys and prison loss\n",checks);return 0;
}
