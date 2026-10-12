#include "core/game.h"
#include "core/npc.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks;
#define CHECK(x) do { ++checks; if (!(x)) { fprintf(stderr,"FAIL %s:%d: %s\n",__FILE__,__LINE__,#x); exit(1); } } while (0)

static void vm_bounds(void)
{
    BtpBld b = {.length=1,.bytes={0xf6}}; BtpScriptState s; uint8_t story[BTP_STORY_BYTES] = {0};
    btp_script_start(&s,&b,story); CHECK(s.error == BTP_SCRIPT_TRUNCATED);
    b.length = 3; b.bytes[1] = 3;
    btp_script_start(&s,&b,story); CHECK(s.error == BTP_SCRIPT_TARGET);
    b = (BtpBld){.length=5,.bytes={0xf6,4,0,0xfb,0xff}};
    btp_script_start(&s,&b,story); CHECK(s.status == BTP_SCRIPT_CONFIRM && s.pc == 3);
    btp_script_confirm(&s,&b,0,story); CHECK(s.status == BTP_SCRIPT_WAIT && s.pc == 4);
    btp_script_start(&s,&b,story); btp_script_confirm(&s,&b,1,story); CHECK(s.status == BTP_SCRIPT_END);
    b = (BtpBld){.length=2,.bytes={0xf0,0}};
    btp_script_start(&s,&b,story); CHECK(s.error == BTP_SCRIPT_TRUNCATED);
    b = (BtpBld){.length=4,.bytes={0xf0,0,22,0xff}};
    btp_script_start(&s,&b,story); CHECK(s.status == BTP_SCRIPT_END && s.row == 22);
    b.bytes[1] = 1; btp_script_start(&s,&b,story); CHECK(s.error == BTP_SCRIPT_SCENE);
    const unsigned ids[] = {12,13,14,15,16,30}, counts[] = {4,6,5,4,7,3};
    for (unsigned i = 0; i < 6; ++i) {
        b = (BtpBld){.length=(uint16_t)(3+2*counts[i]),.bytes={0xf9}}; b.bytes[1] = (uint8_t)ids[i];
        for (unsigned n = 0; n < counts[i]; ++n) b.bytes[2+2*n] = (uint8_t)(b.length-1);
        b.bytes[b.length-1] = 0xff;
        btp_script_start(&s,&b,story); CHECK(s.status == BTP_SCRIPT_MENU && btp_menu_count(ids[i]) == counts[i]);
        CHECK(!btp_script_choose(&s,&b,counts[i],story));
        CHECK(btp_script_choose(&s,&b,counts[i]-1,story) && s.status == BTP_SCRIPT_END);
        b.bytes[2] = (uint8_t)b.length;
        btp_script_start(&s,&b,story); CHECK(s.error == BTP_SCRIPT_TARGET);
    }
    b = (BtpBld){.length=8,.bytes={0xfc,'x',0,0xf5,10,0xfc,'y',0}};
    btp_script_start(&s,&b,story); CHECK(s.status == BTP_SCRIPT_NATIVE && s.text_count == 1 && s.native_action == 10);
    s.has_cash = 1; s.cash_after = 1; s.cash_value = UINT32_MAX;
    uint8_t output[16]; CHECK(btp_script_text(&s,&b,output,sizeof output) && !strcmp((char *)output,"x4294967295"));
    CHECK(!btp_script_text(&s,&b,output,11));
    s.cash_after = 2; CHECK(!btp_script_text(&s,&b,output,sizeof output));
    b = (BtpBld){.length=4,.bytes={0xf4,100,1,0xff}};
    btp_script_start(&s,&b,story); CHECK(s.error == BTP_SCRIPT_STATE_INDEX);
    b.bytes[1] = 39; btp_script_start(&s,&b,story); CHECK(s.status == BTP_SCRIPT_END && story[39] == 1);
    BtpResources *r = calloc(1,sizeof *r); CHECK(r != NULL);
    r->armor = (BtpBld){.length=8,.bytes={0xfd,0xfc,'x',0,0xf5,10,0xf8,0}};
    r->armor.length = 9;
    BtpState game; btp_start(&game); game.npc = (BtpNpcState){0};
    game.mode = BTP_BUILDING; game.entry_slot = 4;
    btp_script_start(&game.script,&r->armor,game.story_flags);
    btp_game_tick(&game,r,BTP_IDLE);
    CHECK(game.mode == BTP_SCRIPT_FAULT && game.script.error == BTP_SCRIPT_BUDGET && game.credits == 35);
    free(r);
}

