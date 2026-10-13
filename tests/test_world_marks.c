#include "core/world.h"
#include "core/campaign.h"
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
    free(clean);free(marked);free(r);printf("PASS: %u world-mark checks, %u original writes and encounter rendering\n",checks,cases);return 0;
}
