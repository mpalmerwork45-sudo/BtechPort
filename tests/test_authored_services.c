#include "core/authored_services.h"
#include "core/events.h"
#include "core/party.h"
#include "core/roster_game.h"
#include "data/content.h"
#include "data/project.h"
#include "data/save.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"%s:%d %s: %s\n",__FILE__,__LINE__,#x,error.text);exit(1); } } while(0)
static BtpError error;
int main(int argc,char **argv)
{
    CHECK(argc==2);BtpContent c={0};CHECK(btp_content_load_project(&c,argv[1],NULL,&error));
    const BtpResources *r=c.resources;BtpState *s=calloc(1,sizeof *s),*old=calloc(1,sizeof *old);CHECK(s && old);
    btp_start(s);s->project=1;CHECK(btp_set_combat_profile(s,r,1));btp_events_start(s,r);
    BtpEventNode e={.op=BTP_EVENT_REPAIR,.value=100};uint8_t *m=btp_party_mech(s,0);
    m[17]=0;m[117]=2;m[118]=1;m[119]=1;m[36]=0;m[51]|=128;m[39]=0;
    s->party.people[0][15]=1;s->credits=99;*old=*s;
    CHECK(btp_authored_service(s,r,&e)==1 && !memcmp(s,old,sizeof *s));
    s->credits=1000;CHECK(!btp_authored_service(s,r,&e));CHECK(s->credits==900 && m[17]==m[86] && !m[117] && !m[118] && !m[119]);
    CHECK(!m[39] && s->party.people[0][15]==1);*old=*s;
    CHECK(btp_authored_service(s,r,&e)==2 && !memcmp(s,old,sizeof *s));
    e.op=BTP_EVENT_REARM;CHECK(!btp_authored_service(s,r,&e));CHECK(m[39]==m[107] && s->credits==800);
    e.op=BTP_EVENT_HEAL;CHECK(!btp_authored_service(s,r,&e));CHECK(s->party.people[0][15]==10*s->party.people[0][1] && s->credits==700);
    e.argument=8;*old=*s;CHECK(btp_authored_service(s,r,&e)==1 && !memcmp(s,old,sizeof *s));
    e=(BtpEventNode){.op=BTP_EVENT_SALVAGE,.value=50,.x=1};
    while (btp_broker_count(s)<4) CHECK(!btp_authored_service(s,r,&e));
    *old=*s;CHECK(btp_authored_service(s,r,&e)==1 && !memcmp(s,old,sizeof *s));
    CHECK(s->party.mechs[2][121]==255 && s->party.mechs[2][17]==r->roster.mechs[1].record[17]/2);
    CHECK(btp_save_write("services-roundtrip.btp",s,r,&error));CHECK(btp_save_load("services-roundtrip.btp",old,r,&error));
    CHECK(old->credits==s->credits && !memcmp(&s->party,&old->party,sizeof s->party));
    CHECK(!remove("services-roundtrip.btp"));free(old);free(s);btp_content_close(&c);
    puts("PASS: priced repair, rearm, heal, salvage, empty/full/no-op transactions and save/load.");return 0;
}
