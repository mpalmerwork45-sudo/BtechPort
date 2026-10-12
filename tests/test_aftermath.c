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
static unsigned rng(const BtpState *s) { return s->npc.rng[0]+((unsigned)s->npc.rng[1]<<8)+((unsigned)s->npc.rng[2]<<16); }
static uint64_t hash(const uint8_t *p,size_t n) { uint64_t h=UINT64_C(14695981039346656037);for (size_t i=0;i<n;++i) h=(h^p[i])*UINT64_C(1099511628211);return h; }
static int restore(BtpState *s,const BtpResources *r) {
    uint8_t a[BTP_STATE_BYTES],b[BTP_STATE_BYTES];BtpState t;
    btp_state_encode(s,a);if (!btp_state_decode(a,sizeof a,btp_active_map(r,s),btp_state_bld(r,s),&t)) return 0;
    btp_state_encode(&t,b);if (memcmp(a,b,sizeof a)) return 0;*s=t;return 1;
}
static void setup(BtpState *s,const BtpResources *r,unsigned slot) {
    btp_start(s);s->story_flags[4]=1;s->npc=(BtpNpcState){.rng={31,66,171}};s->map_id=0;s->mode=BTP_ENCOUNTER;
    s->campaign.world_x=320;s->campaign.world_y=333;s->campaign.battle_x=256;s->campaign.battle_y=256;s->campaign.owned=1;s->campaign.encounter=1;
    s->x_half=64;s->y_half=79;btp_party_init(s);s->party.mech_types[slot]='L';memcpy(btp_party_mech(s,slot),r->combat.loans[0],125);
    for (unsigned i=0;i<8;++i) { const uint8_t p[17]={(uint8_t)i,8,9,7,0,0,0,1,1,1,0,9,(uint8_t)slot,3,30,80,0};memcpy(s->party.people[i],p,17); }
    s->combat=(BtpCombatState){.phase=BTP_COMBAT_ROUND,.friends=1,.count=2,.target_unit=1,.last_target=1,.movement=255,.kick_target=255,.enemy_movement=255};
    BtpCombatState *c=&s->combat;memset(c->orders,255,11);memset(c->enemy_orders,255,sizeof c->enemy_orders);memset(c->enemy_modes,255,sizeof c->enemy_modes);
    c->ids[0]=(uint8_t)slot;c->ids[1]=12;
    for (unsigned i=0;i<2;++i) { memcpy(c->unit[i].record,r->combat.loans[0],125);c->unit[i].x=(uint8_t)(64+10*i);c->unit[i].y=77;c->plans[i].movement=255;c->plans[i].kick=255;memset(c->plans[i].orders,255,11); }
}
int main(int argc,char **argv) {
    if (argc!=2) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError e;CHECK(r);CHECK(btp_resources_load(argv[1],r,&e));CHECK(btp_combat_data_load("work/combat-data.bin",&r->combat,&e));
    FILE *f=fopen("tests/fixtures/aftermath-primary.txt","r");CHECK(f);char line[300];unsigned cases=0;
    while (fgets(line,sizeof line,f)) {
        BtpState s;btp_start(&s);
        if (line[0]=='R') { unsigned n,seed,amount,expected;CHECK(sscanf(line+1,"%u %u %u %u",&n,&seed,&amount,&expected)==4);for (unsigned i=0;i<3;++i) s.npc.rng[i]=(uint8_t)(seed>>(8*i));CHECK(btp_aftermath_cash(s.npc.rng,n)==amount);CHECK(rng(&s)==expected); }
        else if (line[0]=='S') { unsigned skill,v,yes;CHECK(sscanf(line+1,"%u %u %u",&skill,&v,&yes)==3);uint8_t m[125];memcpy(m,r->combat.loans[0],125);m[117]=v&1 ? 3 : 0;m[118]=v&2 ? 2 : 0;m[31]=v&4 ? 0 : 3;CHECK(btp_salvage_eligible(m,skill)==(int)yes); }
        else if (line[0]=='C') { unsigned loan,pilot,mount;uint64_t expected;CHECK(sscanf(line+1,"%u %u %" SCNx64 " %u",&loan,&pilot,&expected,&mount)==4);btp_party_init(&s);uint8_t m[125];memcpy(m,r->combat.loans[loan],125);unsigned kind=m[0];m[0]=255;m[117]=3;m[118]=2;m[31]=m[32]=0;btp_salvage_copy(&s,0,pilot,m,kind);CHECK(hash(s.campaign.mech,125)==expected);CHECK(s.party.people[pilot][12]==mount); }
        else if (line[0]=='E') { unsigned slot,pilot,second,v[10];CHECK(sscanf(line+1,"%u %u %u %u %u %u %u %u %u %u %u %u %u",&slot,&pilot,&second,&v[0],&v[1],&v[2],&v[3],&v[4],&v[5],&v[6],&v[7],&v[8],&v[9])==13);setup(&s,r,slot);s.combat.unit[0].record[121]=(uint8_t)pilot;s.combat.unit[0].record[122]=(uint8_t)second;unsigned seed=rng(&s);btp_campaign_destroy(&s,0);CHECK(s.combat.unit[0].record[0]==v[0]);CHECK(s.aftermath.wrecks[slot] && v[1]);btp_campaign_eject(&s);CHECK(rng(&s)==seed);
            for (unsigned crew=0;crew<2;++crew) { unsigned member=crew ? second : pilot;if (member==255) continue;unsigned at=btp_combat_target(&s.combat,4+member);CHECK(at<s.combat.friends);CHECK(s.combat.unit[at].record[12]==v[2+4*crew]);CHECK(s.combat.unit[at].record[0]!=255 && v[3+4*crew]);CHECK(s.combat.unit[at].x==v[4+4*crew] && s.combat.unit[at].y==v[5+4*crew]); }
            CHECK(restore(&s,r)); }
        else continue;
        ++cases;
    }fclose(f);CHECK(cases==114);
    BtpState s;setup(&s,r,0);s.combat.unit[0].record[121]=0;s.combat.unit[0].record[122]=1;btp_campaign_destroy(&s,0);btp_campaign_eject(&s);CHECK(s.combat.friends==3 && s.combat.count==4 && !s.effects.pending);CHECK(restore(&s,r));
    btp_campaign_destroy(&s,3);s.combat.phase=0;s.combat.won=1;btp_campaign_result(&s,r);CHECK(s.aftermath.phase==1);CHECK(restore(&s,r));CHECK(btp_save_write("work/aftermath-salvage.btp",&s,r,&e));
    for (unsigned guard=0;guard<30 && s.mode==BTP_ENCOUNTER;++guard) { btp_game_tick(&s,r,BTP_ACCEPT);CHECK(restore(&s,r)); }
    CHECK(s.mode==BTP_EXPLORE && s.campaign.mounted && s.party.people[0][12]<4);CHECK(s.campaign.mech[117]==1 && s.campaign.mech[118]==1);
    setup(&s,r,0);s.combat.unit[0].record[121]=0;s.combat.unit[0].record[122]=255;btp_campaign_destroy(&s,0);btp_campaign_eject(&s);unsigned j=btp_combat_target(&s.combat,4);btp_campaign_destroy(&s,j);CHECK(s.effects.pending==2);s.effects.pending=0;s.combat.phase=0;s.combat.lost=1;btp_campaign_result(&s,r);CHECK(s.mode==BTP_GAME_OVER && s.party.people[0][0]==255);CHECK(restore(&s,r));
    free(r);printf("PASS: %u checks; %u primary aftermath cases, saved salvage and crew survival/loss\n",checks,cases);return 0;
}