static void restored_tick(BtpState *s, const BtpResources *r, BtpAction a)
{
    uint8_t b[BTP_STATE_BYTES], again[BTP_STATE_BYTES]; BtpState copy;
    btp_state_encode(s,b);
    CHECK(btp_state_decode(b,sizeof b,&r->map,btp_building_bld(r,s->entry_slot ? s->entry_slot : 1),&copy));
    btp_state_encode(&copy,again); CHECK(!memcmp(b,again,sizeof b));
    btp_game_tick(s,r,a); btp_game_tick(&copy,r,a);
    btp_state_encode(s,b); btp_state_encode(&copy,again); CHECK(!memcmp(b,again,sizeof b));
}
static void enter(BtpState *s, const BtpResources *r, unsigned slot, uint32_t cash)
{
    /* Explicit unit-test precondition; ordinary walks are verified separately. */
    btp_start(s); btp_npc_init(s,&r->map);
    s->x_half = r->map.entrance_x[slot]&127; s->y_half = (uint16_t)((r->map.entrance_y[slot]&127)+1);
    s->credits = cash; s->npc.allowance_pending = (uint8_t)(cash < s->allowance_cap);
    restored_tick(s,r,BTP_UP); CHECK(s->mode == BTP_ENTRY && s->entry_slot == slot);
    restored_tick(s,r,BTP_ACCEPT); CHECK(s->mode == BTP_BUILDING && s->script.status == BTP_SCRIPT_MENU);
    restored_tick(s,r,BTP_ACCEPT); /* Browse */
    restored_tick(s,r,BTP_DOWN);
    restored_tick(s,r,BTP_ACCEPT);
    if (slot == 3) { restored_tick(s,r,BTP_DOWN); restored_tick(s,r,BTP_ACCEPT); }
    CHECK(s->script.status == BTP_SCRIPT_CONFIRM);
}
static void boundaries(const BtpResources *r)
{
    BtpState s;
    enter(&s,r,4,49); BtpNpcState before = s.npc;
    restored_tick(&s,r,BTP_ACCEPT);
    CHECK(!s.story_flags[11] && s.credits == 49 && !s.armor && !memcmp(&s.npc,&before,sizeof before));
    CHECK(s.script.status == BTP_SCRIPT_WAIT); restored_tick(&s,r,BTP_ACCEPT);
    CHECK(s.mode == BTP_EXPLORE && s.y_half == 124);
    enter(&s,r,4,50); restored_tick(&s,r,BTP_ACCEPT);
    CHECK(s.credits == 0 && s.story_flags[11] == 1 && s.armor == 1 && s.armor_points == 25 && s.npc.allowance_pending);
    uint8_t saved[BTP_STATE_BYTES], corrupt[BTP_STATE_BYTES]; BtpState untouched = s, copy = s;
    btp_state_encode(&s,saved);
    const unsigned offsets[] = {228,230,232,235,237,242,277,278,301};
    const uint8_t invalid[] = {49,12,26,2,9,1,2,1,1};
    for (unsigned i = 0; i < sizeof offsets/sizeof offsets[0]; ++i) {
        memcpy(corrupt,saved,sizeof corrupt); corrupt[offsets[i]] = invalid[i];
        CHECK(!btp_state_decode(corrupt,sizeof corrupt,&r->map,&r->armor,&copy));
        CHECK(!memcmp(&copy,&untouched,sizeof copy));
    }
    enter(&s,r,3,1); restored_tick(&s,r,BTP_ACCEPT);
    CHECK(!s.story_flags[11] && s.credits == 1 && !s.weapon && s.script.status == BTP_SCRIPT_WAIT);
    enter(&s,r,3,2); restored_tick(&s,r,BTP_ACCEPT);
    CHECK(s.story_flags[11] == 1 && s.credits == 0 && s.weapon == 1);
    enter(&s,r,3,2); restored_tick(&s,r,BTP_RIGHT); restored_tick(&s,r,BTP_ACCEPT);
    CHECK(s.credits == 2 && !s.weapon && s.script.menu_id == 15 && s.script.selected == 1);
    /* Repair remains outside purchases; failed service preserves equipment. */
    enter(&s,r,4,50); restored_tick(&s,r,BTP_ACCEPT); restored_tick(&s,r,BTP_ACCEPT);
    restored_tick(&s,r,BTP_DOWN); restored_tick(&s,r,BTP_ACCEPT);
    CHECK(s.mode == BTP_SCRIPT_FAULT && s.script.error == BTP_SCRIPT_NATIVE_CONTEXT && s.credits == 0 && s.armor == 1);
    restored_tick(&s,r,BTP_CANCEL); CHECK(s.mode == BTP_BUILDING && s.script.menu_id == 12);
    /* Primary threshold compares before adding: repeated funding can exceed cap. */
    btp_start(&s); btp_npc_init(&s,&r->map); s.credits = 43; s.npc.loop_timer = 0;
    btp_npc_frame(&s,&r->map); CHECK(s.credits == 58 && !s.npc.allowance_pending);
    s.npc.loop_timer = 0; btp_npc_frame(&s,&r->map); CHECK(s.credits == 58);
    /* BTP5 migrates its known unspent allowance marker to baseline cash. */
    btp_state_encode(&s,saved); memcpy(saved,"BTP5",4); saved[4] = 5;
    CHECK(btp_state_decode(saved,224,&r->map,NULL,&copy) && copy.credits == 50 && copy.allowance_cap == 50 && !copy.weapon);
    saved[201] = 1; CHECK(btp_state_decode(saved,224,&r->map,NULL,&copy) && copy.credits == 35);
}
static void replay(const BtpResources *r, const char *path)
{
    FILE *f = fopen(path,"r"); CHECK(f != NULL); BtpState s; btp_start(&s); btp_npc_init(&s,&r->map);
    char line[32]; unsigned ticks = 0;
    while (fgets(line,sizeof line,f)) {
        line[strcspn(line,"\r\n")] = 0; BtpAction a; CHECK(btp_action_parse(line,&a));
        restored_tick(&s,r,a); ++ticks;
        CHECK(!s.npc.fault && s.mode != BTP_SCRIPT_FAULT);
    }
    CHECK(!ferror(f) && fclose(f) == 0);
    CHECK(s.mode == BTP_EXPLORE && s.x_half == 32 && s.y_half == 44 && s.weapon == 1 && s.armor == 1 && s.armor_points == 25);
    printf("Shop persistence: %u ticks restored with identical continuation (%s).\n",ticks,path);
}
static void all_goods(const BtpResources *r)
{
    static const unsigned weapons[11]={2,10,100,10,20,35,40,80,250,1500,1500};
    static const unsigned armor[5]={50,150,200,10000,1000}, protection[5]={25,40,30,50,50};
    for (unsigned slot=3;slot<=4;++slot) for (unsigned id=1;id<=(slot == 3 ? 11u : 5u);++id)
        for (unsigned scenario=0;scenario<4;++scenario) {
            unsigned price = slot == 3 ? weapons[id-1] : armor[id-1];
            uint32_t cash = scenario == 0 ? price-1 : scenario == 2 ? 100000u+price : price;
            BtpState s; btp_start(&s); btp_npc_init(&s,&r->map);
            s.credits=cash; s.npc.allowance_pending=(uint8_t)(cash < s.allowance_cap);
            s.weapon=11; s.armor=5; s.armor_points=50;
            s.x_half=r->map.entrance_x[slot]&127; s.y_half=(uint16_t)((r->map.entrance_y[slot]&127)+1);
            restored_tick(&s,r,BTP_UP); restored_tick(&s,r,BTP_ACCEPT); restored_tick(&s,r,BTP_ACCEPT);
            unsigned category = id <= 6 ? 1 : id <= 9 ? 2 : 3;
            unsigned selection = id <= 6 ? id : id <= 9 ? id-6 : id-9;
            if (slot == 3) {
                for (unsigned n=0;n<category;++n) restored_tick(&s,r,BTP_DOWN);
                restored_tick(&s,r,BTP_ACCEPT);
            } else selection=id;
            for (unsigned n=0;n<selection;++n) restored_tick(&s,r,BTP_DOWN);
            restored_tick(&s,r,BTP_ACCEPT); CHECK(s.script.status == BTP_SCRIPT_CONFIRM);
            if (scenario == 3) restored_tick(&s,r,BTP_RIGHT);
            restored_tick(&s,r,BTP_ACCEPT);
            if (scenario == 0 || scenario == 3) {
                CHECK(s.credits == cash && s.weapon == 11 && s.armor == 5 && s.armor_points == 50);
                if (scenario == 0) CHECK(!s.story_flags[11] && s.script.status == BTP_SCRIPT_WAIT);
                else CHECK(s.script.status == BTP_SCRIPT_MENU);
            } else {
                CHECK(s.credits == cash-price && s.story_flags[11] && s.script.status == BTP_SCRIPT_WAIT);
                CHECK(s.weapon == (slot == 3 ? id : 11));
                CHECK(s.armor == (slot == 4 ? id : 5) && s.armor_points == (slot == 4 ? protection[id-1] : 50));
            }
            if (s.script.status == BTP_SCRIPT_WAIT) restored_tick(&s,r,BTP_ACCEPT);
            CHECK(s.mode != BTP_SCRIPT_FAULT);
        }
}
int main(int argc, char **argv)
{
    vm_bounds();
    if (argc == 2) {
        BtpResources *r = malloc(sizeof *r); BtpError e; CHECK(r && btp_resources_load(argv[1],r,&e));
        boundaries(r); all_goods(r); replay(r,"tests/fixtures/reference-shops.actions"); replay(r,"tests/fixtures/reference-shop-boundaries.actions"); free(r);
    }
    printf("PASS: %u shop checks\n",checks); return 0;
}
