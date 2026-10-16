#include "data/content.h"
#include "data/save.h"
#include "core/party.h"
#include "core/menu.h"
#include "core/npc.h"
#include "core/campaign.h"
#include "core/world.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"FAIL %s:%d: %s\n",__FILE__,__LINE__,#x);exit(1); } } while (0)
static void setup(BtpState *s,const BtpResources *r)
{
    btp_start(s);s->story_flags[4]=s->story_flags[58]=1;s->map_id=4;
    const BtpMap *map=&r->local[3];s->x_half=32;s->y_half=32;
    s->campaign.world_x=(uint16_t)((map->entrance_x[0]>>8)*128u+32u);
    s->campaign.world_y=(uint16_t)((map->entrance_y[0]>>12)*128u+32u);
    btp_npc_enter(s,map);btp_party_init(s);
    for (unsigned i=1;i<8;++i) { memcpy(s->party.people[i],s->party.people[0],17);s->party.people[i][0]=(uint8_t)i; }
    for (unsigned i=0;i<4;++i) {
        uint8_t *m=btp_party_mech(s,i);memcpy(m,r->combat.loans[0],125);
        m[121]=(uint8_t)i;m[122]=255;s->party.people[i][12]=(uint8_t)i;s->party.mech_types[i]=m[0];
    }
    s->campaign.mounted=s->campaign.owned=1;btp_party_recover(s,r,1);
}
static void formation(const BtpState *s,const BtpResources *r,int exact)
{
    unsigned person=0,mech=0;
    for (unsigned i=0;i<12;++i) {
        int vehicle=i>=8;unsigned x,y,place;
        if (vehicle) {
            const uint8_t *m=i==8 ? s->campaign.mech : s->party.mechs[i-9];if (m[0]==255) continue;
            place=mech++;x=s->party.mech_x[i-8];y=s->party.mech_y[i-8];
        } else {
            if (s->party.people[i][0]==255 || s->party.people[i][12]<8) continue;
            place=person++;x=s->party.x[i];y=s->party.y[i];
        }
        int gx=(int)s->campaign.world_x+(vehicle ? r->combat.mech_formation_x[place] : r->combat.formation_x[place]);
        int gy=(int)s->campaign.world_y+(vehicle ? r->combat.mech_formation_y[place] : r->combat.formation_y[place]);
        CHECK(btp_party_walkable(s,r,(int)x,(int)y,vehicle));
        CHECK(abs((int)x-gx)<=8 && abs((int)y-gy)<=8);
        if (exact) CHECK((int)x==gx && (int)y==gy);
    }
}
static void unchanged(const BtpState *s,const BtpState *before)
{
    CHECK(s->credits==before->credits && !memcmp(s->npc.rng,before->npc.rng,3));
    CHECK(!memcmp(s->party.people,before->party.people,sizeof s->party.people));
    CHECK(!memcmp(s->party.mech_types,before->party.mech_types,4));
    CHECK(!memcmp(s->campaign.mech,before->campaign.mech,125));
    CHECK(!memcmp(s->party.mechs,before->party.mechs,375));
}
int main(int argc,char **argv)
{
    CHECK(argc==5);BtpOriginalContentPaths paths={argv[1],argv[2],argv[3],argv[4]};
    BtpContent content={0};BtpError error;CHECK(btp_content_load_original(&content,&paths,&error));
    BtpResources *r=content.resources;
    BtpState *s=calloc(1,sizeof *s),*before=calloc(1,sizeof *before),*copy=calloc(1,sizeof *copy);CHECK(s && before && copy);
    /* Only the in-memory test map changes. Flat terrain isolates the recovery
       policy from town details; a second case adds a blocking roof. */
    memset(r->local[3].tiles,64,sizeof r->local[3].tiles);setup(s,r);formation(s,r,1);
    unsigned goal=s->party.mech_x[3];s->party.mech_x[3]=(uint16_t)(goal+12);*before=*s;
    btp_party_recover(s,r,0);CHECK(s->party.mech_x[3]==goal+12);unchanged(s,before);
    ++s->party.mech_x[3];btp_party_recover(s,r,0);formation(s,r,1);unchanged(s,before);
    /* Nearby but trapped units regroup when leaving the actual Space menu,
       inspector or overhead map, even without walking another step. */
    const unsigned pages[]={BTP_MENU_ROOT,BTP_MENU_MECH,BTP_MENU_MAP};
    for (unsigned i=0;i<3;++i) {
        setup(s,r);s->party.mech_x[2]+=8;s->party.x[5]+=8;*before=*s;
        btp_game_tick(s,r,BTP_OPEN_MENU);CHECK(s->mode==BTP_ACTIONS && s->party.mech_x[2]==before->party.mech_x[2]);
        s->campaign.ui=(uint8_t)pages[i];btp_game_tick(s,r,BTP_ACCEPT);
        CHECK(s->mode==BTP_EXPLORE);formation(s,r,1);unchanged(s,before);
    }
    setup(s,r);s->party.mech_x[2]+=8;btp_game_tick(s,r,BTP_OPEN_MENU);
    s->campaign.ui=BTP_MENU_SAVE;s->menu.io=BTP_MENU_IO_SAVE;
    int saved=btp_save_menu(s,r,"btp-recovery-save.btp",1,&error);
    if (!saved) fprintf(stderr,"Recovery save: %s\n",error.text);
    CHECK(saved);formation(s,r,1);
    CHECK(btp_save_load("btp-recovery-save.btp",copy,r,&error));formation(copy,r,1);CHECK(!remove("btp-recovery-save.btp"));
    /* At the final win/withdrawal message, regroup only after acknowledgement.
       The battle and its result processing must not teleport live combatants. */
    for (unsigned fled=0;fled<2;++fled) {
        setup(s,r);s->party.mech_x[2]+=8;*before=*s;
        s->mode=BTP_ENCOUNTER;s->campaign.encounter=1;s->campaign.return_map=s->map_id;
        s->campaign.return_x=s->x_half;s->campaign.return_y=s->y_half;
        s->aftermath.applied=3;s->aftermath.phase=(uint8_t)(fled ? 6 : 7);s->combat.fled=(uint8_t)fled;
        btp_party_recover(s,r,1);CHECK(s->party.mech_x[2]==before->party.mech_x[2]);
        btp_game_tick(s,r,BTP_ACCEPT);
        if (fled) {
            CHECK(s->mode==BTP_ENCOUNTER && s->party.mech_x[2]==before->party.mech_x[2]);
            btp_game_tick(s,r,BTP_ACCEPT);
        }
        CHECK(s->mode==BTP_EXPLORE && !s->campaign.encounter);
        formation(s,r,1);unchanged(s,before);
    }
    /* Exit a real building script, not a manually closed substitute menu. */
    setup(s,r);unsigned entry=0;
    while (entry<12 && r->local[3].room_map[entry]!=5) ++entry;
    CHECK(entry<12);s->entry_slot=(uint8_t)entry;btp_game_building(s,r,5);
    for (unsigned i=0;i<96 && s->script.status!=BTP_SCRIPT_MENU;++i) btp_game_tick(s,r,BTP_ACCEPT);
    CHECK(s->mode==BTP_BUILDING && s->script.status==BTP_SCRIPT_MENU);
    s->script.selected=(uint8_t)(btp_menu_count(s->script.menu_id)-1u);
    s->party.mech_x[2]+=8;s->party.x[5]+=8;btp_game_tick(s,r,BTP_ACCEPT);
    for (unsigned i=0;i<96 && s->mode==BTP_BUILDING;++i) btp_game_tick(s,r,BTP_ACCEPT);
    CHECK(s->mode==BTP_EXPLORE);formation(s,r,1);
    setup(s,r);r->local[3].tiles[15*32+16]=115;s->party.mech_x[0]-=20;*before=*s;
    btp_party_recover(s,r,1);formation(s,r,0);unchanged(s,before);
    /* Parked vehicles and wrecks share an inactive record byte. Neither is
       moved or resurrected, even if its receipt still marks an owned bay. */
    setup(s,r);s->campaign.mech[0]=s->party.mechs[0][0]=255;
    s->party.mech_x[0]=s->party.mech_x[1]=100;s->party.mech_y[0]=s->party.mech_y[1]=200;
    s->campaign.mounted=0;s->party.people[0][12]=s->party.people[1][12]=8;
    *before=*s;btp_party_recover(s,r,1);
    CHECK(s->party.mech_x[0]==100 && s->party.mech_x[1]==100 && s->party.mech_y[0]==200 && s->party.mech_y[1]==200);
    unchanged(s,before);formation(s,r,0);
    free(copy);free(before);free(s);btp_content_close(&content);
    printf("PASS: %u temporary formation recovery checks (menus, building, battle, distance, terrain and parked units)\n",checks);return 0;
}
