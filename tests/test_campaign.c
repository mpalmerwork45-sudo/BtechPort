#include "core/training.h"
#include "core/npc.h"
#include "core/world.h"
#include "data/save.h"
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x);return 1; } } while (0)
static uint64_t hash(const uint8_t *b,size_t n) {
    uint64_t h=UINT64_C(14695981039346656037);
    for (size_t i=0;i<n;++i) h=(h^b[i])*UINT64_C(1099511628211);
    return h;
}
int main(int argc,char **argv)
{
    if (argc!=3) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError e;CHECK(r);
    CHECK(btp_resources_load(argv[1],r,&e));
    CHECK(btp_combat_data_load("work/combat-data.bin",&r->combat,&e));
    CHECK(btp_dialogue_load("work/talk-data.bin",&r->dialogue,&e));
    CHECK(btp_world_data_load("work/world-data.bin",&r->world,&e));
    FILE *f=fopen("tests/fixtures/invasion-setup.txt","r");CHECK(f);char row[600];unsigned cases=0;
    while (fgets(row,sizeof row,f)) if (row[0]=='P') {
        unsigned assignment,seed,invasion,count,rng;int used;
        CHECK(sscanf(row+1,"%u %u %u %u %u%n",&assignment,&seed,&invasion,&count,&rng,&used)==5);
        BtpState s;btp_start(&s);s.story_flags[0]=(uint8_t)assignment;
        s.script=(BtpScriptState){.status=BTP_SCRIPT_NATIVE,.native_action=1};
        for (unsigned i=0;i<3;++i) s.npc.rng[i]=(uint8_t)(seed>>(8*i));
        btp_training_native(&s,r);
        CHECK(s.campaign.invasion==invasion && s.combat.count==count);
        CHECK((unsigned)s.npc.rng[0]+((unsigned)s.npc.rng[1]<<8)+((unsigned)s.npc.rng[2]<<16)==rng);
        char *at=row+1+used;
        for (unsigned i=1;i<count;++i) {
            unsigned x,y;uint64_t record;CHECK(sscanf(at,"%u %u %" SCNx64 "%n",&x,&y,&record,&used)==3);at+=used;
            CHECK(s.combat.unit[i].x==x && s.combat.unit[i].y==y);
            CHECK(hash(s.combat.unit[i].record,125)==record);
        }
        if (invasion) for (int y=62;y<64;++y) for (int x=56;x<64;++x)
            CHECK(btp_mission_tile(&s,&r->map,x,y)==64);
        ++cases;
    }
    fclose(f);CHECK(cases==16);
    BtpState s;btp_start(&s);f=fopen(argv[2],"r");CHECK(f);
    uint8_t saved[BTP_STATE_BYTES],again[BTP_STATE_BYTES];unsigned actions=0,animation=0;
    while (fgets(row,sizeof row,f)) {
        row[strcspn(row,"\r\n")]=0;BtpAction a;CHECK(btp_action_parse(row,&a));
        btp_game_tick(&s,r,a);animation|=s.cutscene.kind==9;
        BtpState restored;btp_state_encode(&s,saved);
        if (!btp_state_decode(saved,sizeof saved,btp_active_map(r,&s),btp_state_bld(r,&s),&restored)) {
            fprintf(stderr,"save failed tick %u input %s mode %u pc %x mission %u combat %u pos %u,%u inv %u owned %u effect %u,%u step %u\n",
                actions+1,row,s.mode,s.script.pc,s.mission.phase,s.combat.phase,s.x_half,s.y_half,
                s.campaign.invasion,s.campaign.owned,s.effects.count,s.effects.pending,s.combat.step);
            CHECK(0);
        }
        btp_state_encode(&restored,again);CHECK(!memcmp(saved,again,sizeof saved));s=restored;++actions;
    }
    fclose(f);CHECK(s.story_flags[4] && s.mode==BTP_EXPLORE && !s.campaign.invasion);
    CHECK(animation ? !s.campaign.owned : s.campaign.owned);
    CHECK(btp_save_write("work/campaign-test.btp",&s,r,&e));
    BtpState loaded;CHECK(btp_save_load("work/campaign-test.btp",&loaded,r,&e));
    CHECK(remove("work/campaign-test.btp")==0);
    free(r);printf("PASS: %u checks; %u ordinary invasion inputs, %s branch\n",checks,actions,animation ? "mech lost" : "mech retained");return 0;
}
