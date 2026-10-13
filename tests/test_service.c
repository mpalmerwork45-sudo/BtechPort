#include "core/service.h"
#include "core/party.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
static unsigned checks;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x);return 1; } } while (0)
static uint64_t hash(const uint8_t *b,size_t n) { uint64_t h=UINT64_C(14695981039346656037);for (size_t i=0;i<n;++i) h=(h^b[i])*UINT64_C(1099511628211);return h; }
int main(void)
{
    BtpResources *r=calloc(1,sizeof *r);BtpError e;CHECK(r);CHECK(btp_combat_data_load("work/combat-data.bin",&r->combat,&e));
    FILE *f=fopen("tests/fixtures/service-rules.txt","r");CHECK(f);char line[200];unsigned cases=0;
    while (fgets(line,sizeof line,f)) if (line[0]=='F' || line[0]=='P' || line[0]=='A') {
        BtpState s;btp_start(&s);s.story_flags[4]=1;s.campaign.owned=1;s.credits=50000;unsigned kind,loan=0,funds=0,expected;uint64_t record;
        if (line[0]=='F') { CHECK(sscanf(line+1,"%u %u %u %" SCNx64,&kind,&loan,&expected,&record)==4); }
        else if (line[0]=='P') { CHECK(sscanf(line+1,"%u %u %u %" SCNx64,&kind,&funds,&expected,&record)==4); }
        else { CHECK(sscanf(line+1,"%u %u %" SCNx64,&funds,&expected,&record)==3);kind=0; }
        memcpy(s.campaign.mech,r->combat.loans[loan],125);btp_party_init(&s);uint8_t *m=s.campaign.mech;
        if (line[0]=='F') {
            m[123]=(uint8_t)(kind%4);m[124]=(uint8_t)(kind/4);for (unsigned i=0;i<12;++i) m[39+i]=(uint8_t)i;
            for (unsigned i=0;i<10;++i) m[107+i]=(uint8_t)(60+i);
            CHECK(btp_mech_refit(&s,r,0));
        } else if (line[0]=='P') {
            unsigned first=kind ? 28 : 17;m[first]=(uint8_t)(m[first+69]-3);m[first+1]=(uint8_t)(m[first+70]-2);
            s.credits=funds;(void)btp_mech_repair(&s,0,kind,0);
        } else { m[39]=0;m[107]=5;s.credits=funds;(void)btp_mech_reload(&s,r,0,0,5); }
        if (hash(m,125)!=record || s.credits!=expected) fprintf(stderr,"case %s actual cash %u hash %016" PRIx64 "\n",line,s.credits,hash(m,125));
        CHECK(s.credits==expected);CHECK(hash(m,125)==record);++cases;
    }
    fclose(f);CHECK(cases==47);
    f=fopen("tests/fixtures/armour-repair-primary.txt","r");CHECK(f);unsigned armour_cases=0;
    while (fgets(line,sizeof line,f)) {
        unsigned member,kind,points,funds,yes,flag,after,cash,questions;
        CHECK(sscanf(line,"%u %u %u %u %u %u %u %u %u",&member,&kind,&points,&funds,&yes,&flag,&after,&cash,&questions)==9);
        BtpState s;btp_start(&s);btp_party_init(&s);s.credits=funds;
        s.party.people[member][0]=(uint8_t)member;s.party.people[member][13]=(uint8_t)kind;s.party.people[member][14]=(uint8_t)points;
        if (yes) (void)btp_armour_repair(&s,member);
        CHECK(flag==kind && s.party.people[member][14]==after && s.credits==cash);
        CHECK(questions==(unsigned)(points!=(kind==1 ? 25u : kind==2 ? 40u : kind==3 ? 30u : 50u)));
        ++armour_cases;
    }
    fclose(f);CHECK(armour_cases==360);
    /* The same original seven-digit editor serves the ammo prompt. Erasure
       and Escape clear must keep the transaction open without charging cash. */
    BtpState s;btp_start(&s);s.story_flags[4]=1;s.campaign.owned=1;s.credits=10;
    memcpy(s.campaign.mech,r->combat.loans[0],125);btp_party_init(&s);
    s.campaign.mech[39]=0;s.campaign.mech[107]=5;
    s.service=(BtpServiceState){.phase=5,.action=44,.kind=1,.amount=5,.quote_credits=10};
    btp_service_input(&s,r,BTP_DIGIT_1);btp_service_input(&s,r,BTP_DIGIT_2);
    btp_service_input(&s,r,BTP_CANCEL);CHECK(s.service.phase==5 && !strcmp(s.service.input,"1") && s.credits==10);
    btp_service_input(&s,r,BTP_CLEAR_INPUT);CHECK(!strcmp(s.service.input,"0") && s.service.phase==5);
    for (unsigned i=0;i<9;++i) btp_service_input(&s,r,BTP_DIGIT_2);
    CHECK(!strcmp(s.service.input,"2222222") && s.credits==10);
    for (unsigned i=0;i<7;++i) btp_service_input(&s,r,BTP_CANCEL);
    CHECK(!s.service.input[0] && s.service.phase==5);
    btp_service_input(&s,r,BTP_DIGIT_2);btp_service_input(&s,r,BTP_ACCEPT);
    CHECK(s.service.phase==4 && s.service.outcome==1 && s.service.item==1 && s.campaign.mech[39]==2 && s.credits==6);
    free(r);printf("PASS: %u checks, %u original service and %u armour repair cases, ammo editor\n",checks,cases,armour_cases);return 0;
}
