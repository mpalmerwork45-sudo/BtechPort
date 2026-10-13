#include "core/game.h"
#include "core/bank.h"
#include "core/economy.h"
#include "core/npc.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks;
#define CHECK(x) do { ++checks; if (!(x)) { fprintf(stderr,"FAIL %s:%d: %s\n",__FILE__,__LINE__,#x); exit(1); } } while (0)

static void restored_tick(BtpState *s, const BtpResources *r, BtpAction a)
{
    uint8_t b[BTP_STATE_BYTES], again[BTP_STATE_BYTES]; BtpState copy;
    btp_state_encode(s,b);
    CHECK(btp_state_decode(b,sizeof b,&r->map,btp_building_bld(r,s->entry_slot ? s->entry_slot : 1),&copy));
    btp_state_encode(&copy,again); CHECK(!memcmp(b,again,sizeof b));
    btp_game_tick(s,r,a); btp_game_tick(&copy,r,a);
    btp_state_encode(s,b); btp_state_encode(&copy,again); CHECK(!memcmp(b,again,sizeof b));
}
static void synthetic(void)
{
    CHECK(btp_menu_count(7) == 3 && btp_menu_count(10) == 3 && btp_menu_count(11) == 3);
    BtpBld b = {.length=2,.bytes={0xf5,6}}; BtpScriptState v; uint8_t story[BTP_STORY_BYTES] = {0};
    btp_script_start(&v,&b,story); CHECK(v.status == BTP_SCRIPT_NATIVE && v.native_action == 6);
    b.bytes[1] = 31; btp_script_start(&v,&b,story); CHECK(v.status==BTP_SCRIPT_NATIVE && v.native_action==31);
    b.bytes[1] = 48; btp_script_start(&v,&b,story); CHECK(v.error == BTP_SCRIPT_OPCODE);
    b = (BtpBld){.length=4,.bytes={0xf0,0,15,0xff}};
    btp_script_start(&v,&b,story); CHECK(v.status == BTP_SCRIPT_END && v.row == 15);
    BtpAction a; CHECK(btp_action_parse("9",&a) && a == BTP_DIGIT_9);
    CHECK(btp_action_parse("clear",&a) && a == BTP_CLEAR_INPUT);
    CHECK(!btp_action_parse("10",&a));
    BtpState s; btp_start(&s); s.credits = 20; s.investments[0] = 30;
    uint8_t rng[3]; memcpy(rng,s.npc.rng,3);
    CHECK(!btp_economy_below_cap(&s)); btp_economy_wrap(&s);
    CHECK(s.credits == 20 && s.investments[0] == 30 && !memcmp(s.npc.rng,rng,3));
    s.credits = 19; CHECK(btp_economy_below_cap(&s));
    btp_economy_wrap(&s); CHECK(s.credits == 34 && s.investments[0] == 31);
    CHECK(!btp_economy_below_cap(&s));
    /* Explicit extreme primary-code cases, not natural cadet-state claims. */
    s.credits = UINT32_MAX; s.investments[0] = 1;
    CHECK(btp_economy_below_cap(&s));
    s.investments[0] = 0; CHECK(btp_economy_below_cap(&s)); /* Signed high-word comparison. */
    s.investments[2] = 8640; s.credits = UINT32_MAX-s.investments[2];
    memcpy(s.npc.rng,(uint8_t[]){217,227,131},3); btp_economy_wrap(&s);
    CHECK(s.investments[2] == 18000);
    s.investments[2] = 8641; s.credits = UINT32_MAX-s.investments[2];
    memcpy(s.npc.rng,(uint8_t[]){217,227,131},3); btp_economy_wrap(&s);
    CHECK(s.investments[2] == 4500);
}
static void enter(BtpState *s, const BtpResources *r)
{
    btp_start(s); s->npc = (BtpNpcState){0};
    s->x_half = 102; s->y_half = 21;
    restored_tick(s,r,BTP_UP); CHECK(s->mode == BTP_ENTRY && s->entry_slot == 2);
    restored_tick(s,r,BTP_ACCEPT); CHECK(s->script.menu_id == 10);
    restored_tick(s,r,BTP_ACCEPT); CHECK(s->script.status == BTP_SCRIPT_WAIT);
    restored_tick(s,r,BTP_ACCEPT); CHECK(s->script.menu_id == 11 && s->script.has_accounts);
}
static void buy(BtpState *s, const BtpResources *r)
{
    restored_tick(s,r,BTP_ACCEPT); /* change investments */
    restored_tick(s,r,BTP_ACCEPT); /* buy; menu 7 now also selects company 0 */
    CHECK(s->bank.phase == BTP_BANK_MENU);
    restored_tick(s,r,BTP_ACCEPT); CHECK(s->bank.phase == BTP_BANK_AMOUNT);
}
static void boundaries(const BtpResources *r)
{
    BtpState s; enter(&s,r); buy(&s,r);
    restored_tick(&s,r,BTP_DIGIT_0); restored_tick(&s,r,BTP_DIGIT_1);
    CHECK(!strcmp(s.bank.input,"1"));
    restored_tick(&s,r,BTP_DIGIT_2); restored_tick(&s,r,BTP_CANCEL);
    CHECK(!strcmp(s.bank.input,"1"));
    restored_tick(&s,r,BTP_CLEAR_INPUT); CHECK(!strcmp(s.bank.input,"0") && s.bank.phase == BTP_BANK_AMOUNT);
    for (unsigned i = 0; i < 8; ++i) restored_tick(&s,r,BTP_DIGIT_9);
    CHECK(!strcmp(s.bank.input,"9999999"));
    uint8_t saved[BTP_STATE_BYTES], bad[BTP_STATE_BYTES]; BtpState copy = s;
    btp_state_encode(&s,saved);
    const unsigned offsets[] = {344,345,346,347,348,352,356,357,363,364,365};
    const uint8_t invalid[] = {4,3,5,2,34,1,'x',0,'9',2,1};
    for (unsigned i = 0; i < sizeof offsets/sizeof offsets[0]; ++i) {
        memcpy(bad,saved,sizeof bad); bad[offsets[i]] = invalid[i];
        CHECK(!btp_state_decode(bad,sizeof bad,&r->map,&r->comstar,&copy));
        CHECK(!memcmp(&copy,&s,sizeof s));
    }
    restored_tick(&s,r,BTP_ACCEPT);
    CHECK(s.credits == 0 && s.investments[0] == 35 && s.bank.amount == 35 && s.bank.clamped &&
        s.script.status == BTP_SCRIPT_WAIT && s.bank.phase == BTP_BANK_MESSAGE);
    restored_tick(&s,r,BTP_ACCEPT); restored_tick(&s,r,BTP_ACCEPT); restored_tick(&s,r,BTP_ACCEPT);
    CHECK(s.bank.outcome == BTP_BANK_NO_CASH && s.script.status == BTP_SCRIPT_WAIT);
    restored_tick(&s,r,BTP_ACCEPT); restored_tick(&s,r,BTP_ACCEPT); restored_tick(&s,r,BTP_DOWN);
    restored_tick(&s,r,BTP_ACCEPT); CHECK(s.script.choices[7] == 1 && s.bank.phase == BTP_BANK_MENU);
    restored_tick(&s,r,BTP_ACCEPT); CHECK(s.bank.outcome == BTP_BANK_NOT_OWNED && s.investments[0] == 35);
    restored_tick(&s,r,BTP_ACCEPT); restored_tick(&s,r,BTP_ACCEPT); restored_tick(&s,r,BTP_ACCEPT);
    restored_tick(&s,r,BTP_UP); restored_tick(&s,r,BTP_ACCEPT);
    restored_tick(&s,r,BTP_CANCEL); CHECK(!s.bank.input[0]);
    restored_tick(&s,r,BTP_ACCEPT); CHECK(s.bank.outcome == BTP_BANK_ZERO && s.investments[0] == 35 && !s.credits);
    /* A decoded internal BTP6 state acquires empty accounts, retaining cash/equipment. */
    BtpState baseline; btp_start(&baseline); btp_state_encode(&baseline,saved); memcpy(saved,"BTP6",4); saved[4] = 6;
    CHECK(btp_state_decode(saved,320,&r->map,NULL,&copy) && copy.credits == 35 &&
        !copy.investments[0] && !copy.bank.phase && copy.allowance_cap == 50);
    /* Debit, then an unsupported continuation: all three balances/cash roll back. */
    BtpResources *broken = malloc(sizeof *broken); CHECK(broken != NULL); *broken = *r;
    enter(&s,r); buy(&s,r); restored_tick(&s,r,BTP_DIGIT_1);
    broken->comstar.bytes[0x382] = 0xe0;
    btp_game_tick(&s,broken,BTP_ACCEPT);
    CHECK(s.mode == BTP_SCRIPT_FAULT && s.credits == 35 && !s.investments[0] && !s.bank.phase);
    btp_state_encode(&s,saved); CHECK(btp_state_decode(saved,sizeof saved,&r->map,&broken->comstar,&copy));
    btp_game_tick(&s,broken,BTP_CANCEL); CHECK(s.mode == BTP_BUILDING && s.script.menu_id == 10);
    free(broken);
    /* All accounts, including a value above 65535, survive a restored transfer. */
    for (unsigned company = 0; company < 3; ++company) {
        enter(&s,r); s.credits = 70000;
        restored_tick(&s,r,BTP_ACCEPT); restored_tick(&s,r,BTP_ACCEPT);
        for (unsigned i = 0; i < company; ++i) restored_tick(&s,r,BTP_DOWN);
        restored_tick(&s,r,BTP_ACCEPT);
        CHECK(s.bank.phase == BTP_BANK_AMOUNT);
        restored_tick(&s,r,BTP_DIGIT_7); for (unsigned i = 0; i < 4; ++i) restored_tick(&s,r,BTP_DIGIT_0);
        restored_tick(&s,r,BTP_ACCEPT); CHECK(s.credits == 0 && s.investments[company] == 70000);
    }
}
static void replay(const BtpResources *r, const char *stem, unsigned checkpoint)
{
    char path[256]; snprintf(path,sizeof path,"tests/fixtures/%s.actions",stem);
    FILE *f = fopen(path,"r"); CHECK(f != NULL); BtpState s;
    if (checkpoint) btp_start_shop_conversation_checkpoint(&s,r,checkpoint);
    else { btp_start(&s); btp_npc_init(&s,&r->map); }
    char line[32]; unsigned ticks = 0;
    while (fgets(line,sizeof line,f)) {
        line[strcspn(line,"\r\n")] = 0; BtpAction a; CHECK(btp_action_parse(line,&a));
        restored_tick(&s,r,a); CHECK(!s.npc.fault && s.mode != BTP_SCRIPT_FAULT);
        uint8_t text[BTP_BLD_MAX+1]; size_t length; CHECK(btp_game_text(&s,r,text,sizeof text,&length));
        ++ticks;
    }
    CHECK(!ferror(f) && fclose(f) == 0);
    if (checkpoint) CHECK(s.mode == BTP_EXPLORE && !s.talk.phase && !s.talk_result && s.credits == 50);
    printf("M2f persistence: %u ticks restored/continued identically (%s).\n",ticks,stem);
}
enum { FIELDS = 70 };
static int row(FILE *f, uint32_t v[FIELDS])
{
    char line[2048];
    do { if (!fgets(line,sizeof line,f)) return 0; } while (line[0] == '#');
    char *at = line;
    for (unsigned i = 0; i < FIELDS; ++i) {
        char *end; unsigned long value = strtoul(at,&end,10);
        CHECK(end != at && value <= UINT32_MAX && (i+1 < FIELDS ? *end == ',' : *end == '\n'));
        v[i] = (uint32_t)value; at = end+1;
    }
    return 1;
}
static void projection(const BtpState *s, const BtpMap *m, uint32_t v[FIELDS])
{
    v[0] = s->npc.phase; v[1] = s->npc.loop_timer;
    for (unsigned i = 0; i < 3; ++i) v[2+i] = s->npc.rng[i];
    v[5] = s->npc.search; v[6] = s->npc.bias;
    v[7] = 0xc00+s->x_half; v[8] = 0xc000+s->y_half;
    for (unsigned i = 0; i < 8; ++i) {
        unsigned a = 9+7*i, goal = s->npc_pairs[i][0]&7u;
        v[a] = s->npc.actor[i].x; v[a+1] = s->npc.actor[i].y;
        v[a+2] = m->entrance_x[goal]; v[a+3] = m->entrance_y[goal];
        v[a+4] = s->npc.actor[i].direction; v[a+5] = s->npc_pairs[i][0]; v[a+6] = s->npc_pairs[i][1];
    }
    v[65] = s->credits; for (unsigned i = 0; i < 3; ++i) v[66+i] = s->investments[i];
    v[69] = s->allowance_cap;
}
static void frames(const BtpResources *r)
{
    FILE *f = fopen("tests/fixtures/bank-frames.csv","r"); CHECK(f != NULL);
    uint32_t old[FIELDS], next[FIELDS], actual[FIELDS]; CHECK(row(f,old));
    BtpState s = {.x_half=(uint16_t)(old[7]&127u),.y_half=(uint16_t)(old[8]&127u),.map_id=1,.gate=85,
        .credits=old[65],.allowance_cap=(uint16_t)old[69],.menu={.steps=1,.sound=1,.speed=2}};
    s.story_flags[51] = (uint8_t)s.allowance_cap;
    s.npc = (BtpNpcState){.enabled=2,.phase=(uint8_t)old[0],.loop_timer=(uint8_t)old[1],
        .rng={(uint8_t)old[2],(uint8_t)old[3],(uint8_t)old[4]},.search=(uint16_t)old[5],.bias=(uint8_t)old[6]};
    for (unsigned i = 0; i < 3; ++i) s.investments[i] = old[66+i];
    s.npc.allowance_pending = (uint8_t)btp_economy_below_cap(&s);
    for (unsigned i = 0; i < 8; ++i) {
        unsigned a = 9+7*i;
        s.npc.actor[i] = (BtpNpc){(uint16_t)old[a],(uint16_t)old[a+1],(uint8_t)old[a+4]};
        s.npc_pairs[i][0] = (uint8_t)old[a+5]; s.npc_pairs[i][1] = (uint8_t)old[a+6];
    }
    CHECK(btp_npc_valid(&s,&r->map)); unsigned count = 0, samples = 1, wraps = 0;
    while (row(f,next)) {
        CHECK(old[7] == next[7] && old[8] == next[8]); /* No skipped player movements. */
        unsigned delta = (old[1]-next[1])&255u;
        for (unsigned i = 0; i < delta; ++i) {
            uint8_t saved[BTP_STATE_BYTES], again[BTP_STATE_BYTES]; BtpState copy;
            btp_state_encode(&s,saved); CHECK(btp_state_decode(saved,sizeof saved,&r->map,NULL,&copy));
            if (!s.npc.loop_timer) ++wraps;
            btp_npc_frame(&s,&r->map); btp_npc_frame(&copy,&r->map); ++count;
            btp_state_encode(&s,saved); btp_state_encode(&copy,again); CHECK(!memcmp(saved,again,sizeof saved));
        }
        projection(&s,&r->map,actual);
        for (unsigned i = 0; i < FIELDS; ++i) if (actual[i] != next[i]) {
            fprintf(stderr,"Bank frame %u field %u: native %u / original %u\n",samples,i,actual[i],next[i]); exit(1);
        }
        CHECK(!s.npc.fault); memcpy(old,next,sizeof old); ++samples;
    }
    CHECK(!ferror(f) && fclose(f) == 0 && wraps == 2 && s.credits == 18 &&
        s.investments[0] == 31 && !s.investments[1] && s.investments[2] == 2);
    printf("Bank oracle: %u complete outdoor frames/%u samples, two wraps, all cash/accounts/NPC/RNG fields.\n",count,samples);
}
int main(int argc, char **argv)
{
    synthetic();
    if (argc == 2) {
        BtpResources *r = malloc(sizeof *r); BtpError e;
        CHECK(r && btp_resources_load(argv[1],r,&e) && btp_dialogue_load("work/talk-data.bin",&r->dialogue,&e));
        boundaries(r);
        replay(r,"reference-bank",0); replay(r,"reference-bank-rates",0);
        replay(r,"reference-armor-talk-empty",0); replay(r,"reference-weapon-talk-empty",0);
        replay(r,"reference-armor-talk",4); replay(r,"reference-weapon-talk",3);
        frames(r); free(r);
    }
    printf("PASS: %u bank/Talk checks\n",checks); return 0;
}
