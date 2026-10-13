#include "core/party.h"
#include "core/service.h"
#include "core/spy.h"
#include "core/combat.h"
#include "core/campaign.h"
#include "core/menu.h"
#include "data/save.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
static unsigned checks;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x);exit(1); } } while (0)
static uint64_t hash(const uint8_t *p,size_t n)
{
    uint64_t h=UINT64_C(14695981039346656037);
    for (size_t i=0;i<n;++i) h=(h^p[i])*UINT64_C(1099511628211);
    return h;
}
static void setup(BtpState *s,unsigned count)
{
    btp_start(s);s->story_flags[4]=1;btp_party_init(s);
    s->npc=(BtpNpcState){.rng={70,54,210}};
    for (unsigned i=0;i<8;++i) {
        uint8_t p[17]={(uint8_t)(i<count ? i : 255),8,9,7,0,0,0,0,1,0,0,0,8,0,0,80,0};
        memcpy(s->party.people[i],p,17);
    }
    for (unsigned i=0;i<4;++i) { uint8_t *m=btp_party_mech(s,i);memset(m,0,125);m[0]=255; }
    s->story_flags[36]=127;s->map_id=2;s->x_half=20;s->y_half=68;
    s->campaign.world_x=1300;s->campaign.world_y=1092;
}
static void restored(BtpState *s,const BtpResources *r,BtpAction a)
{
    uint8_t before[BTP_STATE_BYTES],after[BTP_STATE_BYTES];BtpState copy;
    btp_state_encode(s,before);CHECK(btp_state_decode(before,sizeof before,btp_active_map(r,s),btp_state_bld(r,s),&copy));
    btp_game_tick(s,r,a);btp_game_tick(&copy,r,a);
    btp_state_encode(s,before);btp_state_encode(&copy,after);CHECK(!memcmp(before,after,sizeof before));
}
int main(int argc,char **argv)
{
    if (argc!=2) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError e;CHECK(r && btp_resources_load(argv[1],r,&e));
    CHECK(btp_combat_data_load("work/combat-data.bin",&r->combat,&e));
    CHECK(btp_dialogue_load("work/talk-data.bin",&r->dialogue,&e));
    CHECK(btp_world_data_load("work/world-data.bin",&r->world,&e));
    FILE *f=fopen("tests/fixtures/recruitment-primary.txt","r");CHECK(f);char line[512];unsigned cases=0;
    BtpBld repair=r->buildings[5];
    while (fgets(line,sizeof line,f)) {
        BtpState s;unsigned flags[4];uint64_t people,mechs[4];
        if (line[0]=='R') {
            unsigned count,next_id,skill,ever,delay,vehicle,rng,next;
            CHECK(sscanf(line+1,"%u %u %u %u %u %u %u %u %u %u %u %u %" SCNx64 " %" SCNx64 " %" SCNx64 " %" SCNx64 " %" SCNx64,
                &count,&next_id,&skill,&ever,&delay,&vehicle,&rng,&next,&flags[0],&flags[1],&flags[2],&flags[3],&people,&mechs[0],&mechs[1],&mechs[2],&mechs[3])==17);
            setup(&s,count);s.party.next_id=(uint8_t)next_id;s.story_flags[38]=(uint8_t)ever;
            if (vehicle) {
                memcpy(s.campaign.mech,r->combat.loans[0],125);s.campaign.mech[121]=0;s.campaign.mech[122]=255;
                s.party.mech_types[0]='L';s.party.people[0][12]=0;s.campaign.owned=s.campaign.mounted=1;
            }
            s.npc.rng[0]=0x56;s.npc.rng[1]=0x34;s.npc.rng[2]=0x12;
            unsigned recruited=(unsigned)btp_party_recruit(&s,skill);
            CHECK(recruited==(count==8 ? 0u : count+1u));
            if (recruited) {
                s.mode=BTP_BUILDING;s.campaign.building=5;
                s.service=(BtpServiceState){.phase=8,.action=0xe9,.mech=(uint8_t)(recruited-1u),.kind=(uint8_t)skill};
                s.script=(BtpScriptState){.status=BTP_SCRIPT_RECRUIT,.pc=2};
                r->buildings[5]=(BtpBld){.length=3,.bytes={0xe9,(uint8_t)skill,0xff}};
                for (unsigned i=0;i<delay;++i) btp_service_input(&s,r,BTP_IDLE);
                btp_service_input(&s,r,BTP_ACCEPT);
            }
            CHECK(s.party.next_id==next && (s.npc.rng[0]+((unsigned)s.npc.rng[1]<<8)+((unsigned)s.npc.rng[2]<<16))==rng);
            uint8_t encoded[BTP_PARTY_BYTES];BtpPartyState copy;btp_party_encode(&s.party,encoded);
            CHECK(btp_party_decode(encoded,&copy));
        } else if (line[0]=='D') {
            unsigned active,selected,discovered;CHECK(sscanf(line+1,"%u %u %u",&active,&selected,&discovered)==3);
            setup(&s,8);s.story_flags[39]=(uint8_t)active;s.story_flags[37]=2;
            s.mode=BTP_ACTIONS;s.campaign.ui=BTP_MENU_PERSON;s.campaign.selected=(uint8_t)selected;
            restored(&s,r,BTP_ACCEPT);CHECK(s.spy_discovered==discovered);++cases;continue;
        } else {
            unsigned discovered,role;
            CHECK(sscanf(line+1,"%u %u %u %u %u %u %" SCNx64 " %" SCNx64 " %" SCNx64 " %" SCNx64 " %" SCNx64,
                &discovered,&role,&flags[0],&flags[1],&flags[2],&flags[3],&people,&mechs[0],&mechs[1],&mechs[2],&mechs[3])==11);
            setup(&s,5);s.story_flags[36]=31;s.story_flags[37]=2;s.story_flags[38]=s.story_flags[39]=1;s.spy_discovered=(uint8_t)discovered;
            for (unsigned bay=0;bay<4;++bay) {
                uint8_t *m=btp_party_mech(&s,bay);memcpy(m,r->combat.loans[0],125);m[121]=0;m[122]=255;s.party.mech_types[bay]='L';
                if (!bay && role) {
                    s.party.people[2][12]=0;m[121]=(uint8_t)(role<4 ? 2 : 3);m[122]=(uint8_t)(role==1 ? 255 : role<4 ? 3 : 2);
                    if (role==2 || role==3) { s.party.people[3][12]=0;s.party.people[3][8]=(uint8_t)(role==3); }
                }
            }
            s.campaign.owned=1;btp_spy_resolve(&s);
        }
        CHECK(hash((const uint8_t *)s.party.people,136)==people);
        for (unsigned i=0;i<4;++i) { CHECK(s.story_flags[36+i]==flags[i]);CHECK(hash(btp_party_mech(&s,i),125)==mechs[i]); }
        ++cases;
    }
    fclose(f);r->buildings[5]=repair;CHECK(cases==314);
    /* Actual original BLD gates: a replacement is offered after the previous
       specialist dies, but not while an equally skilled one remains. */
    for (unsigned hospital=0;hospital<2;++hospital) for (unsigned specialist=0;specialist<2;++specialist) {
        BtpState s;setup(&s,3);s.party.next_id=3;s.story_flags[24]=(uint8_t)!hospital;s.story_flags[27]=s.story_flags[32]=1;
        unsigned kind=hospital ? 9u : 5u,skill=hospital ? 10u : 9u;
        s.party.people[2][skill]=(uint8_t)(specialist ? 3 : 0);
        s.map_id=(uint8_t)(hospital ? 4 : 2);const BtpMap *map=btp_active_map(r,&s);unsigned entry=0;
        while (entry<16 && map->room_map[entry]!=kind) ++entry;
        CHECK(entry<16);
        s.x_half=map->entrance_x[entry]&127u;s.y_half=(uint16_t)((map->entrance_y[entry]&127u)+1u);
        s.campaign.world_x=(uint16_t)((map->entrance_x[entry]>>8)*128u+s.x_half);
        s.campaign.world_y=(uint16_t)((map->entrance_y[entry]>>12)*128u+s.y_half);
        restored(&s,r,BTP_UP);CHECK(s.mode==BTP_ENTRY);restored(&s,r,BTP_ACCEPT);
        unsigned input=0;
        for (;input<2048 && s.service.phase!=8;++input) {
            if (s.script.status==BTP_SCRIPT_MENU) break;
            restored(&s,r,s.cutscene.active || s.audio.sound_count ? BTP_IDLE : BTP_ACCEPT);
        }
        CHECK(input<2048 && s.script.status==BTP_SCRIPT_MENU);
        unsigned item=hospital ? 2u : 0u;
        while (s.script.selected!=item) restored(&s,r,BTP_DOWN);
        restored(&s,r,BTP_ACCEPT);
        for (input=0;input<4096 && s.service.phase!=8 && s.script.status!=BTP_SCRIPT_MENU;++input)
            restored(&s,r,s.cutscene.active || s.audio.sound_count ? BTP_IDLE : BTP_ACCEPT);
        CHECK(input<4096);
        if (!(specialist ? s.service.phase!=8 && btp_party_count(&s.party)==3 : s.service.phase==8 && btp_party_count(&s.party)==4))
            fprintf(stderr,"Replacement: hospital=%u specialist=%u party=%u phase=%u script=%u/%u menu=%u flags14=%u flags24=%u\n",hospital,specialist,btp_party_count(&s.party),s.service.phase,s.script.status,s.script.pc,s.script.menu_id,s.story_flags[14],s.story_flags[24]);
        CHECK(specialist ? s.service.phase!=8 && btp_party_count(&s.party)==3 : s.service.phase==8 && btp_party_count(&s.party)==4);
        if (!specialist) CHECK(s.party.people[3][skill]==3);
    }
    /* Full ordinary-input route: a random technician becomes the spy, the
       Space inspector exposes him, the first wave resolves it, and a new
       technician joins through the reopened Mechit-Lube BLD. Restore before
       every input, including the betrayal page, rather than edit quest flags. */
    f=fopen("tests/fixtures/ordinary-spy-replacement.actions","r");CHECK(f);BtpState route;btp_start(&route);
    unsigned inputs=0,joined=0,inspected=0,confrontation=0,replaced=0;
    while (fgets(line,sizeof line,f)) {
        line[strcspn(line,"\r\n")]=0;BtpAction a;CHECK(btp_action_parse(line,&a));restored(&route,r,a);++inputs;
        joined|=route.story_flags[39] && route.party.people[2][0]==2;
        inspected|=route.spy_discovered!=0;confrontation|=route.combat.phase==BTP_COMBAT_SPY;
        replaced|=route.party.people[2][0]==3 && route.party.people[2][9]==3;
    }
    fclose(f);CHECK(inputs>50000 && joined && inspected && confrontation && replaced);
    CHECK(route.mode==BTP_EXPLORE && !route.story_flags[39] && route.story_flags[38] && btp_party_count(&route.party)==3);
    free(r);printf("PASS: %u checks; 314 original recruitment/spy cases, replacement BLD visits and ordinary spy combat\n",checks);
    return 0;
}
