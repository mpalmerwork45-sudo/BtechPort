#include "core/school.h"
#include "core/economy.h"
#include "core/npc.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks;
#define CHECK(x) do { ++checks; if (!(x)) { fprintf(stderr,"FAIL %s:%d: %s\n",__FILE__,__LINE__,#x); exit(1); } } while (0)
static void same(const BtpState *a, const BtpState *b)
{
    uint8_t one[BTP_STATE_BYTES], two[BTP_STATE_BYTES];
    btp_state_encode(a,one); btp_state_encode(b,two); CHECK(!memcmp(one,two,sizeof one));
}
static void tick(BtpState *s, const BtpResources *r, BtpAction a)
{
    uint8_t bytes[BTP_STATE_BYTES]; BtpState restored;
    btp_state_encode(s,bytes);
    CHECK(btp_state_decode(bytes,sizeof bytes,&r->map,btp_building_bld(r,s->entry_slot ? s->entry_slot : 1),&restored));
    same(s,&restored); btp_game_tick(s,r,a); btp_game_tick(&restored,r,a); same(s,&restored);
}
static void synthetic(void)
{
    CHECK(btp_menu_count(9) == 4);
    for (unsigned rank = 0; rank <= 4; ++rank) CHECK(btp_school_price(rank) == 75u+125u*rank);
    BtpState s; btp_start(&s); CHECK(btp_school_valid(&s));
    s.skills[2] = 5; CHECK(!btp_school_valid(&s)); s.skills[2] = 0;
    s.checkpoint_skills[0] = 5; CHECK(!btp_school_valid(&s)); s.checkpoint_skills[0] = 0;
    s.school.phase = 3; CHECK(!btp_school_valid(&s)); s.school.phase = 0;
    s.school.course = 1; CHECK(!btp_school_valid(&s)); s.school.course = 0;
    BtpResources *r = calloc(1,sizeof *r); CHECK(r);
    s.script = (BtpScriptState){.status=BTP_SCRIPT_NATIVE,.native_action=4,.pc=2};
    btp_school_native(&s,r);
    CHECK(s.script.status == BTP_SCRIPT_ERROR && s.script.error == BTP_SCRIPT_NATIVE_CONTEXT &&
        s.credits == 35 && !s.skills[0]); free(r);
}
static void enter(BtpState *s, const BtpResources *r, unsigned course, unsigned rank, uint32_t cash)
{
    btp_start(s);
    for (unsigned i = 0; i < 5; ++i) tick(s,r,BTP_UP);
    tick(s,r,BTP_ACCEPT); s->credits = cash; s->skills[course] = (uint8_t)rank;
    s->npc.allowance_pending = (uint8_t)btp_economy_below_cap(s);
    tick(s,r,BTP_DOWN); tick(s,r,BTP_DOWN); tick(s,r,BTP_ACCEPT);
    CHECK(s->script.status == BTP_SCRIPT_WAIT && s->story_flags[7] == 1 && !s->story_flags[21]);
    tick(s,r,BTP_ACCEPT);
    CHECK(s->script.menu_id == 9 && s->school.phase == BTP_SCHOOL_PRICES && s->script.pc == 0xf0f);
    for (unsigned i = 0; i < course; ++i) tick(s,r,BTP_DOWN);
}
static void boundaries(const BtpResources *r)
{
    BtpState s;
    for (unsigned course = 0; course < 3; ++course) for (unsigned rank = 0; rank < 4; ++rank) {
        unsigned price = btp_school_price(rank);
        enter(&s,r,course,rank,price-1);
        tick(&s,r,BTP_ACCEPT);
        CHECK(s.school.phase == BTP_SCHOOL_TRANSCRIPT && s.school.outcome == BTP_SCHOOL_NO_FUNDS &&
            s.skills[course] == rank && s.credits == price-1 && !s.story_flags[9] && s.script.pc == 0x10da);
        tick(&s,r,BTP_ACCEPT);
        CHECK(s.script.menu_id == 8 && s.script.selected == 2 && !s.school.phase && !s.story_flags[21]);
        enter(&s,r,course,rank,price);
        uint8_t rng[3]; memcpy(rng,s.npc.rng,3);
        tick(&s,r,BTP_ACCEPT);
        CHECK(s.school.phase == BTP_SCHOOL_TRANSCRIPT && s.school.outcome == BTP_SCHOOL_TRAINED &&
            s.skills[course] == rank+1 && !s.credits && s.story_flags[9] == 1 && s.script.pc == 0xf75 &&
            s.checkpoint_skills[course] == rank && s.checkpoint_valid && !memcmp(rng,s.npc.rng,3));
        for (unsigned i = 0; i < 3; ++i) CHECK(s.skills[i] == (i == course ? rank+1 : 0));
        tick(&s,r,BTP_ACCEPT);
        CHECK(!s.school.phase && s.story_flags[21] == 255 && s.script.pc == 0x10da && s.script.text_count == 1);
        tick(&s,r,BTP_ACCEPT);
        CHECK(!s.checkpoint_valid && s.script.menu_id == 8 && s.script.selected == 2);
        tick(&s,r,BTP_ACCEPT);
        CHECK(s.script.status == BTP_SCRIPT_WAIT && s.script.pc == 0xf55 && s.story_flags[21] == 255);
        for (unsigned i = 0; i < 20; ++i) tick(&s,r,BTP_IDLE);
        CHECK(s.story_flags[21] == 255 && !s.credits && s.skills[course] == rank+1);
    }
    for (unsigned course = 0; course < 3; ++course) {
        enter(&s,r,course,4,UINT32_MAX); tick(&s,r,BTP_ACCEPT);
        CHECK(s.school.outcome == BTP_SCHOOL_MASTERED && s.credits == UINT32_MAX &&
            s.skills[course] == 4 && !s.story_flags[9] && !s.story_flags[21]);
        tick(&s,r,BTP_ACCEPT); CHECK(s.script.menu_id == 8 && s.script.selected == 2);
    }
    enter(&s,r,0,0,UINT32_C(65536)); tick(&s,r,BTP_ACCEPT);
    CHECK(s.credits == UINT32_C(65461) && s.skills[0] == 1); /* 8086 SUB/SBB borrow. */
    enter(&s,r,0,0,35); tick(&s,r,BTP_UP); CHECK(s.script.selected == 3);
    tick(&s,r,BTP_ACCEPT);
    CHECK(s.mode == BTP_EXPLORE && s.credits == 35 && !s.skills[0] && !s.school.phase && !s.checkpoint_valid);
    /* Unknown continuation after a debit must recover the entire uncommitted choice. */
    BtpResources *broken = malloc(sizeof *broken); CHECK(broken); *broken = *r;
    enter(&s,r,2,2,70000); broken->citadel.bytes[0xf6c] = 0xe0;
    tick(&s,broken,BTP_ACCEPT);
    CHECK(s.mode == BTP_SCRIPT_FAULT && s.credits == 70000 && s.skills[2] == 2 &&
        !s.school.phase && !s.checkpoint_valid && !s.story_flags[9]);
    tick(&s,r,BTP_CANCEL); CHECK(s.mode == BTP_BUILDING && s.script.menu_id == 8);
    free(broken);
    /* Atomic validation rejects invalid ranks, phase/context and receipt/cash inconsistencies. */
    enter(&s,r,1,1,200); tick(&s,r,BTP_ACCEPT);
    uint8_t saved[BTP_STATE_BYTES], bad[BTP_STATE_BYTES]; btp_state_encode(&s,saved);
    const unsigned offsets[] = {384,387,390,391,392,393,394,224,33};
    const uint8_t values[] = {5,5,3,3,4,1,1,1,0};
    for (unsigned i = 0; i < sizeof offsets/sizeof offsets[0]; ++i) {
        memcpy(bad,saved,sizeof bad); bad[offsets[i]] = values[i]; BtpState copy = s;
        CHECK(!btp_state_decode(bad,sizeof bad,&r->map,&r->citadel,&copy)); same(&s,&copy);
    }
    /* BTP7/BTS1 saves written in M2g migrate to zero ranks and no tuition phase. */
    btp_start(&s); btp_state_encode(&s,saved); memcpy(saved,"BTP7",4); saved[4] = 7;
    BtpState copy; CHECK(btp_state_decode(saved,384,&r->map,NULL,&copy)); same(&s,&copy);
    puts("School: all subjects/ranks, exact/insufficient/high-word tuition, mastery, Withdraw, context/rollback, atomic validation and BTP7 migration.");
}
static void cooldown(const BtpResources *r)
{
    BtpState s; enter(&s,r,0,0,75); tick(&s,r,BTP_ACCEPT); tick(&s,r,BTP_ACCEPT); tick(&s,r,BTP_ACCEPT);
    s.story_flags[20] = 1; s.story_flags[22] = 255;
    tick(&s,r,BTP_DOWN); tick(&s,r,BTP_DOWN); tick(&s,r,BTP_ACCEPT);
    CHECK(s.mode == BTP_EXPLORE && s.story_flags[21] == 255 && !s.npc.clock);
    for (unsigned i = 0; i < 3; ++i) tick(&s,r,BTP_IDLE);
    CHECK(s.story_flags[20] == 1 && s.story_flags[21] == 255 && s.story_flags[22] == 255);
    tick(&s,r,BTP_IDLE); CHECK(!s.story_flags[20] && s.story_flags[21] == 254 && s.story_flags[22] == 254);
    for (unsigned i = 0; i < 254*4; ++i) tick(&s,r,BTP_IDLE);
    CHECK(!s.story_flags[20] && !s.story_flags[21] && !s.story_flags[22]);
    for (unsigned i = 0; i < 8; ++i) tick(&s,r,BTP_IDLE);
    CHECK(!s.story_flags[21] && s.skills[0] == 1 && !s.story_flags[0]);
    tick(&s,r,BTP_DOWN); tick(&s,r,BTP_UP); tick(&s,r,BTP_ACCEPT);
    tick(&s,r,BTP_UP); tick(&s,r,BTP_UP); tick(&s,r,BTP_ACCEPT);
    CHECK(s.school.phase == BTP_SCHOOL_PRICES && s.skills[0] == 1 && btp_school_price(s.skills[0]) == 200);
    puts("School clock: fixed four-tick outdoor frames, indoor suspension, all three saturated countdowns, re-enrolment without invented mission progress.");
}
static void replay(const BtpResources *r, const char *name)
{
    char path[256]; snprintf(path,sizeof path,"tests/fixtures/reference-class-%s.actions",name);
    FILE *f = fopen(path,"r"); CHECK(f); BtpState s; btp_start(&s); btp_npc_init(&s,&r->map);
    char line[32]; unsigned ticks = 0;
    while (fgets(line,sizeof line,f)) {
        line[strcspn(line,"\r\n")] = 0; BtpAction a; CHECK(btp_action_parse(line,&a));
        tick(&s,r,a); CHECK(!s.npc.fault && s.mode != BTP_SCRIPT_FAULT);
        uint8_t text[BTP_BLD_MAX+1]; size_t n; CHECK(btp_game_text(&s,r,text,sizeof text,&n)); ++ticks;
    }
    CHECK(!ferror(f) && !fclose(f));
    if (!strcmp(name,"funded")) CHECK(s.credits == 27 && s.skills[0] == 1 && s.script.menu_id == 8 && !s.story_flags[21]);
    printf("School persistence: %u ticks restored/continued identically (%s).\n",ticks,name);
}
enum { FIELDS = 70 };
static int row(FILE *f, uint32_t v[FIELDS])
{
    char line[2048];
    do { if (!fgets(line,sizeof line,f)) return 0; } while (line[0] == '#');
    char *p = line;
    for (unsigned i = 0; i < FIELDS; ++i) {
        char *end; unsigned long n = strtoul(p,&end,10);
        CHECK(end != p && n <= UINT32_MAX && *end == (i+1 == FIELDS ? '\n' : ','));
        v[i] = (uint32_t)n; p = end+1;
    }
    return 1;
}
static void projection(const BtpState *s, const BtpMap *m, uint32_t v[FIELDS])
{
    v[0] = s->npc.phase; v[1] = s->npc.loop_timer; memcpy(v+2,(uint32_t[3]){s->npc.rng[0],s->npc.rng[1],s->npc.rng[2]},3*sizeof *v);
    v[5] = s->npc.search; v[6] = s->npc.bias; v[7] = 0xc00+s->x_half; v[8] = 0xc000+s->y_half;
    for (unsigned i = 0; i < 8; ++i) {
        unsigned a = 9+7*i, goal = s->npc_pairs[i][0]&7u;
        v[a] = s->npc.actor[i].x; v[a+1] = s->npc.actor[i].y;
        v[a+2] = m->entrance_x[goal]; v[a+3] = m->entrance_y[goal];
        v[a+4] = s->npc.actor[i].direction; v[a+5] = s->npc_pairs[i][0]; v[a+6] = s->npc_pairs[i][1];
    }
    v[65] = s->credits; for (unsigned i = 0; i < 3; ++i) v[66+i] = s->investments[i]; v[69] = s->allowance_cap;
}
static void frames(const BtpResources *r, const char *name)
{
    char path[256]; snprintf(path,sizeof path,"tests/fixtures/tuition-%s-frames.csv",name);
    FILE *f = fopen(path,"r"); CHECK(f);
    uint32_t old[FIELDS], next[FIELDS], actual[FIELDS]; CHECK(row(f,old));
    BtpState s = {.x_half=(uint16_t)(old[7]&127u),.y_half=(uint16_t)(old[8]&127u),.map_id=1,.gate=85,
        .credits=old[65],.allowance_cap=(uint16_t)old[69]};
    s.npc = (BtpNpcState){.enabled=2,.phase=(uint8_t)old[0],.loop_timer=(uint8_t)old[1],
        .rng={(uint8_t)old[2],(uint8_t)old[3],(uint8_t)old[4]},.search=(uint16_t)old[5],.bias=(uint8_t)old[6]};
    for (unsigned i = 0; i < 3; ++i) s.investments[i] = old[66+i];
    s.npc.allowance_pending = (uint8_t)btp_economy_below_cap(&s);
    for (unsigned i = 0; i < 8; ++i) {
        unsigned a = 9+7*i;
        s.npc.actor[i] = (BtpNpc){(uint16_t)old[a],(uint16_t)old[a+1],(uint8_t)old[a+4]};
        s.npc_pairs[i][0] = (uint8_t)old[a+5]; s.npc_pairs[i][1] = (uint8_t)old[a+6];
    }
    CHECK(btp_npc_valid(&s,&r->map)); unsigned count = 0, samples = 1;
    while (row(f,next)) {
        CHECK(old[7] == next[7] && old[8] == next[8]);
        unsigned delta = (old[1]-next[1])&255u;
        for (unsigned i = 0; i < delta; ++i) {
            uint8_t saved[BTP_STATE_BYTES]; BtpState copy; btp_state_encode(&s,saved);
            CHECK(btp_state_decode(saved,sizeof saved,&r->map,NULL,&copy));
            btp_npc_frame(&s,&r->map); btp_npc_frame(&copy,&r->map); same(&s,&copy); ++count;
        }
        projection(&s,&r->map,actual);
        for (unsigned i = 0; i < FIELDS; ++i) if (actual[i] != next[i]) {
            fprintf(stderr,"Tuition %s sample %u field %u: native %u / original %u\n",name,samples,i,actual[i],next[i]); exit(1);
        }
        CHECK(!s.npc.fault); memcpy(old,next,sizeof old); ++samples;
    }
    CHECK(!ferror(f) && !fclose(f));
    printf("Tuition %s oracle: %u complete outdoor frames/%u samples, all 70 NPC/RNG/economy fields.\n",name,count,samples);
}
int main(int argc, char **argv)
{
    synthetic();
    if (argc == 2) {
        BtpResources *r = malloc(sizeof *r); BtpError e;
        CHECK(r && btp_resources_load(argv[1],r,&e) && btp_dialogue_load("work/talk-data.bin",&r->dialogue,&e));
        boundaries(r); cooldown(r); replay(r,"audit"); replay(r,"funded");
        frames(r,"funding"); frames(r,"clock"); free(r);
    }
    printf("PASS: %u school checks\n",checks); return 0;
}
