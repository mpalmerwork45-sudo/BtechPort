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
    while (s.combat.selected!=7) btp_game_tick(&s,r,BTP_DOWN);
    btp_game_tick(&s,r,BTP_ACCEPT);CHECK(s.combat.phase==BTP_COMBAT_MENU && s.combat.active_unit==1);CHECK(restore(&s,r));
    while (s.combat.selected!=3) btp_game_tick(&s,r,BTP_DOWN);
    btp_game_tick(&s,r,BTP_ACCEPT);CHECK(s.combat.phase==BTP_COMBAT_TARGET && s.combat.target_selected==2 && restore(&s,r));
    btp_game_tick(&s,r,BTP_DOWN);btp_game_tick(&s,r,BTP_ACCEPT);CHECK(restore(&s,r));
    CHECK(s.combat.phase==BTP_COMBAT_MENU && s.combat.selected==0);
    while (s.combat.selected!=9) btp_game_tick(&s,r,BTP_DOWN);
    btp_game_tick(&s,r,BTP_ACCEPT);
    for (unsigned i=0;i<300 && s.combat.phase==BTP_COMBAT_ROUND;++i) { btp_game_tick(&s,r,BTP_IDLE);CHECK(restore(&s,r)); }
    CHECK(s.combat.phase==BTP_COMBAT_MENU && s.combat.round==1);
    CHECK(s.combat.enemy_fired[0]&1u);CHECK(s.combat.plans[0].orders[0]==255);
    f=fopen("tests/fixtures/field-primary.txt","r");CHECK(f);unsigned field=0;
    while (fgets(line,sizeof line,f)) {
        if (line[0]=='H') {
            unsigned skill,equipment,seed,expected,hp[8];CHECK(sscanf(line+1,"%u %u %u %u %u %u %u %u %u %u %u %u",&skill,&equipment,&seed,&expected,&hp[0],&hp[1],&hp[2],&hp[3],&hp[4],&hp[5],&hp[6],&hp[7])==12);
            btp_start(&s);for (unsigned k=0;k<3;++k) s.npc.rng[k]=(uint8_t)(seed>>(k*8));
            for (unsigned p=0;p<8;++p) { uint8_t a[17]={(uint8_t)p,8,9,7,0,0,0,0,0,0,0,0,8,0,0,(uint8_t)(30+p),0};btp_heal_character(a,r->combat.medical[skill][equipment-1],s.npc.rng);CHECK(a[15]==hp[p]); }
            CHECK(rng(&s)==expected);
        } else if (line[0]=='C') {
            unsigned p,seat,occupied,mount[8];char crews[5];CHECK(sscanf(line+1,"%u %u %u %4s %u %u %u %u %u %u %u %u",&p,&seat,&occupied,crews,&mount[0],&mount[1],&mount[2],&mount[3],&mount[4],&mount[5],&mount[6],&mount[7])==12);
            btp_start(&s);btp_party_init(&s);
            for (unsigned i=0;i<8;++i) { memset(s.party.people[i],0,17);s.party.people[i][0]=(uint8_t)i;s.party.people[i][12]=8;s.party.people[i][8]=1; }
            for (unsigned i=0;i<4;++i) { uint8_t *m=btp_party_mech(&s,i);memcpy(m,r->combat.loans[0],125);m[121]=(uint8_t)(occupied ? 1 : 255);m[122]=(uint8_t)(occupied ? 2 : 255); }
            btp_party_allocate(&s,p,2,seat);
            for (unsigned i=0;i<2;++i) { unsigned value;CHECK(sscanf(crews+2*i,"%2x",&value)==1);CHECK(btp_party_mech(&s,2)[121+i]==value); }
            for (unsigned i=0;i<8;++i) CHECK(s.party.people[i][12]==mount[i]);
        } else if (line[0]=='T') {
            unsigned skill,technician,count,reward,expected;uint64_t hashes[4];CHECK(sscanf(line+1,"%u %u %u %u %u %" SCNx64 " %" SCNx64 " %" SCNx64 " %" SCNx64,&skill,&technician,&count,&reward,&expected,&hashes[0],&hashes[1],&hashes[2],&hashes[3])==9);
            btp_start(&s);btp_party_init(&s);s.party.people[technician][0]=(uint8_t)technician;s.party.people[technician][9]=(uint8_t)skill;s.npc.rng[0]=42;s.npc.rng[1]=s.npc.rng[2]=0;
            uint8_t donors[4][125],marked[4]={0};
            for (unsigned i=0;i<4;++i) { uint8_t *m=btp_party_mech(&s,i);memcpy(m,r->combat.loans[0],125);memset(m+17,0,19);m[51]=0x90;m[85]=0xa2;memcpy(donors[i],r->combat.loans[0],125);donors[i][51]=16;donors[i][85]=34;marked[i]=(uint8_t)(i<count); }
            CHECK(btp_party_field_salvage(&s,(const uint8_t (*)[125])donors,marked)==reward);CHECK(rng(&s)==expected);
            for (unsigned i=0;i<4;++i) CHECK(hash(btp_party_mech(&s,i),125)==hashes[i]);
        } else if (line[0]=='P' || line[0]=='M') {
            unsigned p,x,y;CHECK(sscanf(line+1,"%u %u %u",&p,&x,&y)==3);
            CHECK((unsigned)(64+(line[0]=='P' ? r->combat.formation_x[p] : r->combat.mech_formation_x[p]))==x);
            CHECK((unsigned)(64+(line[0]=='P' ? r->combat.formation_y[p] : r->combat.mech_formation_y[p]))==y);
        } else continue;
        ++field;
    }fclose(f);CHECK(field==170);
    free(r);printf("PASS: %u checks, %u party / %u original encounter setup cases and independent ally orders\n",checks,cases,encounters);return 0;
}
