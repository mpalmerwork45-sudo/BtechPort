#include "frontend/pixels.h"
#include "core/animation.h"
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
    encoded[4] = 255; CHECK(!btp_state_decode(encoded, sizeof encoded, &m, NULL, &restored));
    encoded[4] = 12; encoded[12] = 128; CHECK(!btp_state_decode(encoded, sizeof encoded, &m, NULL, &restored));
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
static void diagonals(void)
{
    BtpMap m = {.width=64,.height=64}; memset(m.tiles,64,sizeof m.tiles);
    /* Original N,NE,E,SE,S,SW,W,NW direction and first-frame tables. */
    static const BtpAction actions[8] = {BTP_UP,BTP_UP_RIGHT,BTP_RIGHT,BTP_DOWN_RIGHT,
        BTP_DOWN,BTP_DOWN_LEFT,BTP_LEFT,BTP_UP_LEFT};
    static const int dx[8] = {0,1,1,1,0,-1,-1,-1}, dy[8] = {-1,-1,0,1,1,1,0,-1};
    static const unsigned first[8] = {8,4,4,4,0,12,12,12};
    for (unsigned d=0;d<8;++d) {
        BtpState s; btp_start(&s); s.x_half=s.y_half=64;
        s.facing=(uint8_t)actions[(d+4u)&7u];
        BtpAction parsed;
        CHECK(btp_action_parse(btp_action_name(actions[d]),&parsed) && parsed == actions[d]);
        CHECK(btp_player_direction((unsigned)actions[d]) == d);
        for (unsigned step=0;step<5;++step) {
            btp_tick(&s,&m,actions[d]);
            CHECK(s.x_half == 64+(int)(step+1)*dx[d] && s.y_half == 64+(int)(step+1)*dy[d]);
            CHECK(s.blocked == BTP_CLEAR && s.tick == step+1 && s.player_walk == first[d]+step%4);
            uint8_t bytes[BTP_STATE_BYTES]; BtpState copy;
            btp_state_encode(&s,bytes); CHECK(btp_state_decode(bytes,sizeof bytes,&m,NULL,&copy));
            CHECK(copy.facing == actions[d] && copy.player_walk == s.player_walk);
            if (d & 1u) {
                memcpy(bytes,"BTP9",4); bytes[4]=9;
                CHECK(!btp_state_decode(bytes,416,&m,NULL,&copy));
            }
        }
    }
    BtpState s; btp_start(&s); s.x_half=68; s.y_half=22;
    m.tiles[10*64+35]=85; /* NE destination; both axes must remain in place. */
    btp_tick(&s,&m,BTP_UP_RIGHT);
    CHECK(s.x_half == 68 && s.y_half == 22 && s.blocked == BTP_WALL && s.player_walk == 4);
    btp_tick(&s,&m,BTP_UP_RIGHT); CHECK(s.player_walk == 5 && s.tick == 2);
    m.tiles[10*64+35]=64; m.tiles[11*64+35]=85; m.tiles[10*64+34]=85;
    btp_tick(&s,&m,BTP_UP_RIGHT); /* Original checks the destination, even between walls. */
    CHECK(s.x_half == 69 && s.y_half == 21 && s.blocked == BTP_CLEAR && s.player_walk == 6);
    s.x_half=s.y_half=0; btp_tick(&s,&m,BTP_UP_LEFT);
    CHECK(s.x_half == 0 && s.y_half == 0 && s.blocked == BTP_EDGE && s.player_walk == 12);
    s.x_half=s.y_half=127; btp_tick(&s,&m,BTP_DOWN_RIGHT);
    CHECK(s.x_half == 127 && s.y_half == 127 && s.blocked == BTP_EDGE && s.player_walk == 4);
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
    CHECK(a[100*320+212] == btp_palette[4]); /* Empty test atlas leaves terrain visible. */
    CHECK(a[0] == btp_palette[7]);
    s.x_half = s.y_half = 0; btp_render(r, &s, 1, a);
    CHECK(a[104] == btp_palette[0]);
    /* Resource case must survive rendering; lowercase has its own glyph. */
    r->citadel = (BtpBld){.length=5,.bytes={0xfc,'A','a',0,0xfb}};
    s.mode = BTP_BUILDING; s.entry_slot = 1; btp_script_start(&s.script, &r->citadel, s.story_flags);
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
static void katrina_loop(const BtpResources *r)
{
    BtpState s; btp_start(&s);
    for (unsigned i = 0; i < 5; ++i) btp_game_tick(&s, r, BTP_UP);
    restored_tick(&s, r, BTP_ACCEPT); restored_tick(&s, r, BTP_ACCEPT);
    CHECK(s.script.pc == 0x1aa && s.script.status == BTP_SCRIPT_WAIT && s.story_flags[6] == 0);
    restored_tick(&s, r, BTP_IDLE); restored_tick(&s, r, BTP_ACCEPT);
    CHECK(s.script.pc == 0x349 && s.script.text_count == 3 && s.story_flags[6] == 1 && s.story_flags[22] == 255);
    uint8_t saved[BTP_STATE_BYTES]; BtpState invalid;
    btp_state_encode(&s, saved); saved[66] = BTP_TEXT_SPANS + 1;
    CHECK(!btp_state_decode(saved, sizeof saved, &r->map, &r->citadel, &invalid));
    btp_state_encode(&s, saved); saved[72] = saved[73] = 255;
    CHECK(!btp_state_decode(saved, sizeof saved, &r->map, &r->citadel, &invalid));
    btp_state_encode(&s, saved); ++saved[44];
    CHECK(!btp_state_decode(saved, sizeof saved, &r->map, &r->citadel, &invalid));
    btp_state_encode(&s, saved); saved[123] = 0; /* nonempty checkpoint requires its marker */
    CHECK(!btp_state_decode(saved, sizeof saved, &r->map, &r->citadel, &invalid));
    restored_tick(&s, r, BTP_ACCEPT);
    CHECK(s.script.status == BTP_SCRIPT_MENU && s.script.selected == 0 && s.story_flags[6] == 1 && !s.checkpoint_valid);
    restored_tick(&s, r, BTP_ACCEPT);
    CHECK(s.script.pc == 0x424 && s.script.status == BTP_SCRIPT_WAIT && s.story_flags[6] == 1);
    restored_tick(&s, r, BTP_ACCEPT); restored_tick(&s, r, BTP_UP);
    CHECK(s.script.selected == 4);
    restored_tick(&s, r, BTP_ACCEPT); restored_tick(&s, r, BTP_DOWN); restored_tick(&s, r, BTP_UP);
    CHECK(s.mode == BTP_ENTRY && s.y_half == 21 && s.story_flags[6] == 1);
    restored_tick(&s, r, BTP_ACCEPT);
    CHECK(s.mode == BTP_BUILDING && s.script.selected == 4 && s.story_flags[6] == 1);
    /* Corrupt only a test-owned BLD copy to retain the unknown-action rollback
       regression now that real Class is supported. Byte 21 is a test seed. */
    BtpResources *broken = malloc(sizeof *broken); CHECK(broken); *broken = *r;
    broken->citadel.bytes[0xf04] = 3;
    s.story_flags[21] = 42;
    for (unsigned i = 0; i < 3; ++i) restored_tick(&s, r, BTP_UP);
    CHECK(s.script.selected == 1);
    restored_tick(&s, r, BTP_DOWN); restored_tick(&s, r, BTP_ACCEPT);
    CHECK(s.script.status == BTP_SCRIPT_WAIT && s.story_flags[7] == 1 && s.story_flags[21] == 0);
    restored_tick(&s, broken, BTP_ACCEPT);
    CHECK(s.mode == BTP_SCRIPT_FAULT && s.script.last_opcode == 0xf5 && s.story_flags[7] == 0 &&
          s.story_flags[21] == 42 && s.story_flags[6] == 1 && s.story_flags[22] == 255);
    free(broken);
    restored_tick(&s, r, BTP_CANCEL); restored_tick(&s, r, BTP_DOWN); restored_tick(&s, r, BTP_ACCEPT);
    CHECK(s.mode == BTP_BUILDING && s.talk.phase == BTP_TALK_EMPTY && s.story_flags[13] == 1 && s.story_flags[6] == 1);
    restored_tick(&s, r, BTP_ACCEPT);
    CHECK(s.mode == BTP_BUILDING && s.script.selected == 3);
    /* Migrate a real M2a Hall pause from its 64-byte BTP2 representation. */
    btp_start(&s);
    for (unsigned i = 0; i < 5; ++i) btp_game_tick(&s, r, BTP_UP);
    btp_game_tick(&s, r, BTP_ACCEPT); btp_game_tick(&s, r, BTP_DOWN); btp_game_tick(&s, r, BTP_ACCEPT);
    btp_state_encode(&s, saved);
    uint8_t old[64] = {0}; memcpy(old, saved, 59); memcpy(old, "BTP2", 4); old[4] = 2;
    CHECK(btp_state_decode(old, sizeof old, &r->map, &r->citadel, &invalid));
    CHECK(invalid.script.text_count == 1 && invalid.script.pc == 0x77e && invalid.checkpoint_valid);
    /* Old formats had no NPC context. Empty occupancy remains explicit. */
    memset(s.npc_pairs,0,sizeof s.npc_pairs);
    memset(s.npc_walk,0,sizeof s.npc_walk); /* Legacy formats did not store animation. */
    s.player_walk = 8; /* First north-facing frame. */
    s.npc = (BtpNpcState){0}; /* Legacy saves had no travel clock/positions. */
    s.late=(BtpLateState){0}; /* BTP2 had no saved direction log. */
    btp_game_tick(&s, r, BTP_ACCEPT); btp_game_tick(&invalid, r, BTP_ACCEPT);
    uint8_t migrated[BTP_STATE_BYTES]; btp_state_encode(&s, saved); btp_state_encode(&invalid, migrated);
    if (memcmp(saved,migrated,sizeof saved)) for (unsigned i=0;i<BTP_STATE_BYTES;++i)
        if (saved[i]!=migrated[i]) fprintf(stderr,"legacy continuation byte %u: %u != %u\n",i,saved[i],migrated[i]);
    CHECK(!memcmp(saved, migrated, sizeof saved));
    puts("Katrina core: pause restoration, persistent bytes, repeat denial, re-entry, class rollback, Talk continuation, BTP2 migration.");
}
static void enter_talk(BtpState *s, const BtpResources *r)
{
    for (unsigned i = 0; i < 5; ++i) btp_game_tick(s,r,BTP_UP);
    btp_game_tick(s,r,BTP_ACCEPT);
    for (unsigned i = 0; i < 3; ++i) btp_game_tick(s,r,BTP_DOWN);
    btp_game_tick(s,r,BTP_ACCEPT);
}
static void talk_loop(BtpResources *r)
{
    BtpState s, invalid; btp_start_conversation_checkpoint(&s); enter_talk(&s,r);
    CHECK(s.mode == BTP_BUILDING && s.script.status == BTP_SCRIPT_NATIVE && s.script.pc == 0x10e2);
    CHECK(s.talk.phase == BTP_TALK_MENU && s.talk.mask == 2 && s.talk.count == 1 &&
          s.script.selected == 3 && s.story_flags[13] == 1 && s.talk_result == 91);
    uint8_t body[BTP_BLD_MAX+1]; size_t length;
    CHECK(btp_game_text(&s,r,body,sizeof body,&length) && length == 42);
    CHECK(!btp_game_text(&s,r,body,42,&length));
    restored_tick(&s,r,BTP_IDLE); restored_tick(&s,r,BTP_DOWN); restored_tick(&s,r,BTP_ACCEPT);
    CHECK(s.script.status == BTP_SCRIPT_MENU && s.talk.selected == 1 && s.talk_result == 91 &&
          s.story_flags[13] == 1 && !s.checkpoint_valid);
    restored_tick(&s,r,BTP_ACCEPT); CHECK(s.talk.phase == BTP_TALK_MENU && s.talk.selected == 1);
    restored_tick(&s,r,BTP_UP); restored_tick(&s,r,BTP_ACCEPT);
    CHECK(s.talk.phase == BTP_TALK_REPLY && s.talk.actor == 1 && !s.talk_result && s.script.selected == 3);
    CHECK(btp_game_text(&s,r,body,sizeof body,&length) && length == 162);
    uint8_t saved[BTP_STATE_BYTES];
    const unsigned bad_indexes[] = {123,125,126,127,131,145,146,150};
    for (unsigned i = 0; i < sizeof bad_indexes/sizeof bad_indexes[0]; ++i) {
        btp_state_encode(&s,saved); saved[bad_indexes[i]] ^= 1;
        CHECK(!btp_state_decode(saved,sizeof saved,&r->map,&r->citadel,&invalid));
    }
    btp_state_encode(&s,saved); saved[40] = 0xe3; /* Wrong suspended native PC. */
    CHECK(!btp_state_decode(saved,sizeof saved,&r->map,&r->citadel,&invalid));
    restored_tick(&s,r,BTP_IDLE); restored_tick(&s,r,BTP_ACCEPT);
    CHECK(s.script.status == BTP_SCRIPT_MENU && s.script.selected == 3 && !s.talk.phase && !s.talk_result);
    /* Restore a BTP3 Katrina pause: this format predates NPC context. */
    btp_start(&s);
    for (unsigned i = 0; i < 5; ++i) btp_game_tick(&s,r,BTP_UP);
    btp_game_tick(&s,r,BTP_ACCEPT); btp_game_tick(&s,r,BTP_ACCEPT); btp_game_tick(&s,r,BTP_ACCEPT);
    btp_state_encode(&s,saved);
    uint8_t old[128]; memcpy(old,saved,sizeof old); memcpy(old,"BTP3",4); old[4] = 3;
    CHECK(btp_state_decode(old,sizeof old,&r->map,&r->citadel,&invalid));
    CHECK(invalid.story_flags[6] == 1 && invalid.script.text_count == 3 && !invalid.npc_pairs[1][1]);
    memset(s.npc_pairs,0,sizeof s.npc_pairs);
    memset(s.npc_walk,0,sizeof s.npc_walk); /* Legacy formats did not store animation. */
    s.player_walk = 8; /* First north-facing frame. */
    s.npc = (BtpNpcState){0};
    s.late=(BtpLateState){0}; /* BTP3 predates the direction log too. */
    btp_game_tick(&s,r,BTP_ACCEPT); btp_game_tick(&invalid,r,BTP_ACCEPT);
    uint8_t migrated[BTP_STATE_BYTES]; btp_state_encode(&s,saved); btp_state_encode(&invalid,migrated);
    CHECK(!memcmp(saved,migrated,sizeof saved));
    /* Unknown contexts and missing data fail visibly, rolling back the choice. */
    uint16_t cache_length = r->dialogue.length; r->dialogue.length = 0;
    btp_start_conversation_checkpoint(&s); enter_talk(&s,r);
    CHECK(s.mode == BTP_SCRIPT_FAULT && s.script.error == BTP_SCRIPT_NATIVE_DATA &&
          s.talk_result == 91 && !s.story_flags[13]);
    restored_tick(&s,r,BTP_CANCEL); r->dialogue.length = cache_length;
    /* 07DC:17C6..17EC returns room 8 when no category matches. The original
       then shows its normal empty-room response, including after invasion. */
    uint8_t room=r->map.room_map[1];r->map.room_map[1]=26;
    s.story_flags[4] = 1; restored_tick(&s,r,BTP_ACCEPT);
    CHECK(s.mode == BTP_BUILDING && s.talk.phase == BTP_TALK_EMPTY && s.talk.room == 8 &&
          s.story_flags[4] == 1 && s.story_flags[13] == 1 && s.talk_result == 91);
    restored_tick(&s,r,BTP_ACCEPT);CHECK(s.script.status==BTP_SCRIPT_MENU && !s.talk.phase);
    r->map.room_map[1]=room;
    /* A fault after the native reply also restores the pre-choice result. */
    btp_start_conversation_checkpoint(&s); enter_talk(&s,r); btp_game_tick(&s,r,BTP_ACCEPT);
    uint8_t opcode = r->citadel.bytes[0x10e2]; r->citadel.bytes[0x10e2] = 0xe0;
    restored_tick(&s,r,BTP_ACCEPT);
    CHECK(s.mode == BTP_SCRIPT_FAULT && s.talk_result == 91 && !s.story_flags[13]);
    r->citadel.bytes[0x10e2] = opcode;
    /* Multiple occupants: slot order, bit-7 masking, all nine choices and wrap.
       These are structural tests, not a multi-occupant original-game trace. */
    btp_start_conversation_checkpoint(&s);
    for (unsigned i = 0; i < 8; ++i) { s.npc_pairs[i][0] = (uint8_t)(0x10u+i); s.npc_pairs[i][1] = 1; }
    s.npc_pairs[2][0] |= 0x80;
    enter_talk(&s,r); CHECK(s.talk.count == 8 && s.talk.mask == 255);
    restored_tick(&s,r,BTP_UP); CHECK(s.talk.selected == 8);
    restored_tick(&s,r,BTP_DOWN); CHECK(s.talk.selected == 0);
    for (unsigned i = 0; i < 3; ++i) restored_tick(&s,r,BTP_DOWN);
    restored_tick(&s,r,BTP_ACCEPT); CHECK(s.talk.actor == 3 && s.talk_result == 0);
    /* Cache parser corruption must not mutate a previously valid result. */
    uint8_t *cache; size_t n; BtpError error;
    CHECK(btp_read_file("work/talk-data.bin",&cache,&n,&error));
    BtpDialogue parsed;
    CHECK(btp_dialogue_decode(cache,n,&parsed,&error));
    CHECK(!memcmp(&parsed,&r->dialogue,sizeof parsed));
    CHECK(!btp_dialogue_decode(NULL,n,&parsed,&error));
    CHECK(!btp_dialogue_decode(cache,n-1,&parsed,&error));
    const unsigned corrupt[] = {0,4,6,8,40,72,74,72+4*BTP_TALK_STRINGS};
    for (unsigned i = 0; i < sizeof corrupt/sizeof corrupt[0]; ++i) {
        unsigned at = corrupt[i]; uint8_t before = cache[at]; cache[at] = at == 72+4*BTP_TALK_STRINGS ? 0 : (uint8_t)(before^1);
        CHECK(!btp_dialogue_decode(cache,n,&parsed,&error));
        CHECK(!memcmp(&parsed,&r->dialogue,sizeof parsed)); cache[at] = before;
    }
    free(cache);
    puts("Talk core: Done/selection retention, exact text lengths, result write, pause restoration, invalid states/cache, BTP3 migration, recovery and multi-occupant bounds.");
}
static void citadel_loop(const char *dir)
{
    BtpResources *r = malloc(sizeof *r); CHECK(r);
    BtpError error; CHECK(btp_resources_load(dir, r, &error));
    CHECK(btp_dialogue_load("work/talk-data.bin",&r->dialogue,&error));
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
    btp_game_tick(&s, r, BTP_ACCEPT);
    for (unsigned i = 0; i < 3; ++i) btp_game_tick(&s, r, BTP_DOWN);
    btp_game_tick(&s, r, BTP_ACCEPT);
    CHECK(s.mode == BTP_BUILDING && s.talk.phase == BTP_TALK_EMPTY && s.y_half == 21 && s.story_flags[13] == 1);
    restored_tick(&s, r, BTP_ACCEPT);
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
    katrina_loop(r);
    talk_loop(r);
    /* Exact half coordinates, not the neighboring half in the same tile. */
    r->map = (BtpMap){.width=64,.height=64}; memset(r->map.tiles, 64, sizeof r->map.tiles);
    r->map.entrance_x[1] = 0x0c45; r->map.entrance_y[1] = 0xc014;
    btp_start(&s); s.x_half = 68; s.y_half = 21;
    btp_game_tick(&s, r, BTP_UP); CHECK(s.mode == BTP_EXPLORE && s.y_half == 20);
    btp_start(&s); s.y_half = 21;
    btp_game_tick(&s, r, BTP_UP); CHECK(s.mode == BTP_ENTRY && s.y_half == 21);
    static const BtpAction diagonal[4] = {BTP_UP_LEFT,BTP_UP_RIGHT,BTP_DOWN_LEFT,BTP_DOWN_RIGHT};
    for (unsigned i=0;i<4;++i) {
        btp_start(&s); s.x_half=(uint16_t)(69-btp_action_dx(diagonal[i]));
        s.y_half=(uint16_t)(20-btp_action_dy(diagonal[i]));
        unsigned x=s.x_half,y=s.y_half;
        restored_tick(&s,r,diagonal[i]);
        CHECK(s.mode == BTP_ENTRY && s.entry_action == diagonal[i] && s.x_half == x && s.y_half == y);
        restored_tick(&s,r,BTP_CANCEL);
        CHECK(s.mode == BTP_EXPLORE && s.x_half == 69 && s.y_half == 20);
    }
    free(r);
    puts("Citadel core: entry/decline, six Hall screens, exit, empty Talk, recovery, BTP9 restoration.");
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
static void entry_text(const char *dir)
{
    BtpResources *r=malloc(sizeof *r); uint32_t *f=malloc(BTP_PIXELS*sizeof *f); BtpError e;
    CHECK(r && f && btp_resources_load(dir,r,&e));
    CHECK(btp_dialogue_load("work/talk-data.bin",&r->dialogue,&e));
    for (unsigned slot=0;slot<8;++slot) for (unsigned selected=0;selected<2;++selected) {
        BtpState s; btp_start(&s); s.mode=BTP_ENTRY; s.entry_slot=(uint8_t)slot; s.entry_selected=(uint8_t)selected;
        btp_render(r,&s,0,f);
        const char *labels[]={"Yes","No"};
        for (unsigned label=0;label<2;++label) for (unsigned letter=0;letter<strlen(labels[label]);++letter)
            for (unsigned y=0;y<8;++y) for (unsigned x=0;x<8;++x) {
                unsigned bits=r->dialogue.font[8u*(uint8_t)labels[label][letter]+y];
                unsigned color=selected==label ? (bits&(128u>>x) ? 0u : 14u) : (bits&(128u>>x) ? 15u : 0u);
                CHECK(f[(96u+y)*320u+(label ? 144u : 112u)+8u*letter+x] == btp_palette[color]);
            }
    }
    free(f); free(r);
}
int main(int argc, char **argv)
{
    maps(); graphics(); state(); diagonals(); pixels();
    if (argc == 2) { corpus(argv[1]); citadel_loop(argv[1]); entry_text(argv[1]); }
    printf("PASS: %u checks\n", checks);
    return 0;
}
