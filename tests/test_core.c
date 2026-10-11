#include "frontend/pixels.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks;
#define CHECK(expr) do { ++checks; if (!(expr)) { \
    fprintf(stderr, "%s:%d: %s failed\n", __FILE__, __LINE__, #expr); exit(1); } } while (0)
static void put16(uint8_t *p, unsigned value) { p[0] = (uint8_t)value; p[1] = (uint8_t)(value >> 8); }

static void maps(void)
{
    uint8_t b[541+128] = {0}; BtpMap m; BtpError e;
    b[3] = 16; b[4] = 8;
    for (unsigned i = 0; i < 128; ++i) b[541+i] = (uint8_t)i;
    put16(b+389, 0x0c44); put16(b+421, 0xc014);
    CHECK(btp_map_decode(b, sizeof b, &m, &e));
    CHECK(m.width == 16 && m.height == 8);
    CHECK(btp_map_tile(&m, 7, 0) == 7);
    CHECK(btp_map_tile(&m, 8, 0) == 64);
    CHECK(btp_map_tile(&m, 0, 1) == 8);
    CHECK(btp_map_tile(&m, 15, 7) == 127);
    CHECK(btp_map_tile(&m, -1, 0) == 255);
    CHECK(btp_map_tile(&m, 16, 7) == 255);
    CHECK(m.entrance_x[0] == 0x0c44 && m.entrance_y[0] == 0xc014);
    CHECK(!btp_map_decode(b, sizeof b - 1, &m, &e));
    CHECK(!btp_map_decode(b, 540, &m, &e));
    b[3] = 65; CHECK(!btp_map_decode(b, sizeof b, &m, &e));
    b[3] = 0; CHECK(!btp_map_decode(b, sizeof b, &m, &e));
    b[3] = 15; CHECK(!btp_map_decode(b, sizeof b, &m, &e));
    b[3] = 16; b[0] = 1; CHECK(!btp_map_decode(b, sizeof b, &m, &e));
}
static void graphics(void)
{
    /* Two literals, seven signed repeats, then 31991 repeats = 32000 bytes. */
    uint8_t b[] = {10,0,1,2,0xab,0xcd,0xf9,0xef,0,0xf7,0x7c,0x12};
    BtpGraphic g; BtpError e;
    CHECK(btp_graphic_decode(b, sizeof b, &g, &e));
    CHECK(g.pixels[0] == 10 && g.pixels[1] == 11 && g.pixels[2] == 12 && g.pixels[3] == 13);
    for (unsigned i = 4; i < 18; i += 2) CHECK(g.pixels[i] == 14 && g.pixels[i+1] == 15);
    CHECK(g.pixels[18] == 1 && g.pixels[19] == 2 && g.pixels[63999] == 2);
    b[2] = 2; CHECK(btp_graphic_decode(b, sizeof b, &g, &e));
    CHECK(g.pixels[0] == 10 && g.pixels[1] == 11 && g.pixels[320] == 12 && g.pixels[321] == 13);
    CHECK(g.pixels[640] == 14 && g.pixels[319] == 2);
    b[2] = 3; CHECK(!btp_graphic_decode(b, sizeof b, &g, &e));
    b[2] = 1; CHECK(!btp_graphic_decode(b, sizeof b - 1, &g, &e));
    b[0] = 9; CHECK(!btp_graphic_decode(b, sizeof b, &g, &e));
    b[0] = 10; b[9] = 0xf8; CHECK(!btp_graphic_decode(b, sizeof b, &g, &e));
    b[9] = 0xf6; CHECK(!btp_graphic_decode(b, sizeof b, &g, &e));
    b[9] = 0; b[10] = 0; CHECK(!btp_graphic_decode(b, sizeof b, &g, &e));
    uint8_t bad_literal[] = {2,0,1,127};
    CHECK(!btp_graphic_decode(bad_literal, sizeof bad_literal, &g, &e));
    uint8_t bad_repeat[] = {2,0,1,0x80};
    CHECK(!btp_graphic_decode(bad_repeat, sizeof bad_repeat, &g, &e));
    uint8_t bad_long[] = {3,0,1,0,1};
    CHECK(!btp_graphic_decode(bad_long, sizeof bad_long, &g, &e));
}
static void state(void)
{
    BtpMap m = {.width=64,.height=64}; memset(m.tiles, 64, sizeof m.tiles);
    BtpState s; btp_start(&s);
    CHECK(s.x_half == 69 && s.y_half == 25 && s.gate == 85);
    m.tiles[12*64+35] = 85;
    btp_tick(&s, &m, BTP_RIGHT);
    CHECK(s.x_half == 69 && s.blocked == BTP_WALL && s.tick == 1);
    m.tiles[12*64+35] = 84;
    btp_tick(&s, &m, BTP_RIGHT);
    CHECK(s.x_half == 70 && s.blocked == BTP_CLEAR);
    btp_tick(&s, &m, BTP_LEFT); btp_tick(&s, &m, BTP_UP); btp_tick(&s, &m, BTP_DOWN);
    CHECK(s.x_half == 69 && s.y_half == 25 && s.tick == 5);
    BtpState west = s; west.x_half = 68; west.y_half = 22;
    m.tiles[11*64+33] = 181;
    btp_tick(&west, &m, BTP_LEFT);
    CHECK(west.x_half == 67 && west.blocked == BTP_CLEAR);
    btp_tick(&west, &m, BTP_LEFT);
    CHECK(west.x_half == 67 && west.blocked == BTP_WALL);
    uint8_t encoded[BTP_STATE_BYTES], roundtrip[BTP_STATE_BYTES];
    btp_state_encode(&s, encoded);
    BtpState restored;
    CHECK(btp_state_decode(encoded, sizeof encoded, &m, NULL, &restored));
    btp_state_encode(&restored, roundtrip);
    CHECK(!memcmp(encoded, roundtrip, sizeof encoded));
    for (unsigned i = 0; i < 100; ++i) {
        BtpAction a = i % 2 ? BTP_LEFT : BTP_RIGHT;
        btp_tick(&s, &m, a); btp_tick(&restored, &m, a);
    }
    btp_state_encode(&s, encoded); btp_state_encode(&restored, roundtrip);
    CHECK(!memcmp(encoded, roundtrip, sizeof encoded));
    CHECK(!btp_state_decode(encoded, sizeof encoded - 1, &m, NULL, &restored));
    encoded[4] = 3; CHECK(!btp_state_decode(encoded, sizeof encoded, &m, NULL, &restored));
    encoded[4] = 2; encoded[12] = 128; CHECK(!btp_state_decode(encoded, sizeof encoded, &m, NULL, &restored));
    encoded[12] = 69; encoded[23] = 1; CHECK(!btp_state_decode(encoded, sizeof encoded, &m, NULL, &restored));
    s.x_half = 0; s.y_half = 0; btp_tick(&s, &m, BTP_LEFT);
    CHECK(s.x_half == 0 && s.blocked == BTP_EDGE);
    btp_tick(&s, &m, BTP_UP); CHECK(s.y_half == 0 && s.blocked == BTP_EDGE);
    s.x_half = 127; s.y_half = 127; btp_tick(&s, &m, BTP_RIGHT); btp_tick(&s, &m, BTP_DOWN);
    CHECK(s.x_half == 127 && s.y_half == 127 && s.blocked == BTP_EDGE);
    s.tick = UINT32_MAX; btp_tick(&s, &m, BTP_IDLE); CHECK(s.tick == 0);
    BtpAction a; CHECK(!btp_action_parse("unknown", &a)); CHECK(btp_action_parse("right", &a) && a == BTP_RIGHT);
    m.entrance_x[0] = 0x0c44; m.entrance_y[0] = 0xc014;
    s.x_half = 68; s.y_half = 20; CHECK(btp_entrance(&s, &m) == 0);
}
static void pixels(void)
{
    BtpResources *r = calloc(1, sizeof *r);
    uint32_t *a = malloc(BTP_PIXELS * sizeof *a), *b = malloc(BTP_PIXELS * sizeof *b);
    CHECK(r && a && b);
    r->map.width = r->map.height = 64;
    for (unsigned i = 0; i < 256; ++i) r->tiles.pixels[i] = (uint8_t)(i % 16);
    BtpState s; btp_start(&s);
    btp_render(r, &s, 0, a); btp_render(r, &s, 0, b);
    CHECK(!memcmp(a, b, BTP_PIXELS * sizeof *a));
    CHECK(a[104] == btp_palette[8]); /* camera_x=456, tile pixel column=8 */
    CHECK(a[105] == btp_palette[1]); /* observed MAP1 index-9 remap */
    CHECK(a[117] == btp_palette[9]); /* observed MAP1 index-5 remap */
    CHECK(a[100*320+212] == btp_palette[1]);
    CHECK(a[0] == btp_palette[7]);
    s.x_half = s.y_half = 0; btp_render(r, &s, 1, a);
    CHECK(a[104] == btp_palette[0]);
    /* Resource case must survive rendering; lowercase has its own glyph. */
    r->citadel = (BtpBld){.length=5,.bytes={0xfc,'A','a',0,0xfb}};
    s.mode = BTP_BUILDING; btp_script_start(&s.script, &r->citadel);
    btp_render(r, &s, 0, a);
    CHECK(a[9*320+111] == btp_palette[15]);
    CHECK(a[9*320+117] == btp_palette[0]);
    CHECK(a[11*320+117] == btp_palette[15]);
    free(a); free(b); free(r);
}

static void restored_tick(BtpState *s, const BtpResources *r, BtpAction action)
{
    uint8_t before[BTP_STATE_BYTES], after[BTP_STATE_BYTES], restored[BTP_STATE_BYTES];
    btp_state_encode(s, before);
    BtpState copy;
    CHECK(btp_state_decode(before, sizeof before, &r->map, &r->citadel, &copy));
    btp_state_encode(&copy, restored); CHECK(!memcmp(before, restored, sizeof before));
    btp_game_tick(s, r, action); btp_game_tick(&copy, r, action);
    btp_state_encode(s, after); btp_state_encode(&copy, restored);
    CHECK(!memcmp(after, restored, sizeof after));
}
static void citadel_loop(const char *dir)
{
    BtpResources *r = malloc(sizeof *r); CHECK(r);
    BtpError error; CHECK(btp_resources_load(dir, r, &error));
    BtpState s; btp_start(&s);
    for (unsigned i = 0; i < 5; ++i) btp_game_tick(&s, r, BTP_UP);
    CHECK(s.mode == BTP_ENTRY && s.x_half == 69 && s.y_half == 21);
    restored_tick(&s, r, BTP_IDLE);
    CHECK(s.mode == BTP_ENTRY && s.story_flags[10] == 0);
    restored_tick(&s, r, BTP_CANCEL);
    CHECK(s.mode == BTP_EXPLORE && s.y_half == 20 && s.story_flags[10] == 0);
    btp_start(&s);
    for (unsigned i = 0; i < 5; ++i) btp_game_tick(&s, r, BTP_UP);
    restored_tick(&s, r, BTP_ACCEPT);
    CHECK(s.mode == BTP_BUILDING && s.y_half == 21 && s.story_flags[10] == 1);
    restored_tick(&s, r, BTP_DOWN);
    CHECK(s.script.selected == 1);
    restored_tick(&s, r, BTP_ACCEPT);
    for (unsigned i = 0; i < 6; ++i) {
        CHECK(s.script.status == BTP_SCRIPT_WAIT && s.mode == BTP_BUILDING && s.y_half == 21);
        restored_tick(&s, r, BTP_IDLE);
        CHECK(s.script.status == BTP_SCRIPT_WAIT);
        restored_tick(&s, r, BTP_ACCEPT);
    }
    CHECK(s.script.status == BTP_SCRIPT_MENU && s.script.selected == 1);
    for (unsigned i = 0; i < 3; ++i) restored_tick(&s, r, BTP_DOWN);
    restored_tick(&s, r, BTP_ACCEPT);
    CHECK(s.mode == BTP_EXPLORE && s.y_half == 20 && s.script.status == BTP_SCRIPT_END);
    restored_tick(&s, r, BTP_DOWN);
    CHECK(s.y_half == 21 && s.story_flags[10] == 1);
    btp_start(&s);
    for (unsigned i = 0; i < 5; ++i) btp_game_tick(&s, r, BTP_UP);
    btp_game_tick(&s, r, BTP_ACCEPT); btp_game_tick(&s, r, BTP_ACCEPT);
    CHECK(s.mode == BTP_SCRIPT_FAULT && s.script.last_opcode == 0xf3 && s.y_half == 21);
    restored_tick(&s, r, BTP_CANCEL);
    CHECK(s.mode == BTP_BUILDING && s.script.status == BTP_SCRIPT_MENU);
    uint8_t saved[BTP_STATE_BYTES]; btp_state_encode(&s, saved); BtpState invalid;
    saved[42] = saved[43] = 255;
    CHECK(!btp_state_decode(saved, sizeof saved, &r->map, &r->citadel, &invalid));
    btp_state_encode(&s, saved); saved[46] = saved[47] = 255;
    CHECK(!btp_state_decode(saved, sizeof saved, &r->map, &r->citadel, &invalid));
    btp_state_encode(&s, saved); saved[52] = BTP_SCRIPT_END;
    CHECK(!btp_state_decode(saved, sizeof saved, &r->map, &r->citadel, &invalid));
    uint8_t legacy[24] = {'B','T','P','1',1,0,0,0,0,0,0,0,69,0,25,0,1,85,0,0,0,0,0,0};
    CHECK(btp_state_decode(legacy, sizeof legacy, &r->map, &r->citadel, &invalid));
    CHECK(invalid.mode == BTP_EXPLORE && invalid.x_half == 69 && invalid.script.pc == 0);
    /* Exact half coordinates, not the neighboring half in the same tile. */
    r->map = (BtpMap){.width=64,.height=64}; memset(r->map.tiles, 64, sizeof r->map.tiles);
    r->map.entrance_x[1] = 0x0c45; r->map.entrance_y[1] = 0xc014;
    btp_start(&s); s.x_half = 68; s.y_half = 21;
    btp_game_tick(&s, r, BTP_UP); CHECK(s.mode == BTP_EXPLORE && s.y_half == 20);
    btp_start(&s); s.y_half = 21;
    btp_game_tick(&s, r, BTP_UP); CHECK(s.mode == BTP_ENTRY && s.y_half == 21);
    free(r);
    puts("Citadel core: entry/decline, six dialogue screens, exit, error recovery, mid-dialogue BTP2 restore.");
}

static void corpus(const char *dir)
{
    char path[4096]; uint8_t *b; size_t n; BtpMap m; BtpGraphic g; BtpError e;
    for (unsigned i = 1; i <= 14; ++i) {
        snprintf(path, sizeof path, "%s/MAP%u.MTP", dir, i);
        CHECK(btp_read_file(path, &b, &n, &e)); CHECK(btp_map_decode(b, n, &m, &e)); free(b);
    }
    const char *names[] = {"BTTLTECH.ICN","ANIMATE.ICN","MAP.ICN","STARLEAG.ICN","DESTRUCT.ICN",
        "BTTITLE.CMP","INFOCOM.CMP","BTSTATS.CMP","BTBORDER.CMP","MECHSHAP.CMP","ENDMECH.CMP","TINYLAND.CMP"};
    for (unsigned i = 0; i < sizeof names / sizeof names[0]; ++i) {
        snprintf(path, sizeof path, "%s/%s", dir, names[i]);
        CHECK(btp_read_file(path, &b, &n, &e));
        if (!btp_graphic_decode(b, n, &g, &e)) { fprintf(stderr, "%s: %s\n", path, e.text); exit(1); }
        ++checks;
        int valid = 1;
        for (unsigned j = 0; j < BTP_PIXELS; ++j) if (g.pixels[j] >= 16) valid = 0;
        CHECK(valid);
        free(b);
    }
    snprintf(path, sizeof path, "%s/MAP15.MTP", dir);
    CHECK(btp_read_file(path, &b, &n, &e)); CHECK(!btp_map_decode(b, n, &m, &e)); free(b);
    puts("Authentic corpus: 14 MTP + 12 ICN/CMP decoded; raw MAP15 explicitly rejected.");
}
int main(int argc, char **argv)
{
    maps(); graphics(); state(); pixels();
    if (argc == 2) { corpus(argv[1]); citadel_loop(argv[1]); }
    printf("PASS: %u checks\n", checks);
    return 0;
}
