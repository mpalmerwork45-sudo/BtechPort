#include "core/combat.h"
#include "core/animation.h"
#include "core/party.h"
#include "core/world.h"
#include "frontend/pixels.h"
#include "data/save.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x);exit(1); } } while (0)
static void input(BtpState *s,const BtpResources *r,BtpAction action)
{
    uint8_t a[BTP_STATE_BYTES],b[BTP_STATE_BYTES];BtpState copy;btp_state_encode(s,a);
    CHECK(btp_state_decode(a,sizeof a,btp_active_map(r,s),btp_state_bld(r,s),&copy));
    btp_game_tick(s,r,action);btp_game_tick(&copy,r,action);btp_state_encode(s,a);btp_state_encode(&copy,b);CHECK(!memcmp(a,b,sizeof a));
}
static void anchors(BtpResources *r)
{
    FILE *file=fopen("tests/fixtures/combat-anchors-primary.txt","r");CHECK(file);
    unsigned id,x,y,px,py,cases=0;
    uint32_t actual[BTP_PIXELS],expected[BTP_PIXELS];
    while (fscanf(file," S %u %u %u %u %u",&id,&x,&y,&px,&py)==5) {
        BtpState s;btp_start(&s);s.mode=BTP_ENCOUNTER;
        s.combat=(BtpCombatState){.phase=BTP_COMBAT_SCAN,.friends=1,.count=2,.movement=255};
        s.combat.unit[0]=(BtpCombatUnit){.x=64,.y=64};s.combat.unit[0].record[0]=255;
        BtpCombatUnit *u=&s.combat.unit[1];u->x=(uint8_t)x;u->y=(uint8_t)y;
        u->infantry=(uint8_t)((id>=4 && id<12) || id>=16);u->record[0]=255;s.combat.ids[1]=(uint8_t)id;
        btp_render(r,&s,0,expected);u->record[0]=(uint8_t)(u->infantry ? 1 : 'C');
        btp_render(r,&s,0,actual);unsigned terrain;
        CHECK(btp_draw_sprite(&r->sprites,u->infantry ? 270u : btp_mech_sprite_base('C',1),
            (int)px,(int)py,btp_combat_cover(&r->map,u,&terrain),104,expected));
        CHECK(!memcmp(actual,expected,sizeof actual));++cases;
    }
    fclose(file);CHECK(cases==50);
}
static void paths(BtpResources *r)
{
    BtpState s;btp_start(&s);s.story_flags[4]=1;s.campaign.encounter=1;
    s.campaign.battle_x=1280;s.campaign.battle_y=1024;
    BtpMap map;btp_combat_map(r,&s,&map);unsigned paths=0;
    /* Real Starport tiles, every legal half-step and eight goals. Both
       manual and computer paths must keep each infantry foot off roofs. */
    for (int y=2;y<126;++y) for (int x=2;x<124;++x) if (btp_map_tile(&map,(x+1)/2,y/2)<85)
    for (int dy=-1;dy<=1;++dy) for (int dx=-1;dx<=1;++dx) if (dx || dy) for (int ai=0;ai<2;++ai) {
        BtpCombatUnit u={.infantry=1,.x=(uint8_t)x,.y=(uint8_t)y,.direction=6};u.record[2]=12;
        int8_t path[12][2];btp_combat_plan(&map,85,&u,NULL,x+dx*8,y+dy*8,0,ai,path);++paths;
        int px=x,py=y;
        for (unsigned i=0;i<12;++i) {
            if (path[i][0]==2 || path[i][1]==2) break;
            px+=path[i][0];py+=path[i][1];CHECK(btp_map_tile(&map,(px+1)/2,py/2)<85);
        }
    }
    CHECK(paths==121024);
}
static void formations(BtpResources *r)
{
    FILE *file=fopen("tests/fixtures/town-formation-primary.txt","r");CHECK(file);
    char line[512],key[20];BtpState s={0};BtpError e;unsigned cases=0,exact=0;
    while (fgets(line,sizeof line,file)) {
        unsigned town,x,y,people,mechs;int used;
        CHECK(sscanf(line,"F %u %19s %u %u %u %u%n",&town,key,&x,&y,&people,&mechs,&used)==6);
        if (!strcmp(key,"idle")) {
            CHECK(btp_save_load("Original DOS/GAME3",&s,r,&e));s.map_id=(uint8_t)town;s.story_flags[36]=255;
            s.campaign.world_x=(uint16_t)x;s.campaign.world_y=(uint16_t)y;
            s.x_half=(uint16_t)(x&127u);s.y_half=(uint16_t)(y&127u);s.campaign.mounted=(uint8_t)(town==4);
            if (town==4) {
                for (unsigned i=0;i<3;++i) { btp_party_mech(&s,i)[0]=s.party.mech_types[i];s.party.people[i][12]=(uint8_t)i; }
                btp_party_mech(&s,0)[122]=255;s.party.people[3][12]=8;
            } else {
                for (unsigned i=0;i<8;++i) s.party.people[i][12]=8;
                for (unsigned i=0;i<4;++i) btp_party_mech(&s,i)[0]=255;
            }
            for (unsigned i=0;i<8;++i) { s.party.x[i]=(uint16_t)x;s.party.y[i]=(uint16_t)y; }
            for (unsigned i=0;i<4;++i) { s.party.mech_x[i]=(uint16_t)x;s.party.mech_y[i]=(uint16_t)y; }
            btp_party_follow(&s,r,(uint16_t)x,(uint16_t)y);
        } else { BtpAction action;CHECK(btp_action_parse(key,&action));input(&s,r,action); }
        if (s.campaign.world_x!=x || s.campaign.world_y!=y) fprintf(stderr,"Town %u observation %u cursor %u,%u expected %u,%u\n",town,cases,s.campaign.world_x,s.campaign.world_y,x,y);
        CHECK(s.campaign.world_x==x && s.campaign.world_y==y);
        const char *at=line+used;
        for (unsigned i=0;i<people+mechs;++i) {
            unsigned slot,fx,fy;CHECK(sscanf(at,"%u %u %u%n",&slot,&fx,&fy,&used)==3);at+=used;
            int mech=i>=people;unsigned ax=mech ? s.party.mech_x[slot] : s.party.x[slot],ay=mech ? s.party.mech_y[slot] : s.party.y[slot];
            CHECK(btp_party_walkable(&s,r,(int)ax,(int)ay,mech));
            if (ax!=fx || ay!=fy) fprintf(stderr,"Town %u observation %u %s %u: %u,%u expected %u,%u\n",town,cases,mech ? "mech" : "person",slot,ax,ay,fx,fy);
            CHECK(ax==fx && ay==fy);++exact;
        }
        ++cases;
    }
    fclose(file);CHECK(cases==40 && exact==160);
    printf("Town observations: %u, exact members %u\n",cases,exact);
}
static void collision(BtpResources *r)
{
    FILE *file=fopen("tests/fixtures/formation-collision-primary.txt","r");CHECK(file);
    unsigned town,x,y,people,mechs,blocked,cases=0;int dx,dy;
    while (fscanf(file," F %u %u %u %u %u %d %d %u",&town,&x,&y,&people,&mechs,&dx,&dy,&blocked)==8) {
        BtpState s;btp_start(&s);s.story_flags[4]=1;s.map_id=(uint8_t)town;btp_party_init(&s);
        for (unsigned i=0;i<8;++i) { s.party.people[i][0]=(uint8_t)(i<people ? i : 255);s.party.people[i][12]=8; }
        for (unsigned i=0;i<4;++i) btp_party_mech(&s,i)[0]=(uint8_t)(i<mechs ? 'L' : 255);
        int allowed=btp_party_can_stand(&s,r,(int)x+dx,(int)y+dy);
        if (allowed==(int)blocked) fprintf(stderr,"Formation %u town %u at %u,%u: %u foot %u mechs, delta %d,%d\n",cases,town,x,y,people,mechs,dx,dy);
        CHECK(allowed!=(int)blocked);++cases;
    }
    fclose(file);CHECK(cases==1920);
    file=fopen("tests/fixtures/formation-entrance-primary.txt","r");CHECK(file);cases=0;int door;
    while (fscanf(file," E %u %u %u %u %u %d %d %d %u",&town,&x,&y,&people,&mechs,&dx,&dy,&door,&blocked)==9) {
        BtpState s;btp_start(&s);s.story_flags[4]=1;s.map_id=(uint8_t)town;btp_party_init(&s);
        for (unsigned i=0;i<8;++i) { s.party.people[i][0]=(uint8_t)(i<people ? i : 255);s.party.people[i][12]=8; }
        for (unsigned i=0;i<4;++i) btp_party_mech(&s,i)[0]=(uint8_t)(i<mechs ? 'L' : 255);
        const BtpMap *map=btp_active_map(r,&s);
        int entry=btp_party_entrance(&s,r,map,(int)(x&127u)+dx,(int)(y&127u)+dy);
        if (entry!=door) fprintf(stderr,"Entry case %u: %d expected %d\n",cases,entry,door);
        CHECK(entry==door);CHECK(btp_party_can_stand(&s,r,(int)x+dx,(int)y+dy)!=(int)blocked);++cases;
    }
    fclose(file);CHECK(cases==480);
    file=fopen("tests/fixtures/town-boundaries-primary.txt","r");CHECK(file);cases=0;unsigned towns=0;
    while (fscanf(file," E %u %u %u %u %u %d %d %d %u",&town,&x,&y,&people,&mechs,&dx,&dy,&door,&blocked)==9) {
        BtpState s;btp_start(&s);s.story_flags[4]=(uint8_t)(town!=1);s.map_id=(uint8_t)town;btp_party_init(&s);
        for (unsigned i=0;i<8;++i) { s.party.people[i][0]=(uint8_t)(i<people ? i : 255);s.party.people[i][12]=8; }
        for (unsigned i=0;i<4;++i) btp_party_mech(&s,i)[0]=(uint8_t)(i<mechs ? 'L' : 255);
        const BtpMap *map=btp_active_map(r,&s);
        int water=btp_world_deep_crossing(r,&s,x,y,dx,dy);
        int entry=water ? -1 : btp_party_entrance(&s,r,map,(int)(x&127u)+dx,(int)(y&127u)+dy);
        int rejected=water || !btp_party_can_stand(&s,r,(int)x+dx,(int)y+dy);
        if (entry!=door || rejected!=(int)blocked) fprintf(stderr,"Extended boundary %u town %u at %u,%u %u/%u delta %d,%d: entry %d/%d block %d/%u\n",cases,town,x,y,people,mechs,dx,dy,entry,door,rejected,blocked);
        CHECK(entry==door && rejected==(int)blocked);towns|=1u<<town;++cases;
    }
    fclose(file);CHECK(cases>10000 && towns==16382);printf("Extended original town boundaries: %u\n",cases);
}
int main(int argc,char **argv)
{
    if (argc!=2) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError e;
    CHECK(r && btp_resources_load(argv[1],r,&e));CHECK(btp_world_data_load("work/world-data.bin",&r->world,&e));
    CHECK(btp_combat_data_load("work/combat-data.bin",&r->combat,&e));CHECK(btp_dialogue_load("work/talk-data.bin",&r->dialogue,&e));
    anchors(r);paths(r);formations(r);collision(r);
    free(r);printf("PASS: %u town movement checks, 50 original anchors and 121024 Starport paths\n",checks);return 0;
}
