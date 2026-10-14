#include "core/combat.h"
#include "core/npc.h"
#include "core/audio.h"
#include "core/effects.h"
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
    if (!loan) {
        BtpState computer=s;
        step(&computer,r,BTP_UP);step(&computer,r,BTP_ACCEPT);
        CHECK(computer.combat.automatic==1 && computer.combat.auto_run && computer.combat.phase==BTP_COMBAT_MESSAGES);
        step(&computer,r,BTP_ACCEPT);step(&computer,r,BTP_ACCEPT);step(&computer,r,BTP_IDLE);
        CHECK(computer.combat.phase==BTP_COMBAT_ROUND);
        unsigned enemy_x=computer.combat.unit[1].x,enemy_y=computer.combat.unit[1].y;
        unsigned steps=0;
        while (!computer.effects.count && computer.combat.phase && steps++<4096) step(&computer,r,BTP_IDLE);
        CHECK(computer.effects.count && computer.combat.unit[1].x==enemy_x && computer.combat.unit[1].y==enemy_y);
        step(&computer,r,BTP_OPEN_MENU);CHECK(computer.combat.paused && computer.combat.phase==BTP_COMBAT_ROUND);
        while (computer.combat.phase==BTP_COMBAT_ROUND && steps++<4096) step(&computer,r,BTP_IDLE);
        CHECK(computer.combat.phase==BTP_COMBAT_MENU && computer.combat.paused);
        unsigned round=computer.combat.round;step(&computer,r,BTP_IDLE);CHECK(computer.combat.round==round);
        command(&computer,r,9);
        while (computer.combat.phase && steps++<12000) step(&computer,r,BTP_IDLE);
        CHECK(computer.combat.won && computer.mission.phase==BTP_MISSION_RETURN);
    }
    step(&s,r,BTP_ACCEPT);
    step(&s,r,BTP_ACCEPT);step(&s,r,BTP_ACCEPT);CHECK(s.combat.phase==BTP_COMBAT_MENU);
    command(&s,r,6);CHECK(s.combat.phase==BTP_COMBAT_SCAN_CHOICE);
    step(&s,r,BTP_DOWN);step(&s,r,BTP_ACCEPT);CHECK(s.combat.phase==BTP_COMBAT_SCAN && s.combat.scan_unit==1);
    step(&s,r,BTP_DOWN);step(&s,r,BTP_ACCEPT);CHECK(s.combat.phase==BTP_COMBAT_SCAN_DETAIL);
    step(&s,r,BTP_CANCEL);step(&s,r,BTP_CANCEL);
    command(&s,r,0);step(&s,r,BTP_RIGHT);step(&s,r,BTP_CANCEL);CHECK(!s.combat.goal_active);
    command(&s,r,4);CHECK(s.combat.phase==BTP_COMBAT_KICK);step(&s,r,BTP_CANCEL);CHECK(s.combat.kick_target==255);
    command(&s,r,3);step(&s,r,BTP_ACCEPT);step(&s,r,BTP_CANCEL);CHECK(s.combat.orders[0]==255);
    step(&s,r,BTP_CANCEL);command(&s,r,8);CHECK(s.combat.fled && !s.combat.phase);
    CHECK(s.mission.phase==BTP_MISSION_RETURN);step(&s,r,BTP_ACCEPT);
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
        glyph(r,frame,id,208-3*dx*8,88-3*dy*8);
        step(&s,r,BTP_ACCEPT);CHECK(s.combat.goal_active);
        btp_render(r,&s,0,frame);glyph(r,frame,id,208+dx*8,88+dy*8);
        step(&s,r,BTP_ACCEPT);step(&s,r,BTP_IDLE);
        CHECK(s.combat.unit[0].x==64+dx && s.combat.unit[0].y==77+dy);
        btp_render(r,&s,0,frame);glyph(r,frame,id,208+dx*8,88+dy*8);
    }
    free(frame);r->map=map;r->sprites.format=format;
}
static void sequential_audio(const BtpState *menu,BtpResources *r)
{
    BtpState s=*menu;while (s.script.selected) step(&s,r,BTP_DOWN);step(&s,r,BTP_ACCEPT);
    while (s.cutscene.active) step(&s,r,BTP_IDLE);
    step(&s,r,BTP_ACCEPT);step(&s,r,BTP_ACCEPT);step(&s,r,BTP_ACCEPT);
    /* Controlled presentation prerequisite: three different attacks, with an
       outtake attached to the first. No numeric hit-rule parity is inferred. */
    s.combat.phase=BTP_COMBAT_ROUND;s.combat.step=11;s.combat.shot=(BtpShot){.hit=1};
    s.effects=(BtpEffectsState){0};s.audio=(BtpAudioState){0};
    btp_effects_shot(&s,0,1,17);btp_effects_shot(&s,0,1,9);btp_effects_shot(&s,0,1,6);
    s.effects.outtakes[0][0]=4;
    const unsigned expected[]={2,4,3,4,11,4};unsigned sound=0,ticks=0,outtake=0;
    while ((s.effects.count || s.presentation.count || s.cutscene.active) && ticks++<4096) {
        unsigned count=s.effects.count,stage=s.effects.stage,age=s.effects.age,busy=s.audio.sound_count;
        uint8_t encoded[BTP_STATE_BYTES],again[BTP_STATE_BYTES];BtpState copy;int16_t a[BTP_AUDIO_TICK_SAMPLES],b[BTP_AUDIO_TICK_SAMPLES];
        btp_state_encode(&s,encoded);CHECK(btp_state_decode(encoded,sizeof encoded,&r->map,&r->training,&copy));
        btp_game_tick_audio(&s,r,BTP_IDLE,a);btp_game_tick_audio(&copy,r,BTP_IDLE,b);
        btp_state_encode(&s,encoded);btp_state_encode(&copy,again);
        CHECK(!memcmp(encoded,again,sizeof encoded) && !memcmp(a,b,sizeof a));
        CHECK(s.audio.sound_count<=1 && s.combat.phase==BTP_COMBAT_ROUND && s.combat.step==11);
        if (busy) CHECK(s.effects.count==count && s.effects.age==age);
        if (count && stage==BTP_EFFECT_START && s.effects.stage==BTP_EFFECT_FIRE_SOUND) {
            CHECK(sound<6 && btp_effects_sound(s.effects.shots[0].weapon)==expected[sound++]);
            if (s.audio.sound_count) CHECK(s.audio.sounds[0]==expected[sound-1]);
            if (count==2) CHECK(outtake);
        }
        if (stage==BTP_EFFECT_ATTACK && s.effects.stage==BTP_EFFECT_HIT_SOUND) {
            CHECK(sound<6 && expected[sound++]==4);
            if (s.audio.sound_count) CHECK(s.audio.sounds[0]==4);
        }
        if (s.cutscene.active) { CHECK(!s.audio.sound_count && s.effects.count==2);outtake=1; }
    }
    CHECK(ticks<4096 && sound==6 && outtake && !s.audio.sound_count);
    s.effects.pending=1;s.combat.shot.destroyed=1;s.combat.unit[1].record[0]=255;
    step(&s,r,BTP_IDLE);
    CHECK(s.mission.phase==BTP_MISSION_RETURN && !s.audio.sound_count && !s.effects.count && !s.presentation.count);
    step(&s,r,BTP_ACCEPT);CHECK(!s.audio.sound_count);
}
static void death_pixels(const BtpState *menu,BtpResources *r)
{
    BtpState start=*menu;while (start.script.selected) step(&start,r,BTP_DOWN);step(&start,r,BTP_ACCEPT);
    while (start.cutscene.active) step(&start,r,BTP_IDLE);
    step(&start,r,BTP_ACCEPT);step(&start,r,BTP_ACCEPT);step(&start,r,BTP_ACCEPT);
    BtpMap original=r->map;memset(r->map.tiles,64,sizeof r->map.tiles);
    uint32_t *living=malloc(BTP_PIXELS*sizeof *living),*queued=malloc(BTP_PIXELS*sizeof *queued);CHECK(living && queued);
    for (unsigned human=0;human<2;++human) {
        BtpState s=start;s.combat.phase=BTP_COMBAT_ROUND;s.combat.flash=0;
        unsigned tx=s.combat.unit[0].x+4u,ty=s.combat.unit[0].y;
        CHECK(tx<127 && ty>1);
        s.combat.unit[1].x=(uint8_t)tx;s.combat.unit[1].y=(uint8_t)ty;s.combat.unit[1].infantry=(uint8_t)human;s.combat.unit[1].cover=0;
        if (human) {
            s.story_flags[0]=s.mission.assignment=3;s.combat.count=4;
            memset(s.combat.unit[1].record,0,125);
            const uint8_t person[17]={1,6,0,0,0,0,0,0,0,0,0,9,8,0,0,60,0};
            memcpy(s.combat.unit[1].record,person,17);s.combat.ids[1]=16;
            for (unsigned i=2;i<4;++i) {
                memcpy(s.combat.unit[i].record,person,17);s.combat.unit[i].record[0]=255;
                s.combat.unit[i].infantry=1;s.combat.unit[i].x=s.combat.unit[i].y=127;
            }
        }
        s.effects=(BtpEffectsState){0};s.audio=(BtpAudioState){0};
        btp_render(r,&s,0,living);
        s.combat.shot=(BtpShot){.hit=1};btp_effects_shot(&s,0,1,17);
        s.combat.shot.destroyed=1;btp_effects_shot(&s,0,1,17);
        s.effects.stage=BTP_EFFECT_FIRE_SOUND;
        s.terrain_marks[0]=(BtpTerrainMark){(uint8_t)(human ? 126 : 128),0xcc,(uint8_t)(tx-!human),(uint8_t)(ty-!human)};
        s.combat.unit[1].record[0]=255;s.combat.unit[1].x=s.combat.unit[1].y=127;
        CHECK(btp_effects_pending_death(&s,1)==&s.effects.shots[1]);
        btp_render(r,&s,0,queued);
        /* The later shot's wreck cannot appear while an earlier shot plays.
           Compare the whole map viewport to the live pre-destruction scene. */
        for (unsigned y=0;y<200;++y) CHECK(!memcmp(living+y*320+104,queued+y*320+104,216*sizeof *living));
        uint8_t encoded[BTP_STATE_BYTES];BtpState copy;btp_state_encode(&s,encoded);
        CHECK(btp_combat_valid(&s) && btp_effects_valid(&s));
        CHECK(btp_state_decode(encoded,sizeof encoded,&r->map,&r->training,&copy));
        btp_render(r,&copy,0,queued);
        for (unsigned y=0;y<200;++y) CHECK(!memcmp(living+y*320+104,queued+y*320+104,216*sizeof *living));
        s.effects.shots[0]=s.effects.shots[1];memset(&s.effects.shots[1],0,sizeof s.effects.shots[1]);s.effects.count=1;
        s.effects.stage=BTP_EFFECT_IMPACT;s.effects.age=(uint8_t)btp_effects_length(&s.effects.shots[0],&r->combat);
        btp_effects_tick(&s,r);
        CHECK(!btp_effects_pending_death(&s,1));
        CHECK(human ? !s.effects.count && !s.audio.sound_count : s.effects.stage==BTP_EFFECT_DEATH_SOUND && s.audio.sounds[0]==8);
        btp_render(r,&s,0,queued);unsigned changed=0;
        for (unsigned y=0;y<200;++y) changed+=(unsigned)(memcmp(living+y*320+104,queued+y*320+104,216*sizeof *living)!=0);
        CHECK(changed>0);
    }
    free(living);free(queued);r->map=original;
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
            /* A newly enabled original outtake consumes a game RNG draw.
               Graphics-on/off therefore need not have identical full state.
               This single-shell microstep still resolves the same attack. */
            CHECK(!memcmp(s.combat.unit,no_graphics.combat.unit,sizeof s.combat.unit));
        }
        if (s.combat.phase && !s.effects.pending && s.combat.unit[1].record[0]!=255) {
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
            step(&loaded,r,BTP_IDLE);if (loaded.combat.unit[1].record[0]!=255) CHECK(loaded.combat.unit[1].x==enemy_x && loaded.combat.unit[1].y==enemy_y);
        }
    }
    fclose(file);CHECK(s.mode==BTP_EXPLORE && s.story_flags[0]==3 && s.story_flags[1]==1 && s.allowance_cap==500);
    CHECK(menu.story_flags[0]==2 && combat_ticks>100 && effects>0);
    for (unsigned loan=0;loan<3;++loan) decline(&menu,r,loan);
    route_pixels(&menu,r);
    sequential_audio(&menu,r);death_pixels(&menu,r);
    btp_start(&s);uint8_t old[BTP_STATE_BYTES];BtpState migrated;
    btp_state_encode(&s,old);memcpy(old,"BTPC",4);old[4]=12;
    CHECK(btp_state_decode(old,512,&r->map,&r->training,&migrated));CHECK(!memcmp(&s,&migrated,sizeof s));
    free(r);printf("PASS: %u combat integration assertions; %u input continuations, three loans and flee results\n",checks,ticks);
    return 0;
}
