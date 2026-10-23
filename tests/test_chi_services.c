/* Synthetic service contracts and mechanics; no original resources required. */
#include "data/chi_services.h"
#include "data/project.h"
#include "core/service.h"
#include "core/party.h"
#include "core/economy.h"
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
static BtpError error;
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"CHI service line %d: %s (%s)\n",__LINE__,#x,error.text);exit(1); } } while (0)
static int load(BtpResources *r,BtpChiServices *c,const char *body)
{
    memset(c,0,sizeof *c);FILE *f=fopen("chi-services-test.json","wb");CHECK(f);
    fprintf(f,"{\"format\":\"btp-chi-services-v1\",\"schema_version\":1,\"parameters\":{%s}}",body);CHECK(!fclose(f));
    BtpDigest d;btp_digest_start(&d);error.text[0]=0;
    int ok=btp_chi_services_load(".","chi-services-test.json",c,r,&d,&error);CHECK(!remove("chi-services-test.json"));return ok;
}
int main(void)
{
    BtpResources *r=calloc(1,sizeof *r);BtpProject *p=calloc(1,sizeof *p);BtpChiServices *c=calloc(1,sizeof *c);BtpState *s=calloc(1,sizeof *s);
    CHECK(r && p && c && s);r->project=p;p->chi_services=c;
    CHECK(load(r,c,"\"repair.armour\":7,\"repair.structure\":11,\"repair.weapon\":40,\"armour.repair.1\":3,\"recruit.rank\":4,\"recruit.limit\":2,\"market.rate.0\":100"));
    CHECK(btp_chi_service(r,BTP_SVC_REPAIR_ARMOUR)==7 && btp_chi_service_default(r,BTP_SVC_REPAIR_ARMOUR)==4);
    char text[128];CHECK(btp_chi_service_expand(r,"Cost {service:repair.armour}.",text,sizeof text));CHECK(!strcmp(text,"Cost 7."));
    CHECK(btp_chi_service_expand(r,"{service:armour.price.4:comma}",text,sizeof text));CHECK(!strcmp(text,"10,000"));
    CHECK(!btp_chi_service_expand(r,"{service:missing}",text,sizeof text));CHECK(!btp_chi_service_expand(r,"{service:repair.armour}",text,1));
    btp_start(s);btp_party_init(s);s->credits=20;s->campaign.mech[0]='L';s->campaign.mech[17]=0;s->campaign.mech[86]=3;
    CHECK(btp_mech_repair_resources(s,r,0,0,0)==2 && s->credits==6 && s->campaign.mech[17]==2);
    s->credits=7;CHECK(btp_mech_repair_resources(s,r,0,0,0)==1 && !s->credits);
    s->credits=8;s->party.people[0][13]=1;s->party.people[0][14]=22;CHECK(btp_armour_repair_resources(s,r,0)==2 && s->credits==2 && s->armor_points==24);
    unsigned member=(unsigned)btp_party_recruit_resources(s,r,5);CHECK(member==2 && s->party.people[1][9]==4);CHECK(!btp_party_recruit_resources(s,r,6));
    for (unsigned i=0;i<47;++i) { CHECK(btp_chi_actions[i].action==i+1 && btp_chi_actions[i].buildings);for (unsigned k=0;k<i;++k) CHECK(strcmp(btp_chi_actions[i].id,btp_chi_actions[k].id)); }
    const char *bad[]={"\"repair.armour\":-1","\"repair.armour\":true","\"repair.armour\":1,\"repair.armour\":2","\"unknown\":0","\"market.rate.0\":0","\"recruit.spy_chance\":25","\"prison.reward\":3","\"prison.start_attempt\":5"};
    for (unsigned i=0;i<sizeof bad/sizeof *bad;++i) CHECK(!load(r,c,bad[i]));
    free(s);free(c);free(p);free(r);puts("Native service catalogue, strict fields, price references, partial repairs, recruitment and bounded failures pass.");return 0;
}
