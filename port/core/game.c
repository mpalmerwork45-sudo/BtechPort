#include "core/game.h"
#include <string.h>

void btp_start(BtpState *s)
{
    *s = (BtpState){.x_half = 69, .y_half = 25, .map_id = 1, .gate = 85};
}

void btp_tick(BtpState *s, const BtpMap *m, BtpAction a)
{
    ++s->tick; /* Explicit unsigned wrapping; no clock or graphics dependency. */
    if (a < BTP_UP || a > BTP_RIGHT) return;
    s->facing = (uint8_t)a;
    int x = s->x_half, y = s->y_half;
    if (a == BTP_UP) --y;
    if (a == BTP_DOWN) ++y;
    if (a == BTP_LEFT) --x;
    if (a == BTP_RIGHT) ++x;
    if (x < 0 || y < 0 || x >= 2 * m->width || y >= 2 * m->height) {
        s->blocked = BTP_EDGE;
        return;
    }
    /* The reference trace includes x=68 -> 67 (free) -> 66 (blocked).
       Collision samples the player's offset position, not the cursor's tile:
       ceil(x_half/2), floor(y_half/2). Multi-unit footprints are deferred. */
    int tile_x = (x + 1) / 2, tile_y = y / 2;
    if (tile_x >= m->width) { s->blocked = BTP_EDGE; return; }
    if (btp_map_tile(m, tile_x, tile_y) >= s->gate) {
        s->blocked = BTP_WALL;
        return;
    }
    s->x_half = (uint16_t)x; s->y_half = (uint16_t)y; s->blocked = BTP_CLEAR;
}

int btp_entrance(const BtpState *s, const BtpMap *m)
{
    for (int i = 0; i < 8; ++i)
        if (s->x_half / 2 == (m->entrance_x[i] & 127) / 2 &&
            s->y_half / 2 == (m->entrance_y[i] & 127) / 2) return i;
    return -1;
}

void btp_state_encode(const BtpState *s, uint8_t b[BTP_STATE_BYTES])
{
    memset(b, 0, BTP_STATE_BYTES);
    memcpy(b, "BTP1", 4); b[4] = 1;
    for (unsigned i = 0; i < 4; ++i) b[8+i] = (uint8_t)(s->tick >> (8 * i));
    b[12] = (uint8_t)s->x_half; b[13] = (uint8_t)(s->x_half >> 8);
    b[14] = (uint8_t)s->y_half; b[15] = (uint8_t)(s->y_half >> 8);
    b[16] = s->map_id; b[17] = s->gate; b[18] = s->facing; b[19] = s->blocked;
}

int btp_state_decode(const uint8_t *b, size_t n, const BtpMap *m, BtpState *s)
{
    if (!b || !m || !s || n != BTP_STATE_BYTES || memcmp(b, "BTP1", 4) || b[4] != 1) return 0;
    for (unsigned i = 5; i < 8; ++i) if (b[i]) return 0;
    for (unsigned i = 20; i < 24; ++i) if (b[i]) return 0;
    BtpState result = {0};
    for (unsigned i = 0; i < 4; ++i) result.tick |= (uint32_t)b[8+i] << (8 * i);
    result.x_half = (uint16_t)(b[12] | (uint16_t)b[13] << 8);
    result.y_half = (uint16_t)(b[14] | (uint16_t)b[15] << 8);
    result.map_id = b[16]; result.gate = b[17]; result.facing = b[18]; result.blocked = b[19];
    if (result.map_id != 1 || result.gate != 85 || result.facing > BTP_RIGHT ||
        result.blocked > BTP_EDGE || result.x_half >= 2 * m->width || result.y_half >= 2 * m->height)
        return 0;
    *s = result;
    return 1;
}

const char *btp_action_name(BtpAction a)
{
    static const char *names[] = {"idle", "up", "down", "left", "right"};
    return a >= BTP_IDLE && a <= BTP_RIGHT ? names[a] : "invalid";
}
int btp_action_parse(const char *name, BtpAction *a)
{
    for (int i = BTP_IDLE; i <= BTP_RIGHT; ++i)
        if (!strcmp(name, btp_action_name((BtpAction)i))) { *a = (BtpAction)i; return 1; }
    return 0;
}
