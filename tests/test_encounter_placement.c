#include "core/campaign.h"
#include "core/combat.h"
#include "core/party.h"
#include "core/world.h"
#include "data/save.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x);exit(1); } } while (0)
enum { SIDE=128, CELLS=SIDE*SIDE };
static unsigned root(unsigned parent[CELLS],unsigned at)
{
    while (parent[at]!=at) { parent[at]=parent[parent[at]];at=parent[at]; }
    return at;
}
/* An independent connected-component check over actual terrain. Joining
   neighbours tests whether an enemy can approach any living party member;
   it does not call the encounter's placement or reachability helpers. */
static void components(const BtpResources *r,const BtpState *s,unsigned mech,unsigned parent[CELLS],uint8_t legal[CELLS])
{
    BtpMap map;btp_combat_map(r,s,&map);
    for (unsigned y=0;y<SIDE;++y) for (unsigned x=0;x<SIDE;++x) {
        unsigned at=y*SIDE+x;parent[at]=at;
        legal[at]=(uint8_t)(x<126 && btp_map_tile(&map,(int)(x+1)/2,(int)y/2)<85);
        if (mech) {
            legal[at]=(uint8_t)(x<126 && btp_map_tile(&map,(int)x/2,(int)y/2)<85 &&
                btp_map_tile(&map,(int)x/2+1,(int)y/2)<85 &&
                btp_world_location(r,s,(s->campaign.battle_x+(int)x)/2,(s->campaign.battle_y+(int)y)/2)!=2 &&
                btp_world_location(r,s,(s->campaign.battle_x+(int)x)/2+1,(s->campaign.battle_y+(int)y)/2)!=2);
        }
        if (!legal[at]) continue;
        if (x && legal[at-1]) parent[root(parent,at)]=root(parent,at-1);
        if (y) for (int dx=-1;dx<=1;++dx) if ((int)x+dx>=0 && (int)x+dx<SIDE) {
            unsigned other=(y-1)*SIDE+(unsigned)((int)x+dx);
            if (legal[other]) parent[root(parent,at)]=root(parent,other);
        }
    }
}
static void restore(BtpState *s,const BtpResources *r)
{
    uint8_t a[BTP_STATE_BYTES],b[BTP_STATE_BYTES];BtpState copy;btp_state_encode(s,a);
    CHECK(btp_state_decode(a,sizeof a,btp_active_map(r,s),btp_state_bld(r,s),&copy));
    btp_state_encode(&copy,b);CHECK(!memcmp(a,b,sizeof a));*s=copy;
}
static BtpState context(const BtpResources *r,unsigned x,unsigned y,unsigned mechs)
{
    BtpState s;btp_start(&s);s.story_flags[4]=1;s.story_flags[38]=1;
    s.campaign.world_x=(uint16_t)x;s.campaign.world_y=(uint16_t)y;
    s.map_id=(uint8_t)btp_world_location(r,&s,(int)x/2,(int)y/2);
    s.x_half=(uint16_t)(s.map_id ? x&127u : x);s.y_half=(uint16_t)(s.map_id ? y&127u : y);
    btp_party_init(&s);
    for (unsigned i=0;i<mechs;++i) {
        memcpy(s.party.people[i],s.party.people[0],17);s.party.people[i][0]=(uint8_t)i;
        uint8_t *m=btp_party_mech(&s,i);memcpy(m,r->combat.loans[0],125);m[121]=(uint8_t)i;m[122]=255;
        s.party.mech_types[i]=m[0];s.party.people[i][12]=(uint8_t)i;
    }
    s.campaign.owned=s.campaign.mounted=(uint8_t)(mechs!=0);s.party.next_id=(uint8_t)(mechs ? mechs : 1);
    if (mechs==3) { memcpy(s.party.people[3],s.party.people[0],17);s.party.people[3][0]=3;s.party.people[3][12]=8;s.party.next_id=4; }
    btp_party_follow(&s,r,(uint16_t)x,(uint16_t)y);
    return s;
}
int main(int argc,char **argv)
{
    if (argc!=2 && argc!=3) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError error;
    CHECK(r && btp_resources_load(argv[1],r,&error));CHECK(btp_world_data_load("work/world-data.bin",&r->world,&error));
    CHECK(btp_combat_data_load("work/combat-data.bin",&r->combat,&error));CHECK(btp_dialogue_load("work/talk-data.bin",&r->dialogue,&error));
    const unsigned centres[][2]={{1274,1078},{1274,1090},{1274,1130},{1274,1144},
        {1290,1018},{1330,1018},{1370,1018},{1412,1040},{1412,1090},{1412,1130},
        {1300,1158},{1340,1158},{1380,1158},{1339,1117},{1324,1098},{1200,1200}};
    const unsigned seeds[]={1,2,3,4,17,42,1234,5678,0x123456,0xffffff};
    unsigned contexts=0,offers=0,enemies=0,none=0,feet=0,vehicles=0,captured=0;
    for (unsigned group=0;group<3;++group) for (unsigned pos=0;pos<sizeof centres/sizeof *centres;++pos) {
        BtpState before=context(r,centres[pos][0],centres[pos][1],group ? group==1 ? 1u : 3u : 0u);
        if (!btp_party_can_stand(&before,r,before.campaign.world_x,before.campaign.world_y) || (before.map_id==2 && group)) continue;
        ++contexts;unsigned parent[2][CELLS];uint8_t legal[2][CELLS];int prepared=0;
        for (unsigned j=0;j<sizeof seeds/sizeof *seeds;++j) {
            BtpState s=before;
            for (unsigned b=0;b<3;++b) s.npc.rng[b]=(uint8_t)(seeds[j]>>(8*b));
            BtpState draws=s;BtpCombatUnit candidates[12];uint8_t ids[12];int dx,dy;
            unsigned generated=btp_campaign_candidates(&draws,r,candidates,ids,&dx,&dy);
            int offered=btp_campaign_random(&s,r);CHECK(!memcmp(s.npc.rng,draws.npc.rng,3));
            if (!offered) {
                CHECK(s.mode==BTP_EXPLORE && !s.campaign.encounter && !s.combat.count);
                CHECK(s.x_half==before.x_half && s.y_half==before.y_half);restore(&s,r);++none;continue;
            }
            CHECK(s.combat.phase==BTP_COMBAT_OFFER && s.combat.count>s.combat.friends);++offers;
            if (!prepared) { for (unsigned kind=0;kind<2;++kind) components(r,&s,kind,parent[kind],legal[kind]);prepared=1; }
            for (unsigned i=s.combat.friends;i<s.combat.count;++i) {
                const BtpCombatUnit *u=&s.combat.unit[i];unsigned kind=!u->infantry,at=(unsigned)u->y*SIDE+u->x;int reachable=0,matched=0;
                if (!legal[kind][at]) fprintf(stderr,"Illegal spawn at world %u,%u, party %u,%u seed %u id %u\n",s.campaign.battle_x+u->x,s.campaign.battle_y+u->y,before.campaign.world_x,before.campaign.world_y,seeds[j],s.combat.ids[i]);
                CHECK(legal[kind][at]);
                for (unsigned f=0;f<s.combat.friends;++f) {
                    const BtpCombatUnit *friend=&s.combat.unit[f];
                    int margin=kind && friend->infantry ? 1 : 0;
                    for (int offset=-margin;offset<=margin;++offset) {
                        int x=(int)friend->x+offset;if (x<0 || x>=SIDE) continue;
                        unsigned goal=friend->y*SIDE+(unsigned)x;
                        if (legal[kind][goal] && root(parent[kind],at)==root(parent[kind],goal)) reachable=1;
                    }
                }
                if (!reachable) fprintf(stderr,"Unreachable spawn at world %u,%u, party %u,%u seed %u id %u\n",s.campaign.battle_x+u->x,s.campaign.battle_y+u->y,before.campaign.world_x,before.campaign.world_y,seeds[j],s.combat.ids[i]);
                CHECK(reachable);
                for (unsigned k=0;k<generated;++k) if (s.combat.ids[i]==ids[k]) {
                    CHECK(!memcmp(u->record,candidates[k].record,u->infantry ? 17u : 125u));matched=1;
                }
                CHECK(matched);++enemies;if (kind) ++vehicles;else ++feet;
            }
            restore(&s,r);
            if (argc==3 && !pos && !(captured&(1u<<group))) {
                /* Optional controlled prerequisites for the SDL test; no
                   supplied original save or ordinary campaign is edited. */
                char path[1024];int n=snprintf(path,sizeof path,"%s-%u.btp",argv[2],group);
                CHECK(n>0 && (size_t)n<sizeof path && btp_save_write(path,&s,r,&error));captured|=1u<<group;
            }
        }
    }
    CHECK(contexts>=30 && offers>=100 && feet && vehicles);
    CHECK(argc==2 || captured==7);
    printf("PASS: %u checks, %u legal party positions / %u seeds, %u offers, %u empty placements, %u reachable enemies (%u foot / %u mechs)\n",
        checks,contexts,(unsigned)(sizeof seeds/sizeof *seeds),offers,none,enemies,feet,vehicles);
    free(r);return 0;
}
