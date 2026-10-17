#include "core/world.h"
#include "core/campaign.h"
#include "core/menu.h"
#include "core/combat.h"
#include "frontend/pixels.h"
#include "data/save.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x);exit(1); } } while (0)
static void restore(BtpState *s,const BtpResources *r)
{
    uint8_t a[BTP_STATE_BYTES],b[BTP_STATE_BYTES];BtpState copy;
    btp_state_encode(s,a);CHECK(btp_state_decode(a,sizeof a,btp_active_map(r,s),btp_state_bld(r,s),&copy));
    btp_state_encode(&copy,b);CHECK(!memcmp(a,b,sizeof a));*s=copy;
}
int main(int argc,char **argv)
{
    if (argc!=2) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError error;
    CHECK(r && btp_resources_load(argv[1],r,&error));
    CHECK(btp_combat_data_load("work/combat-data.bin",&r->combat,&error));
    CHECK(btp_dialogue_load("work/talk-data.bin",&r->dialogue,&error));
    CHECK(btp_world_data_load("work/world-data.bin",&r->world,&error));
    FILE *f=fopen("tests/fixtures/world-marks-primary.txt","r");CHECK(f);
    char line[160];unsigned cases=0;
    while (fgets(line,sizeof line,f)) {
        unsigned index,sprite,want_sprite,sector,lx,ly,next;int x,y;BtpState s;btp_start(&s);
        CHECK(sscanf(line,"M %u %u %d %d %u %u %u %u %u",&index,&sprite,&x,&y,&want_sprite,&sector,&lx,&ly,&next)==9);
        s.terrain_next=(uint8_t)index;btp_world_mark(&s,sprite,x,y);const BtpTerrainMark *m=&s.terrain_marks[index];
        CHECK(m->sprite==want_sprite && m->sector==sector && m->x==lx && m->y==ly && s.terrain_next==next);
        restore(&s,r);++cases;
    }
    fclose(f);CHECK(cases==126);
    f=fopen("tests/fixtures/fire-primary.txt","r");CHECK(f);BtpState flame;
    unsigned fire_cases=0;
    while (fgets(line,sizeof line,f)) {
        unsigned cx,cy,x,y,sprite,frame,visible,before,after,px,py;
        CHECK(sscanf(line,"F %u %u %u %u %u %u %u %u %u %u %u",&cx,&cy,&x,&y,&sprite,&frame,&visible,&before,&after,&px,&py)==11);
        if (!frame) { btp_start(&flame);btp_world_mark(&flame,sprite,(int)x,(int)y); }
        CHECK(flame.terrain_marks[0].sprite==before);
        btp_world_animate_marks(&flame,(int)cx,(int)cy);
        CHECK(flame.terrain_marks[0].sprite==after);
        int dx=(int)x-(int)cx,dy=(int)y-(int)cy;
        CHECK(visible==(unsigned)(dx>=-13 && dx<=13 && dy>=-12 && dy<=12));
        if (visible) CHECK(px==(unsigned)(208+8*dx) && py==(unsigned)(96+8*dy));
        restore(&flame,r);++fire_cases;
    }
    fclose(f);CHECK(fire_cases==720);
    /* The actual encounter offer previously reproduced all map-0 wrecks at
       local coordinates. Sixty-four old casualties must leave its view clean. */
    BtpState s;CHECK(btp_save_load("Original DOS/GAME3",&s,r,&error));
    s.map_id=0;s.x_half=s.campaign.world_x=1400;s.y_half=s.campaign.world_y=1200;
    CHECK(btp_campaign_random(&s,r));
    memset(s.terrain_marks,0,sizeof s.terrain_marks);s.terrain_next=0;
    uint32_t *clean=malloc(BTP_PIXELS*sizeof *clean),*marked=malloc(BTP_PIXELS*sizeof *marked);CHECK(clean && marked);
    btp_render(r,&s,0,clean);
    for (unsigned i=0;i<64;++i) btp_world_mark(&s,126u+(i&3u),
        (int)s.campaign.battle_x+(int)s.x_half-128+(int)(i%8u)-4,
        (int)s.campaign.battle_y+(int)s.y_half+(int)(i/8u)-4);
    restore(&s,r);btp_render(r,&s,0,marked);CHECK(!memcmp(clean,marked,BTP_PIXELS*sizeof *clean));
    /* A casualty at this battlefield remains visible and survives a save. */
    btp_world_mark(&s,128,(int)s.campaign.battle_x+(int)s.x_half+5,
        (int)s.campaign.battle_y+(int)s.y_half-3);
    restore(&s,r);btp_render(r,&s,0,marked);CHECK(memcmp(clean,marked,BTP_PIXELS*sizeof *clean));
    /* v33 cannot identify a map-0 battle's origin. Migration clears only the
       ambiguous decoration; invalid original-format coordinates still fail. */
    BtpState old;btp_start(&old);old.terrain_next=1;old.terrain_marks[0]=(BtpTerrainMark){128,0,60,60};
    uint8_t bytes[BTP_STATE_BYTES];btp_state_encode(&old,bytes);memcpy(bytes,"BTPX",4);bytes[4]=33;
    BtpState migrated;CHECK(btp_state_decode(bytes,sizeof bytes,&r->map,NULL,&migrated));
    CHECK(!migrated.terrain_next && !migrated.terrain_marks[0].sprite && migrated.credits==old.credits);
    btp_state_encode(&old,bytes);bytes[2051]=128;CHECK(!btp_state_decode(bytes,sizeof bytes,&r->map,NULL,&migrated));
    btp_state_encode(&old,bytes);bytes[2049]=130;CHECK(!btp_state_decode(bytes,sizeof bytes,&r->map,NULL,&migrated));
    /* Declared post-combat outdoor prerequisite: persistent marks must draw
       during normal walking, hold between outdoor redraws, and survive saves. */
    CHECK(btp_save_load("Original DOS/GAME3",&s,r,&error));s.map_id=0;
    s.x_half=s.campaign.world_x=1400;s.y_half=s.campaign.world_y=1200;
    s.combat=(BtpCombatState){0};s.campaign.encounter=0;s.mode=BTP_EXPLORE;
    s.story_flags[58]=1; /* Keep this animation test free of random encounters. */
    memset(s.terrain_marks,0,sizeof s.terrain_marks);s.terrain_next=0;
    btp_render(r,&s,0,clean);btp_world_mark(&s,128,1405,1197);btp_world_mark(&s,124,1396,1202);
    btp_render(r,&s,0,marked);CHECK(memcmp(clean,marked,BTP_PIXELS*sizeof *clean));
    s.tick=0;btp_render(r,&s,0,clean);s.tick=1;btp_render(r,&s,0,marked);
    /* A host tick alone no longer changes the flame's two-frame sprite. */
    for (unsigned y=112;y<126;++y) CHECK(!memcmp(clean+y*320+176,marked+y*320+176,16*sizeof *clean));
    s.campaign.world_clock=0;unsigned changes=0;
    for (unsigned tick=0;tick<30;++tick) {
        unsigned previous=s.terrain_marks[1].sprite;btp_game_tick(&s,r,BTP_IDLE);restore(&s,r);
        changes+=s.terrain_marks[1].sprite!=previous;CHECK(s.terrain_marks[0].sprite==128);
    }
    CHECK(changes==6 && !s.combat.phase && s.mode==BTP_EXPLORE);
    CHECK(btp_save_write("work/weapon-presentation/outdoor-fire.btp",&s,r,&error));
    BtpState held=s;btp_menu_open(&s);unsigned previous=s.terrain_marks[1].sprite;
    for (unsigned tick=0;tick<20;++tick) btp_game_tick(&s,r,BTP_IDLE);
    CHECK(s.terrain_marks[1].sprite==previous);
    /* v40's old tick-driven visible frame migrates without jumping phase. */
    btp_state_encode(&held,bytes);memcpy(bytes,"BTPe",4);bytes[4]=40;
    CHECK(btp_state_decode(bytes,sizeof bytes,&r->map,NULL,&migrated));
    CHECK((migrated.terrain_marks[1].sprite^1u)==124u+(held.tick&1u));
    BtpState battle;btp_start(&battle);battle.mode=BTP_MISSION;
    battle.mission.phase=BTP_MISSION_DRIVE;battle.mission.assignment=2;btp_combat_begin(&battle,r);
    battle.combat.phase=BTP_COMBAT_ROUND;battle.combat.unit[0].x=battle.combat.unit[0].y=64;
    battle.combat.unit[1].x=battle.combat.unit[1].y=120;
    memset(battle.combat.path,2,sizeof battle.combat.path);
    btp_world_mark(&battle,124,1536+68,1536+66);
    btp_combat_tick(&battle,r,BTP_IDLE);CHECK(battle.terrain_marks[0].sprite==124);
    battle.combat.path[0][0][0]=1;battle.combat.path[0][0][1]=0;
    btp_combat_tick(&battle,r,BTP_IDLE);CHECK(battle.terrain_marks[0].sprite==125);
    btp_combat_tick(&battle,r,BTP_IDLE);CHECK(battle.terrain_marks[0].sprite==125);
    free(clean);free(marked);free(r);printf("PASS: %u world-mark checks, %u original writes and encounter rendering\n",checks,cases);return 0;
}
