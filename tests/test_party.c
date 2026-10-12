#include "core/campaign.h"
#include "core/party.h"
#include "core/combat.h"
#include "data/save.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
static unsigned checks;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x);return 1; } } while (0)
static uint64_t hash(const uint8_t *b,size_t n) { uint64_t h=UINT64_C(14695981039346656037);for (size_t i=0;i<n;++i) h=(h^b[i])*UINT64_C(1099511628211);return h; }
static unsigned rng(const BtpState *s) { return s->npc.rng[0]+((unsigned)s->npc.rng[1]<<8)+((unsigned)s->npc.rng[2]<<16); }
static int restore(BtpState *s,const BtpResources *r)
{
    uint8_t a[BTP_STATE_BYTES],b[BTP_STATE_BYTES];BtpState v;
    btp_state_encode(s,a);if (!btp_state_decode(a,sizeof a,btp_active_map(r,s),btp_state_bld(r,s),&v)) return 0;
    btp_state_encode(&v,b);if (memcmp(a,b,sizeof a)) return 0;*s=v;return 1;
}
int main(int argc,char **argv)
{
    if (argc!=2) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError e;CHECK(r);
    CHECK(btp_resources_load(argv[1],r,&e));CHECK(btp_combat_data_load("work/combat-data.bin",&r->combat,&e));
    FILE *f=fopen("tests/fixtures/party-setup.txt","r");CHECK(f);char line[800],hex[35];unsigned cases=0;
    while (fgets(line,sizeof line,f)) if (line[0]=='R' || line[0]=='G') {
        BtpState s;btp_start(&s);s.story_flags[4]=1;s.map_id=2;s.x_half=105;s.y_half=94;
        s.campaign.world_x=1385;s.campaign.world_y=1118;s.story_flags[38]=1;btp_party_init(&s);
        unsigned seed,expected,skill,count;uint64_t mech;int used;
        if (line[0]=='R') {
            CHECK(sscanf(line+1,"%u %u %34s %" SCNx64 " %u%n",&seed,&expected,hex,&mech,&count,&used)==5);
            for (unsigned i=0;i<3;++i) s.npc.rng[i]=(uint8_t)(seed>>(i*8));
            btp_campaign_rex(&s,r);CHECK(s.combat.count==count+2 && s.combat.friends==2);
            CHECK(hash(s.campaign.mech,125)==mech);
            char *at=line+1+used;
            for (unsigned i=0;i<count;++i) {
                unsigned x,y;uint64_t record;CHECK(sscanf(at,"%u %u %" SCNx64 "%n",&x,&y,&record,&used)==3);at+=used;
                CHECK(s.combat.unit[i+2].x==x && s.combat.unit[i+2].y==y);
                CHECK(hash(s.combat.unit[i+2].record,17)==record);
            }
            CHECK(restore(&s,r));
            for (unsigned i=0;i<3;++i) { btp_game_tick(&s,r,BTP_ACCEPT);CHECK(restore(&s,r)); }
            btp_combat_select(&s.combat,1);CHECK(restore(&s,r));
        } else {
            CHECK(sscanf(line+1,"%u %u %u %34s",&seed,&skill,&expected,hex)==4);
            s.party.next_id=(uint8_t)seed;CHECK(btp_party_recruit(&s,skill));CHECK(restore(&s,r));
        }
        CHECK(rng(&s)==expected);
        for (unsigned i=0;i<17;++i) { unsigned value;CHECK(sscanf(hex+2*i,"%2x",&value)==1);CHECK(s.party.people[1][i]==value); }
        ++cases;
    }
    fclose(f);CHECK(cases==65);
    f=fopen("tests/fixtures/encounter-setup.txt","r");CHECK(f);unsigned encounters=0;
    while (fgets(line,sizeof line,f)) if (line[0]=='E') {
        unsigned owned,seed,expected,count;int dx,dy,used;
        CHECK(sscanf(line+1,"%u %u %u %d %d %u%n",&owned,&seed,&expected,&dx,&dy,&count,&used)==6);
        BtpState s;btp_start(&s);s.story_flags[4]=1;s.campaign.owned=(uint8_t)owned;
        if (owned) memcpy(s.campaign.mech,r->combat.loans[0],125);
        btp_party_init(&s);for (unsigned i=0;i<3;++i) s.npc.rng[i]=(uint8_t)(seed>>(i*8));
        BtpCombatUnit units[12];uint8_t ids[12];int x,y;
        CHECK(btp_campaign_candidates(&s,r,units,ids,&x,&y)==count);CHECK(x==dx && y==dy);CHECK(rng(&s)==expected);
        char *at=line+1+used;
        for (unsigned i=0;i<count;++i) { unsigned id;uint64_t record;CHECK(sscanf(at,"%u %" SCNx64 "%n",&id,&record,&used)==2);at+=used;
            CHECK(ids[i]==id);CHECK(hash(units[i].record,units[i].infantry ? 17 : 125)==record); }
        ++encounters;
    }
    fclose(f);CHECK(encounters==18);
    BtpState s;btp_start(&s);s.story_flags[4]=1;s.map_id=2;s.campaign.world_x=1385;s.campaign.world_y=1118;
    s.npc.rng[0]=1;s.npc.rng[1]=s.npc.rng[2]=0;btp_campaign_rex(&s,r);
    for (unsigned i=0;i<3;++i) { btp_game_tick(&s,r,BTP_ACCEPT);CHECK(restore(&s,r)); }
    for (unsigned i=0;i<6;++i) btp_game_tick(&s,r,BTP_DOWN);
    btp_game_tick(&s,r,BTP_ACCEPT);CHECK(s.combat.phase==BTP_COMBAT_PICK);
    btp_game_tick(&s,r,BTP_DOWN);btp_game_tick(&s,r,BTP_ACCEPT);CHECK(s.combat.active_unit==1);CHECK(restore(&s,r));
    for (unsigned i=0;i<4;++i) btp_game_tick(&s,r,BTP_DOWN);
    for (unsigned i=0;i<4;++i) { btp_game_tick(&s,r,BTP_ACCEPT);CHECK(restore(&s,r)); }
    CHECK(s.combat.phase==BTP_COMBAT_MENU);btp_game_tick(&s,r,BTP_ACCEPT);
    for (unsigned i=0;i<300 && s.combat.phase==BTP_COMBAT_ROUND;++i) { btp_game_tick(&s,r,BTP_IDLE);CHECK(restore(&s,r)); }
    CHECK(s.combat.phase==BTP_COMBAT_MENU && s.combat.round==1);
    CHECK(s.combat.enemy_fired[0]&1u);CHECK(s.combat.plans[0].orders[0]==255);
    free(r);printf("PASS: %u checks, %u party / %u original encounter setup cases and independent ally orders\n",checks,cases,encounters);return 0;
}
