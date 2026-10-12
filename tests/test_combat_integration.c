#include "core/combat.h"
#include "core/npc.h"
#include "frontend/pixels.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x);exit(1); } } while (0)
static void step(BtpState *s,const BtpResources *r,BtpAction action)
{
    uint8_t before[BTP_STATE_BYTES],after[BTP_STATE_BYTES];BtpState copy;
    btp_state_encode(s,before);
    CHECK(btp_state_decode(before,sizeof before,&r->map,btp_building_bld(r,s->entry_slot),&copy));
    btp_game_tick(s,r,action);btp_game_tick(&copy,r,action);
    btp_state_encode(s,before);btp_state_encode(&copy,after);CHECK(!memcmp(before,after,sizeof before));
}
static void command(BtpState *s,const BtpResources *r,unsigned wanted)
{
    CHECK(s->combat.phase==BTP_COMBAT_MENU);
    while (s->combat.selected!=wanted) step(s,r,BTP_DOWN);
    step(s,r,BTP_ACCEPT);
}
static void decline(const BtpState *menu,const BtpResources *r,unsigned loan)
{
    BtpState s=*menu;
    while (s.script.selected!=loan) step(&s,r,BTP_DOWN);
    step(&s,r,BTP_ACCEPT);
    for (unsigned i=0;s.cutscene.active && i<128;++i) step(&s,r,BTP_IDLE);
    CHECK(s.combat.phase==BTP_COMBAT_CONTROL && !s.cutscene.active);
    CHECK(!memcmp(s.combat.unit[0].record,r->combat.loans[loan],125));
    step(&s,r,BTP_UP);step(&s,r,BTP_ACCEPT);CHECK(s.combat.phase==BTP_COMBAT_NOTICE);
    step(&s,r,BTP_ACCEPT);step(&s,r,BTP_DOWN);step(&s,r,BTP_ACCEPT);
    step(&s,r,BTP_ACCEPT);step(&s,r,BTP_ACCEPT);CHECK(s.combat.phase==BTP_COMBAT_MENU);
    command(&s,r,6);step(&s,r,BTP_DOWN);CHECK(s.combat.scan_unit==1);step(&s,r,BTP_CANCEL);
    command(&s,r,0);step(&s,r,BTP_RIGHT);step(&s,r,BTP_CANCEL);CHECK(!s.combat.goal_active);
    command(&s,r,4);CHECK(s.combat.phase==BTP_COMBAT_KICK);step(&s,r,BTP_CANCEL);CHECK(s.combat.kick_target==255);
    command(&s,r,3);step(&s,r,BTP_ACCEPT);step(&s,r,BTP_CANCEL);CHECK(s.combat.orders[0]==255);
    step(&s,r,BTP_CANCEL);command(&s,r,8);CHECK(s.combat.fled && !s.combat.phase);
    for (unsigned i=0;i<4;++i) step(&s,r,BTP_LEFT);
    step(&s,r,BTP_IDLE);CHECK(s.mode==BTP_BUILDING && s.story_flags[0]==2 && !s.story_flags[1] && s.allowance_cap==250);
    step(&s,r,BTP_ACCEPT);CHECK(s.mode==BTP_EXPLORE && !s.mission.phase && !s.combat.fled);
}
static void glyph(const BtpResources *r,const uint32_t *frame,unsigned id,int x,int y)
{
    unsigned drawn=0;
    for (unsigned row=0;row<8;++row) for (unsigned col=0;col<8;++col)
        if (r->dialogue.font[id*8+row]&(128u>>col)) {
            CHECK(frame[(y+(int)row)*320+x+(int)col]==btp_palette[15]);++drawn;
        }
    CHECK(drawn>0);
}
static void route_pixels(const BtpState *menu,BtpResources *r)
{
    BtpState start=*menu;
    while (start.script.selected) step(&start,r,BTP_DOWN);
    step(&start,r,BTP_ACCEPT);
    while (start.cutscene.active) step(&start,r,BTP_IDLE);
    step(&start,r,BTP_ACCEPT);step(&start,r,BTP_ACCEPT);step(&start,r,BTP_ACCEPT);
    CHECK(start.combat.phase==BTP_COMBAT_MENU);
    BtpMap map=r->map;memset(r->map.tiles,64,sizeof r->map.tiles);
    uint8_t format=r->sprites.format;r->sprites.format=0;
    uint32_t *frame=malloc(BTP_PIXELS*sizeof *frame);CHECK(frame);
    /* Original 103B direction glyphs, compared against the owner's font pixels
       and actual movement in all eight directions, before/after confirmation. */
    static const int directions[8][3]={{0,-1,1},{1,-1,2},{1,0,3},{1,1,4},
        {0,1,5},{-1,1,6},{-1,0,7},{-1,-1,8}};
    for (unsigned i=0;i<8;++i) {
        BtpState s=start;int dx=directions[i][0],dy=directions[i][1];unsigned id=(unsigned)directions[i][2];
        s.combat.phase=BTP_COMBAT_MOVE;s.combat.selected=0;
        s.combat.cursor_x=(uint8_t)(64+4*dx);s.combat.cursor_y=(uint8_t)(77+4*dy);
        BtpState unchanged=s;btp_render(r,&s,0,frame);CHECK(!memcmp(&s,&unchanged,sizeof s));
        glyph(r,frame,id,208-3*dx*8,72-3*dy*8);
        step(&s,r,BTP_ACCEPT);CHECK(s.combat.goal_active);
        btp_render(r,&s,0,frame);glyph(r,frame,id,208+dx*8,72+dy*8);
        step(&s,r,BTP_ACCEPT);step(&s,r,BTP_IDLE);
        CHECK(s.combat.unit[0].x==64+dx && s.combat.unit[0].y==77+dy);
        btp_render(r,&s,0,frame);glyph(r,frame,id,208+dx*8,72+dy*8);
    }
    free(frame);r->map=map;r->sprites.format=format;
}
int main(int argc,char **argv)
{
    if (argc!=5) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError error;CHECK(r);
    CHECK(btp_resources_load(argv[1],r,&error));CHECK(btp_dialogue_load(argv[2],&r->dialogue,&error));
    CHECK(btp_combat_data_load(argv[3],&r->combat,&error));
    BtpState s,menu={0};btp_start(&s);btp_npc_init(&s,&r->map);
    FILE *file=fopen(argv[4],"r");CHECK(file);char line[40];unsigned ticks=0,combat_ticks=0,effects=0;
    uint8_t enemy_x=0,enemy_y=0;
    while (fgets(line,sizeof line,file)) {
        line[strcspn(line,"\r\n")]=0;BtpAction action;CHECK(btp_action_parse(line,&action));
        if (s.story_flags[0]==2 && s.script.status==BTP_SCRIPT_MENU && s.script.menu_id==7) menu=s;
        int round=s.combat.phase==BTP_COMBAT_ROUND;BtpState no_graphics=s;
        no_graphics.combat.graphics=0;no_graphics.combat.flash=0;
        if (round) btp_game_tick(&no_graphics,r,action);
        step(&s,r,action);++ticks;combat_ticks+=s.combat.phase!=0;
        if (round) {
            no_graphics.combat.graphics=s.combat.graphics;no_graphics.combat.flash=s.combat.flash;
            uint8_t visible[BTP_STATE_BYTES],invisible[BTP_STATE_BYTES];
            btp_state_encode(&s,visible);btp_state_encode(&no_graphics,invisible);
            CHECK(!memcmp(visible,invisible,sizeof visible));
        }
        if (s.combat.phase && !s.effects.pending) {
            if (!enemy_x) { enemy_x=s.combat.unit[1].x;enemy_y=s.combat.unit[1].y; }
            CHECK(s.combat.unit[1].x==enemy_x && s.combat.unit[1].y==enemy_y && s.combat.unit[1].direction==6);
        }
        if (s.combat.flash && !s.effects.pending) {
            ++effects;
            uint8_t old[BTP_STATE_BYTES];BtpState migrated;
            btp_state_encode(&s,old);memcpy(old+512,old+4096,384);memcpy(old,"BTPD",4);old[4]=13;old[878]=0;
            memset(old+896,0,sizeof old-896);
            CHECK(btp_state_decode(old,1024,&r->map,&r->training,&migrated));CHECK(!migrated.combat.flash);
            memcpy(old,"BTPE",4);old[4]=14;old[878]=s.combat.flash;
            CHECK(btp_state_decode(old,1024,&r->map,&r->training,&migrated));CHECK(migrated.combat.flash==s.combat.flash);
        }
        if (s.combat.phase==BTP_COMBAT_ROUND && s.combat.step==1) {
            uint8_t bad[BTP_STATE_BYTES];BtpState untouched=s;
            btp_state_encode(&s,bad);bad[896]=1;
            CHECK(!btp_state_decode(bad,sizeof bad,&r->map,&r->training,&untouched));CHECK(!memcmp(&untouched,&s,sizeof s));
            btp_state_encode(&s,bad);bad[512+125+2]=8;
            CHECK(!btp_state_decode(bad,sizeof bad,&r->map,&r->training,&untouched));CHECK(!memcmp(&untouched,&s,sizeof s));
            btp_state_encode(&s,bad);bad[878]=4;
            CHECK(!btp_state_decode(bad,sizeof bad,&r->map,&r->training,&untouched));CHECK(!memcmp(&untouched,&s,sizeof s));
            /* A v13 save may contain a target path from the previous build.
               Loading it must still leave the shell stationary. */
            BtpState old=s,loaded;old.combat.flash=0;old.combat.delay=0;old.combat.path_index[1]=0;
            old.combat.path[1][0][0]=-1;old.combat.path[1][0][1]=0;
            btp_state_encode(&old,bad);memcpy(bad+512,bad+4096,384);memcpy(bad,"BTPD",4);bad[4]=13;
            memset(bad+896,0,sizeof bad-896);
            CHECK(btp_state_decode(bad,1024,&r->map,&r->training,&loaded));
            step(&loaded,r,BTP_IDLE);CHECK(loaded.combat.unit[1].x==enemy_x && loaded.combat.unit[1].y==enemy_y);
        }
    }
    fclose(file);CHECK(s.mode==BTP_EXPLORE && s.story_flags[0]==3 && s.story_flags[1]==1 && s.allowance_cap==500);
    CHECK(menu.story_flags[0]==2 && combat_ticks>100 && effects>0);
    for (unsigned loan=0;loan<3;++loan) decline(&menu,r,loan);
    route_pixels(&menu,r);
    btp_start(&s);uint8_t old[BTP_STATE_BYTES];BtpState migrated;
    btp_state_encode(&s,old);memcpy(old,"BTPC",4);old[4]=12;
    CHECK(btp_state_decode(old,512,&r->map,&r->training,&migrated));CHECK(!memcmp(&s,&migrated,sizeof s));
    free(r);printf("PASS: %u combat integration assertions; %u input continuations, three loans and flee results\n",checks,ticks);
    return 0;
}
