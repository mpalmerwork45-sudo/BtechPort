#include "core/combat.h"
#include "core/campaign.h"
#include "core/party.h"
#include "data/save.h"
#include "frontend/pixels.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
static unsigned checks;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x);exit(1); } } while (0)
static uint64_t left_hash(const uint32_t *pixels)
{
    uint64_t h=UINT64_C(14695981039346656037);
    for (unsigned y=0;y<200;++y) for (unsigned x=0;x<104;++x) for (int shift=16;shift>=0;shift-=8)
        h=(h^(uint8_t)(pixels[y*320+x]>>shift))*UINT64_C(1099511628211);
    return h;
}
static void setup(BtpState *s,const BtpResources *r)
{
    BtpError e;CHECK(btp_save_load("Original DOS/GAME3",s,r,&e));
    s->party.people[3][12]=8;s->campaign.mech[122]=255;
    s->campaign.encounter=1;s->mode=BTP_ENCOUNTER;s->x_half=64;s->y_half=66;
    s->combat=(BtpCombatState){.phase=BTP_COMBAT_MENU,.selected=9,.count=6,.friends=4,.target_unit=4,
        .last_target=4,.movement=255,.kick_target=255,.enemy_movement=255};
    BtpCombatState *c=&s->combat;memset(c->orders,255,11);memset(c->enemy_orders,255,sizeof c->enemy_orders);
    memset(c->enemy_modes,255,sizeof c->enemy_modes);
    for (unsigned i=0;i<4;++i) {
        c->plans[i].movement=c->plans[i].kick=255;memset(c->plans[i].orders,255,11);
        c->ids[i]=(uint8_t)(i==3 ? 7 : i);c->unit[i].x=(uint8_t)(64+2*i);c->unit[i].y=64;
        memcpy(c->unit[i].record,i==3 ? s->party.people[3] : btp_party_mech(s,i),i==3 ? 17u : 125u);
    }
    c->unit[3].infantry=1;c->unit[3].x=64;c->ids[4]=13;c->ids[5]=17;
    memcpy(c->unit[4].record,r->combat.loans[0],125);c->unit[4].x=47;c->unit[4].y=47;
    /* The source's first visible enemy human is ID17 with a Shotgun and
       full health. Equivalent relative coordinates retain its NW bearing. */
    const uint8_t human[17]={1,12,6,0,1,3,1,3,1,0,0,4,8,3,12,120,0};
    memcpy(c->unit[5].record,human,17);c->unit[5].infantry=1;c->unit[5].x=47;c->unit[5].y=47;
    s->campaign.battle_x=1152;s->campaign.battle_y=1664;
}
static void step(BtpState *s,const BtpResources *r,BtpAction a)
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
    CHECK(btp_dialogue_load("work/talk-data.bin",&r->dialogue,&e));CHECK(btp_combat_data_load("work/combat-data.bin",&r->combat,&e));
    CHECK(btp_world_data_load("work/world-data.bin",&r->world,&e));
    uint32_t *frame=malloc(BTP_PIXELS*sizeof *frame);CHECK(frame);
    FILE *f=fopen("tests/fixtures/combat-ui-primary.txt","r");CHECK(f);unsigned index,cases=0;uint64_t expected;
    while (fscanf(f," U %u %" SCNx64,&index,&expected)==2) {
        BtpState s;setup(&s,r);BtpCombatState *c=&s.combat;
        if (index==1 || index==2) { btp_combat_select(c,index);c->selected=7; }
        if (index>=3) { btp_combat_select(c,3);c->selected=7; }
        if (index==4 || index==7) { c->phase=BTP_COMBAT_SCAN_CHOICE;c->selected=0; }
        if (index==5 || index==6 || index==8) {
            c->phase=BTP_COMBAT_SCAN;c->selected=0;c->scan_unit=(uint8_t)(index==5 ? 0 : index==6 ? 3 : 5);
            c->target_selected=(uint8_t)(index==8);
        }
        if (index==7) { c->phase=BTP_COMBAT_NOTICE;c->notice=15;c->notice_return=BTP_COMBAT_SCAN_CHOICE;c->selected=c->target_selected=1; }
        btp_render(r,&s,0,frame);uint64_t actual=left_hash(frame);
        if (actual!=expected) { fprintf(stderr,"Original UI case %u: %016" PRIx64 " / %016" PRIx64 "\n",index,actual,expected);CHECK(btp_write_ppm("work/combat-ui-failed.ppm",frame)); }
        CHECK(actual==expected);++cases;
    }
    fclose(f);CHECK(cases==9);
    BtpState s;setup(&s,r);BtpCombatState *c=&s.combat;btp_combat_select(c,3);
    CHECK(btp_combat_menu_count(c)==8);c->selected=9;step(&s,r,BTP_DOWN);CHECK(c->selected==0);
    step(&s,r,BTP_ACCEPT);CHECK(c->phase==BTP_COMBAT_MOVE);step(&s,r,BTP_RIGHT);step(&s,r,BTP_ACCEPT);CHECK(c->goal_active);
    c->selected=10;step(&s,r,BTP_ACCEPT);CHECK(!c->goal_active && !c->waypoint_count && c->movement==255 && !c->plans[3].active);
    c->selected=6;step(&s,r,BTP_ACCEPT);CHECK(c->phase==BTP_COMBAT_SCAN_CHOICE);step(&s,r,BTP_ACCEPT);
    CHECK(c->phase==BTP_COMBAT_SCAN && c->scan_unit==0);step(&s,r,BTP_DOWN);step(&s,r,BTP_ACCEPT);
    CHECK(c->phase==BTP_COMBAT_SCAN_DETAIL);step(&s,r,BTP_OPEN_MENU);CHECK(c->phase==BTP_COMBAT_SCAN);
    for (unsigned i=0;i<3;++i) step(&s,r,BTP_ACCEPT);
    CHECK(c->scan_unit==3 && !btp_combat_scan_detail(c));
    step(&s,r,BTP_DOWN);step(&s,r,BTP_ACCEPT);CHECK(c->phase==BTP_COMBAT_MENU && c->selected==6);
    step(&s,r,BTP_ACCEPT);step(&s,r,BTP_DOWN);step(&s,r,BTP_ACCEPT);CHECK(c->phase==BTP_COMBAT_NOTICE && c->notice==15);
    step(&s,r,BTP_OPEN_MENU);CHECK(c->phase==BTP_COMBAT_SCAN && c->scan_unit==5);step(&s,r,BTP_ACCEPT);CHECK(c->scan_unit==5);
    step(&s,r,BTP_CANCEL);CHECK(c->phase==BTP_COMBAT_MENU);
    btp_combat_select(c,0);c->unit[0].record[119]=2;c->selected=6;step(&s,r,BTP_ACCEPT);step(&s,r,BTP_DOWN);step(&s,r,BTP_ACCEPT);
    CHECK(c->phase==BTP_COMBAT_NOTICE && c->notice==16);step(&s,r,BTP_ACCEPT);CHECK(c->scan_unit==5);
    setup(&s,r);btp_combat_select(&s.combat,3);s.combat.selected=7;
    CHECK(btp_save_write("work/combat-ui-start.btp",&s,r,&e));
    free(frame);free(r);printf("PASS: %u checks; nine original combat UI regions, foot moves and saved friend/enemy scans\n",checks);return 0;
}
