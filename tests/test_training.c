#include "core/training.h"
#include "core/npc.h"
#include "data/save.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks;
#define CHECK(x) do { ++checks; if (!(x)) { fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x); exit(1); } } while (0)

static void restored_tick(BtpState *s, const BtpResources *r, BtpAction a)
{
    uint8_t bytes[BTP_STATE_BYTES], other[BTP_STATE_BYTES]; BtpState copy;
    btp_state_encode(s,bytes);
    if (!btp_state_decode(bytes,sizeof bytes,&r->map,btp_building_bld(r,s->entry_slot),&copy)) {
        fprintf(stderr,"Unsavable mode=%u phase=%u/%u pc=%04x status=%u cp=%u\n",
            s->mode,s->quiz.phase,s->mission.phase,s->script.pc,s->script.status,s->checkpoint_valid);
        CHECK(0);
    }
    btp_state_encode(&copy,other); CHECK(!memcmp(bytes,other,sizeof bytes));
    btp_game_tick(s,r,a); btp_game_tick(&copy,r,a);
    btp_state_encode(s,bytes); btp_state_encode(&copy,other); CHECK(!memcmp(bytes,other,sizeof bytes));
}
static void select(BtpState *s, const BtpResources *r, unsigned selected)
{
    for (unsigned n=0; s->script.selected != selected; ++n) {
        CHECK(n < 20); restored_tick(s,r,BTP_DOWN);
    }
    restored_tick(s,r,BTP_ACCEPT);
}
static void invalid(const BtpState *s, const BtpResources *r, unsigned at, uint8_t value)
{
    uint8_t bytes[BTP_STATE_BYTES]; BtpState untouched=*s;
    btp_state_encode(s,bytes); bytes[at]=value;
    CHECK(!btp_state_decode(bytes,sizeof bytes,&r->map,btp_building_bld(r,s->entry_slot),&untouched));
    CHECK(!memcmp(s,&untouched,sizeof untouched));
}
static void enter(BtpState *s, const BtpResources *r, unsigned slot)
{
    s->x_half = (uint16_t)((r->map.entrance_x[slot]&127)-1);
    s->y_half = r->map.entrance_y[slot]&127;
    restored_tick(s,r,BTP_RIGHT); CHECK(s->mode == BTP_ENTRY && s->entry_slot == slot);
    restored_tick(s,r,BTP_ACCEPT);
}
static void answers(BtpState *s, const BtpResources *r, int wrong)
{
    restored_tick(s,r,BTP_ACCEPT);
    for (unsigned round=0;round<3;++round) {
        CHECK(s->mode == BTP_QUIZ && s->quiz.round == round);
        unsigned answer = btp_quiz_answer[s->quiz.point];
        if (wrong && round == 0) answer = (answer+1u)%20u;
        for (unsigned n=0;s->quiz.selected != answer;++n) {
            CHECK(n < 20); restored_tick(s,r,BTP_DOWN);
        }
        restored_tick(s,r,BTP_ACCEPT);
    }
}
static void animation(BtpState *s, const BtpResources *r)
{
    if (s->cutscene.active) {
        invalid(s,r,441,3); invalid(s,r,442,s->cutscene.kind == 8 ? 0 : 8);
        invalid(s,r,443,s->cutscene.kind == 8 ? 3 : 18); invalid(s,r,450,1);
    }
    for (unsigned n=0;s->cutscene.active;++n) {
        CHECK(n < 128); restored_tick(s,r,n&1u ? BTP_IDLE : BTP_ACCEPT);
    }
}
static void begin(BtpState *s, const BtpResources *r, unsigned mech)
{
    btp_start(s); btp_npc_init(s,&r->map); enter(s,r,0);
    CHECK(s->quiz.phase == BTP_QUIZ_INTRO); answers(s,r,0);
    CHECK(s->script.status == BTP_SCRIPT_CONFIRM && s->script.pc == 0x1c8);
    restored_tick(s,r,BTP_ACCEPT); CHECK(s->script.status == BTP_SCRIPT_WAIT);
    restored_tick(s,r,BTP_ACCEPT); CHECK(s->script.menu_id == 7);
    select(s,r,mech); animation(s,r);
    CHECK(s->mode == BTP_MISSION && s->mission.phase == BTP_MISSION_DRIVE);
    CHECK(s->x_half == 64 && s->y_half == 79 && s->story_flags[2] == mech);
    /* v10/v11 first-mission saves predate timed cutscenes. Their established
       state migrates exactly once playback has completed. */
    uint8_t old[BTP_STATE_BYTES], current[BTP_STATE_BYTES]; BtpState loaded;
    for (unsigned version=10;version<=11;++version) {
        btp_state_encode(s,old); old[3]=(uint8_t)(version == 10 ? 'A' : 'B'); old[4]=(uint8_t)version;
        CHECK(btp_state_decode(old,version == 10 ? 448u : sizeof old,&r->map,&r->training,&loaded));
        btp_state_encode(&loaded,current); btp_state_encode(s,old); CHECK(!memcmp(old,current,sizeof old));
    }
}
static void synthetic(void)
{
    BtpResources *r = calloc(1,sizeof *r); CHECK(r);
    r->map.width = r->map.height = 64; memset(r->map.tiles,64,sizeof r->map.tiles);
    BtpState s; btp_start(&s); s.x_half = 64; s.y_half = 80;
    for (unsigned tile=0;tile<48;++tile) for (unsigned parity=0;parity<2;++parity) {
        s.y_half = (uint16_t)(80+parity); r->map.tiles[39*64+32]=(uint8_t)tile;
        unsigned flag = tile & (parity ? 4u : 1u) ?
            ((tile & 15u) == 15 && (tile & 48u) != 16 ? 16u : 8u) : 0u;
        CHECK(btp_mission_terrain(&s,&r->map) == flag);
    }
    memset(r->map.tiles,64,sizeof r->map.tiles);
    s.x_half=64; s.y_half=80; s.mode=BTP_MISSION;
    s.mission=(BtpMissionState){.phase=BTP_MISSION_DRIVE,.walk=6,.direction=2};
    btp_mission_tick(&s,r,BTP_UP_RIGHT);
    CHECK(s.x_half == 65 && s.y_half == 79 && s.mission.walk == 4 && s.mission.elapsed == 1);
    btp_mission_tick(&s,r,BTP_UP_RIGHT);
    CHECK(s.x_half == 66 && s.y_half == 78 && s.mission.walk == 5 && s.mission.elapsed == 2);
    r->map.tiles[37*64+34]=85; /* Block second foot column at proposed (67,77). */
    btp_mission_tick(&s,r,BTP_UP_RIGHT);
    CHECK(s.x_half == 66 && s.y_half == 78 && s.blocked == BTP_WALL && s.mission.walk == 6 && s.mission.elapsed == 3);
    memset(r->map.tiles,64,sizeof r->map.tiles);
    for (unsigned mech=0;mech<3;++mech) for (unsigned above=0;above<2;++above) {
        btp_start(&s); s.story_flags[2]=(uint8_t)mech; s.x_half=60; s.y_half=79;
        s.mode=BTP_MISSION; s.mission=(BtpMissionState){.phase=BTP_MISSION_DRIVE,.corner=1,
            .elapsed=(uint16_t)((mech ? 214 : 264)+above)};
        CHECK(btp_mission_tick(&s,r,BTP_IDLE)); CHECK(s.story_flags[1] == !above);
    }
    /* The original uses a wrapping 16-bit subtraction and a signed comparison. */
    s.mode=BTP_MISSION; s.mission.phase=BTP_MISSION_DRIVE; s.mission.elapsed=0;
    CHECK(btp_mission_tick(&s,r,BTP_IDLE) && s.story_flags[1]);
    s.mode=BTP_MISSION; s.mission=(BtpMissionState){.phase=BTP_MISSION_DRIVE};
    CHECK(!btp_mission_tick(&s,r,BTP_RIGHT) && s.mission.phase == BTP_MISSION_WARNING);
    CHECK(s.x_half == 60 && !s.mission.elapsed);
    btp_mission_tick(&s,r,BTP_ACCEPT); btp_mission_tick(&s,r,BTP_RIGHT);
    CHECK(s.x_half == 61 && s.mission.elapsed == 1 && s.mission.warned);
    s.x_half=64; s.y_half=79; s.mission.idle=10;
    unsigned elapsed=s.mission.elapsed;
    for (unsigned n=0;n<10;++n) CHECK(!btp_mission_tick(&s,r,BTP_IDLE));
    CHECK(s.mission.elapsed == elapsed); btp_mission_tick(&s,r,BTP_IDLE);
    CHECK(s.mission.elapsed == elapsed+1);
    r->map.tiles[38*64+33]=85; btp_mission_tick(&s,r,BTP_RIGHT);
    CHECK(s.x_half == 64 && s.y_half == 79 && s.blocked == BTP_WALL);
    r->map.tiles[38*64+33]=84; btp_mission_tick(&s,r,BTP_RIGHT);
    CHECK(s.x_half == 65 && s.blocked == BTP_CLEAR);
    /* Sparse script flags and animation operands stay bounded. */
    BtpBld b={.length=6,.bytes={0xea,8,1,0xf4,47,1}}; BtpScriptState v;
    btp_script_start(&v,&b,s.story_flags);
    CHECK(v.animation_kind == 8 && v.animation_flags == 1 && v.status == BTP_SCRIPT_ANIMATION);
    btp_script_animation_return(&v,&b,s.story_flags); CHECK(s.story_flags[47] == 1);
    b.bytes[1]=9; btp_script_start(&v,&b,s.story_flags); CHECK(v.error == BTP_SCRIPT_SCENE);
    b=(BtpBld){.length=4,.bytes={0xf4,48,1,0xff}};
    btp_script_start(&v,&b,s.story_flags); CHECK(v.error == BTP_SCRIPT_STATE_INDEX);
    free(r);
}
static void quiz(const BtpResources *r)
{
    BtpState s; btp_start(&s); btp_npc_init(&s,&r->map);
    memcpy(s.npc.rng,(uint8_t[]){128,238,198},3); enter(&s,r,0);
    restored_tick(&s,r,BTP_ACCEPT); CHECK(s.quiz.point == 7);
    CHECK(!memcmp(s.npc.rng,(uint8_t[]){64,221,140},3));
    invalid(&s,r,418,4); invalid(&s,r,419,20); invalid(&s,r,420,3);
    invalid(&s,r,421,10); invalid(&s,r,422,2); invalid(&s,r,423,0);
    invalid(&s,r,20,BTP_BUILDING); invalid(&s,r,425,1); invalid(&s,r,434,1);
    const unsigned points[3]={7,5,2};
    for (unsigned n=0;n<3;++n) {
        CHECK(s.quiz.point == points[n]);
        while (s.quiz.selected != btp_quiz_answer[s.quiz.point]) restored_tick(&s,r,BTP_DOWN);
        restored_tick(&s,r,BTP_ACCEPT);
    }
    CHECK(s.script.status == BTP_SCRIPT_CONFIRM && s.story_flags[20] == 0);
    CHECK(!memcmp(s.npc.rng,(uint8_t[]){16,118,48},3));
    restored_tick(&s,r,BTP_RIGHT); restored_tick(&s,r,BTP_ACCEPT);
    CHECK(s.script.status == BTP_SCRIPT_WAIT); restored_tick(&s,r,BTP_ACCEPT);
    CHECK(s.talk.phase == BTP_TALK_EMPTY); restored_tick(&s,r,BTP_ACCEPT);
    CHECK(s.mode == BTP_EXPLORE && s.x_half == 46 && s.y_half == 114 && !s.story_flags[0]);
    btp_start(&s); btp_npc_init(&s,&r->map); enter(&s,r,0); answers(&s,r,1);
    CHECK(s.quiz.phase == BTP_QUIZ_FAILED && s.story_flags[20] == 255 && !s.story_flags[0]);
    restored_tick(&s,r,BTP_ACCEPT); CHECK(s.mode == BTP_EXPLORE);
    enter(&s,r,0); CHECK(s.mode == BTP_BUILDING && s.script.status == BTP_SCRIPT_WAIT);
    restored_tick(&s,r,BTP_ACCEPT); CHECK(s.talk.phase == BTP_TALK_EMPTY);
    restored_tick(&s,r,BTP_ACCEPT); CHECK(s.mode == BTP_EXPLORE);
}
static void barracks(const BtpResources *r)
{
    BtpState s; btp_start(&s); btp_npc_init(&s,&r->map); enter(&s,r,6);
    CHECK(s.script.menu_id == 19); select(&s,r,1);
    CHECK(s.script.status == BTP_SCRIPT_WAIT && !s.story_flags[19]); restored_tick(&s,r,BTP_ACCEPT);
    CHECK(s.mode == BTP_EXPLORE);
    s.story_flags[0]=1; s.story_flags[1]=0; enter(&s,r,6); select(&s,r,1);
    CHECK(s.script.status == BTP_SCRIPT_WAIT && !s.story_flags[19]); restored_tick(&s,r,BTP_ACCEPT);
    s.story_flags[1]=1; s.story_flags[20]=255; enter(&s,r,6); select(&s,r,1);
    CHECK(s.story_flags[19] == 1);
    unsigned screens=0;
    while (s.script.status == BTP_SCRIPT_WAIT && screens++ < 12) {
        restored_tick(&s,r,BTP_ACCEPT); animation(&s,r);
    }
    CHECK(screens == 7 && s.mode == BTP_BUILDING && s.script.menu_id == 19 && !s.story_flags[20]);
    CHECK(s.script.animation_kind == 8 && s.script.animation_flags == 1);
    select(&s,r,1); CHECK(s.script.status == BTP_SCRIPT_WAIT && s.story_flags[19] == 1);
    restored_tick(&s,r,BTP_ACCEPT); CHECK(s.script.menu_id == 19);
    select(&s,r,0); animation(&s,r); CHECK(s.mode == BTP_EXPLORE);
}
static void mission(const BtpResources *r)
{
    BtpState s; begin(&s,r,0);
    invalid(&s,r,123,0); invalid(&s,r,426,BTP_MISSION_WARNING);
    invalid(&s,r,427,2); invalid(&s,r,429,11); invalid(&s,r,430,16); invalid(&s,r,431,8);
    invalid(&s,r,26,3); invalid(&s,r,411,49); invalid(&s,r,146,1);
    BtpNpcState npc=s.npc; uint8_t pairs[16]; memcpy(pairs,s.npc_pairs,16);
    /* First reach the corner, then return; this slow L-shaped route is an
       observed failure, rather than an invented alternate mission. */
    for (unsigned n=0;n<56;++n) restored_tick(&s,r,BTP_RIGHT);
    for (unsigned n=0;n<45;++n) restored_tick(&s,r,BTP_DOWN);
    CHECK(s.x_half == 120 && s.y_half == 124 && s.mission.phase == BTP_MISSION_CORNER);
    restored_tick(&s,r,BTP_ACCEPT);
    /* Original capture waits at the corner. Four bounded timer updates put
       this otherwise borderline (262-update) route over the Locust limit. */
    for (unsigned n=0;n<44;++n) restored_tick(&s,r,BTP_IDLE);
    for (unsigned n=0;n<45;++n) restored_tick(&s,r,BTP_UP);
    for (unsigned n=0;n<60;++n) restored_tick(&s,r,BTP_LEFT);
    CHECK(!memcmp(&s.npc,&npc,sizeof npc) && !memcmp(s.npc_pairs,pairs,16));
    CHECK(s.credits == 35); restored_tick(&s,r,BTP_IDLE);
    CHECK(s.mode == BTP_BUILDING && s.mission.phase == BTP_MISSION_RESULT);
    CHECK(!s.story_flags[0] && !s.story_flags[1] && s.story_flags[3] == 1 && s.story_flags[20] == 255);
    restored_tick(&s,r,BTP_ACCEPT);
    CHECK(s.mode == BTP_EXPLORE && !s.mission.phase && s.x_half == 47 && s.y_half == 118 && s.allowance_cap == 50);
    /* Success thresholds were independently read from the original routine.
       The live optimized route is covered by the differential replay. */
    for (unsigned mech=0;mech<3;++mech) {
        begin(&s,r,mech); s.x_half=60; s.y_half=79; s.mission.corner=1;
        s.mission.elapsed=(uint16_t)(mech ? 214 : 264);
        restored_tick(&s,r,BTP_IDLE);
        CHECK(s.story_flags[0] == 1 && s.story_flags[1] == 1 && !s.story_flags[3]);
        CHECK(s.allowance_cap == 150 && s.script.mech_result == mech+1 && s.story_flags[20] == 255);
        invalid(&s,r,406,50); invalid(&s,r,415,4); invalid(&s,r,416,0);
        uint8_t text[BTP_BLD_MAX+1]; size_t length; CHECK(btp_game_text(&s,r,text,sizeof text,&length) && length);
        restored_tick(&s,r,BTP_ACCEPT); CHECK(s.mode == BTP_EXPLORE && s.allowance_cap == 150);
        s.story_flags[20]=0; enter(&s,r,0); answers(&s,r,0);
        restored_tick(&s,r,BTP_ACCEPT); restored_tick(&s,r,BTP_ACCEPT); select(&s,r,0); animation(&s,r);
        CHECK(s.mode == BTP_MISSION && s.story_flags[0] == 1 && s.allowance_cap == 150 && s.mission.assignment == 1);
        CHECK(s.x_half == 64 && s.y_half == 79 && s.mission.phase == BTP_MISSION_SNICKER);
    }
}
static void lounge(const BtpResources *r)
{
    BtpState s; btp_start(&s); s.npc=(BtpNpcState){0}; enter(&s,r,7);
    CHECK(s.script.menu_id == 24); select(&s,r,0); animation(&s,r); CHECK(s.talk.phase == BTP_TALK_EMPTY);
    restored_tick(&s,r,BTP_ACCEPT); CHECK(s.script.menu_id == 24);
    select(&s,r,1); CHECK(s.mode == BTP_EXPLORE && s.x_half == 17 && s.y_half == 89);
    enter(&s,r,7); s.npc_pairs[0][0]=113; s.npc_pairs[0][1]=5;
    s.npc_pairs[2][0]=114; s.npc_pairs[2][1]=7; s.recruitment=s.story_flags[45]=1;
    s.talk_result=s.story_flags[46]=91;
    select(&s,r,0); animation(&s,r); CHECK(s.talk.count == 2);
    restored_tick(&s,r,BTP_ACCEPT); CHECK(s.script.status == BTP_SCRIPT_WAIT && !s.recruitment && !s.talk_result);
    CHECK(!s.npc_pairs[0][1] && s.npc_pairs[2][1] == 7 && !s.story_flags[47]);
    for (unsigned n=0;n<4;++n) restored_tick(&s,r,BTP_ACCEPT);
    CHECK(s.story_flags[47] == 1 && s.script.status == BTP_SCRIPT_WAIT);
    restored_tick(&s,r,BTP_ACCEPT); CHECK(s.mode == BTP_EXPLORE && s.story_flags[47] == 1);
    enter(&s,r,7); select(&s,r,0); animation(&s,r); CHECK(s.talk.count == 1);
    restored_tick(&s,r,BTP_ACCEPT); CHECK(s.talk.phase == BTP_TALK_REPLY);
    restored_tick(&s,r,BTP_ACCEPT); restored_tick(&s,r,BTP_DOWN); restored_tick(&s,r,BTP_ACCEPT);
    CHECK(s.script.menu_id == 24 && s.story_flags[47] == 1);
}
static void rubble(const BtpResources *r)
{
    for (unsigned mech=0;mech<3;++mech) for (unsigned rubble=0;rubble<8;++rubble) {
        BtpState s; btp_start(&s); btp_npc_init(&s,&r->map);
        s.story_flags[0]=1; s.story_flags[1]=1; s.allowance_cap=150; s.story_flags[51]=150;
        enter(&s,r,0); answers(&s,r,0);
        restored_tick(&s,r,BTP_ACCEPT); CHECK(s.script.text[0].offset == 0x40f);
        restored_tick(&s,r,BTP_ACCEPT); select(&s,r,mech); animation(&s,r);
        CHECK(s.mode == BTP_MISSION && s.mission.assignment == 1);
        if (!mech) {
            CHECK(s.mission.phase == BTP_MISSION_SNICKER);
            restored_tick(&s,r,BTP_ACCEPT);
        }
        s.mission.rubble=(uint8_t)rubble;
        s.mission.rubble_under=btp_map_tile(&r->map,btp_rubble_x[rubble],btp_rubble_y[rubble]);
        s.x_half=(uint16_t)(2u*btp_rubble_x[rubble]-2u);
        s.y_half=(uint16_t)(2u*btp_rubble_y[rubble]+2u); s.mission.idle=0;
        CHECK(btp_mission_tile(&s,&r->map,btp_rubble_x[rubble],btp_rubble_y[rubble]) == 80);
        restored_tick(&s,r,BTP_IDLE);
        CHECK(s.mission.corner && s.mission.phase == BTP_MISSION_PICKUP && !s.mission.elapsed);
        CHECK(btp_mission_tile(&s,&r->map,btp_rubble_x[rubble],btp_rubble_y[rubble]) ==
            (mech ? s.mission.rubble_under : 80));
        invalid(&s,r,434,2); invalid(&s,r,435,8); invalid(&s,r,432,1);
        restored_tick(&s,r,BTP_ACCEPT);
        /* Arbitrarily long waits cannot fail the original second assignment. */
        for (unsigned n=0;n<32;++n) restored_tick(&s,r,BTP_IDLE);
        CHECK(!s.mission.elapsed); s.x_half=60; s.y_half=79;
        restored_tick(&s,r,BTP_IDLE);
        CHECK(s.mode == BTP_BUILDING && s.mission.phase == BTP_MISSION_RESULT);
        CHECK(s.mech_skills[1] == 1 && s.story_flags[1] == (mech != 0));
        CHECK(s.story_flags[0] == (mech ? 2 : 1) && s.allowance_cap == (mech ? 250 : 150));
        restored_tick(&s,r,BTP_ACCEPT); CHECK(s.mode == BTP_EXPLORE && !s.mission.phase);
        if (mech && !rubble) {
            s.story_flags[20]=0; enter(&s,r,0); answers(&s,r,0);
            restored_tick(&s,r,BTP_ACCEPT);
            CHECK(s.script.status == BTP_SCRIPT_WAIT && s.script.text[0].offset == 0x4f8);
            restored_tick(&s,r,BTP_ACCEPT); CHECK(s.mode == BTP_EXPLORE);
            s.story_flags[19]=1; s.story_flags[20]=0; enter(&s,r,0); answers(&s,r,0);
            restored_tick(&s,r,BTP_ACCEPT);
            CHECK(s.script.text[0].offset == 0x5b7); restored_tick(&s,r,BTP_ACCEPT);
            select(&s,r,mech); animation(&s,r);
            CHECK(s.mode == BTP_SCRIPT_FAULT && !s.mission.phase && s.story_flags[0] == 2 && s.allowance_cap == 250);
        }
    }
}
static void diagonal_return(const BtpResources *r)
{
    static const BtpAction diagonal[4] = {BTP_UP_LEFT,BTP_UP_RIGHT,BTP_DOWN_LEFT,BTP_DOWN_RIGHT};
    for (unsigned i=0;i<4;++i) {
        BtpState s; begin(&s,r,0);
        s.entry_action=(uint8_t)diagonal[i];
        restored_tick(&s,r,diagonal[i]);
        CHECK(s.x_half == 64+btp_action_dx(diagonal[i]) && s.y_half == 79+btp_action_dy(diagonal[i]));
        s.x_half=60; s.y_half=79; s.mission.corner=1; s.mission.elapsed=264;
        restored_tick(&s,r,BTP_IDLE); CHECK(s.story_flags[1]);
        restored_tick(&s,r,BTP_ACCEPT);
        CHECK(s.mode == BTP_EXPLORE && s.x_half == 46+btp_action_dx(diagonal[i]) &&
              s.y_half == 118+btp_action_dy(diagonal[i]) && s.facing == diagonal[i]);
        restored_tick(&s,r,BTP_IDLE);
    }
}
int main(int argc, char **argv)
{
    synthetic();
    if (argc > 1) {
        BtpResources *r=malloc(sizeof *r); BtpError e; CHECK(r);
        CHECK(btp_resources_load(argv[1],r,&e)); CHECK(btp_dialogue_load("work/talk-data.bin",&r->dialogue,&e));
        quiz(r); barracks(r); mission(r); rubble(r); lounge(r); diagonal_return(r); free(r);
    }
    printf("PASS: %u training timer, quiz, mission, barracks, lounge and continuation assertions.\n",checks);
    return 0;
}
