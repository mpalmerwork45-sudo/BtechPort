#include "core/npc.h"
#include "core/economy.h"
#include "core/animation.h"

/* Independently expressed from 193B0..193EA, including CMC/SBB carry. */
uint8_t btp_rng_next(uint8_t r[3])
{
    unsigned a = r[0], b = r[1], c = r[2];
    r[2] = (uint8_t)((c << 1) | ((a >> 1) & 1u));
    r[1] = (uint8_t)((b << 1) | (c >> 7));
    uint8_t difference = (uint8_t)((a >> 2) - a - (1u - (b >> 7)));
    r[0] = (uint8_t)((a >> 1) | ((unsigned)(difference & 1u) << 7));
    return (uint8_t)(r[0] ^ r[1]);
}

static int local_word(unsigned x, unsigned y, const BtpMap *m)
{
    return (x & ~127u) == (m->entrance_x[1] & ~127u) &&
        (y & ~127u) == (m->entrance_y[1] & ~127u) &&
        (x & 127u) < 2u*m->width && (y & 127u) < 2u*m->height;
}
static int map_valid(const BtpMap *m)
{
    for (unsigned i = 0; i < 8; ++i)
        if (m->npc_routes[i] > 7 || !local_word(m->entrance_x[i],m->entrance_y[i],m)) return 0;
    return 1;
}
void btp_npc_init(BtpState *s, const BtpMap *m)
{
    if (s->npc.enabled != 1) return;
    if (!map_valid(m)) { s->npc.fault = BTP_NPC_BAD_MAP; return; }
    for (unsigned i = 0; i < 8; ++i) if (s->npc_pairs[i][0] & 0x88u) {
        s->npc.fault = BTP_NPC_BAD_CONTEXT; return;
    }
    for (unsigned i = 0; i < 8; ++i) {
        unsigned origin = s->npc_pairs[i][0] >> 4;
        s->npc.actor[i] = (BtpNpc){m->entrance_x[origin],m->entrance_y[origin],0};
    }
    /* Recorded MAP1 baseline: slot 4 has completed one eastward step. Startup
       menus/initialization remain outside this slice, as in M1. */
    ++s->npc.actor[4].x; s->npc.actor[4].direction = 2;
    s->npc_walk[4] = 4;
    s->npc.enabled = 2;
}
int btp_npc_valid(const BtpState *s, const BtpMap *m)
{
    const BtpNpcState *n = &s->npc;
    if (n->enabled > 2 || n->phase > 2 || n->clock >= BTP_NPC_FRAME_TICKS ||
        (n->bias != 0 && n->bias != 8) || n->fault > BTP_NPC_BAD_CONTEXT || n->allowance_pending > 1) return 0;
    if (!n->enabled) {
        if (n->phase || n->clock || n->bias || n->search || n->fault || n->loop_timer || n->allowance_pending ||
            n->rng[0] || n->rng[1] || n->rng[2]) return 0;
    } else if (!n->search || n->search > 100 || s->conversation_checkpoint) return 0;
    for (unsigned i = 0; i < 8; ++i) {
        const BtpNpc *a = &n->actor[i];
        if (a->direction > 7 || (n->enabled && (s->npc_pairs[i][0] & 0x88u))) return 0;
        if (n->enabled != 2) {
            if (a->x || a->y || a->direction) return 0;
        } else if ((a->x == 0) != (a->y == 0) || (a->x && !local_word(a->x,a->y,m))) return 0;
        if (n->enabled == 2 && s->npc_pairs[i][1] && a->x) return 0;
    }
    return 1;
}
static int near_player(const BtpState *s, const BtpNpc *a)
{
    int px = s->x_half, py = s->y_half;
    int x = a->x & 127, y = a->y & 127;
    return a->x && x > (px & 112)-16 && x < (px | 15)+16 &&
        y > (py & 112)-16 && y < (py | 15)+16;
}
static unsigned heading(int dx, int dy)
{
    int ax = dx < 0 ? -dx : dx, ay = dy < 0 ? -dy : dy;
    if (2*ax < ay) return dy < 0 ? 0u : 4u;
    if (2*ay < ax) return dx < 0 ? 6u : 2u;
    return dy < 0 ? (dx < 0 ? 7u : 1u) : (dx < 0 ? 5u : 3u);
}
static int half_floor(int value) { return value / 2 - (value < 0 && value % 2 != 0); }
static int passable(const BtpState *s, const BtpMap *m, unsigned slot, int x, int y)
{
    if (x < 0 || y < 0 || x >= 2*m->width || y >= 2*m->height) return 0;
    int px = s->x_half, py = s->y_half;
    /* Reconstruct the original 24x24 working-grid address arithmetic. The
       parity corrections are preserved, including its asymmetric sampling. */
    int at = (((py & 15)/2)+2)*24 + ((px & 15)/2)+2;
    at += half_floor(y-py+12)*24 + half_floor(x-px+13);
    if (!((x-px) & 1) && (px & 1)) ++at;
    if (((y-py) & 1) && (py & 1)) at += 24;
    if (at < 0 || at >= 576) return 0;
    int tx = (px & 112)/2-8 + at%24, ty = (py & 112)/2-8 + at/24;
    if (btp_map_tile(m,tx,ty) >= s->gate) return 0;
    /* Original F9FE..FA88 compares human/NPC positions exactly. Its wider
       FB00..FB59 footprints belong to other unit slots, absent on this MAP1
       baseline. A cadet does not block the two adjacent half coordinates. */
    if (y == py && x == px) return 0;
    for (unsigned i = 0; i < 8; ++i) if (i != slot && s->npc.actor[i].x &&
        (s->npc.actor[i].x & 127) == x && (s->npc.actor[i].y & 127) == y) return 0;
    return 1;
}
static void walk(BtpState *s, const BtpMap *m, unsigned i)
{
    BtpNpc *a = &s->npc.actor[i];
    if (--s->npc.search == 0) { s->npc.search = 30; s->npc.bias ^= 8; }
    unsigned destination = s->npc_pairs[i][0] & 7u;
    int x = a->x & 127, y = a->y & 127;
    int gx = m->entrance_x[destination] & 127, gy = m->entrance_y[destination] & 127;
    if (x == gx && y == gy) return; /* Original direction helper returns -1. */
    unsigned desired = heading(gx-x,gy-y), direction = a->direction;
    if (desired != direction) direction = (direction + (((desired-direction)&7u) < 5 ? 1u : 7u)) & 7u;
    /* Candidates spiral around the gradual turn, alternating handedness after
       30 active path calls. No global pathfinding replaces the original rule. */
    for (unsigned trial = 0; trial < 8; ++trial) {
        int turn = trial ? (int)((trial+1)/2) * (trial & 1u ? 1 : -1) : 0;
        if (s->npc.bias) turn = -turn;
        unsigned d = (unsigned)((int)direction + turn + 8) & 7u;
        int dx = d == 0 || d == 4 ? 0 : d < 4 ? 1 : -1;
        int dy = d == 2 || d == 6 ? 0 : d == 0 || d == 1 || d == 7 ? -1 : 1;
        if (!passable(s,m,i,x+dx,y+dy)) continue;
        a->x = (uint16_t)((a->x & ~127u) | (unsigned)(x+dx));
        a->y = (uint16_t)((a->y & ~127u) | (unsigned)(y+dy));
        a->direction = (uint8_t)d;
        if (a->x == m->entrance_x[destination] && a->y == m->entrance_y[destination]) {
            s->npc_pairs[i][1] = btp_rng_next(s->npc.rng) & 31u;
            s->npc_pairs[i][0] = (uint8_t)((destination << 4) | m->npc_routes[destination]);
            a->x = a->y = 0;
        }
        return;
    }
}
void btp_npc_frame(BtpState *s, const BtpMap *m)
{
    btp_npc_init(s,m);
    if (!s->npc.enabled || s->npc.fault) return;
    if (!map_valid(m) || !btp_npc_valid(s,m)) {
        s->npc.fault = BTP_NPC_BAD_CONTEXT; return;
    }
    (void)btp_rng_next(s->npc.rng); /* Main-loop encounter check also draws on MAP1. */
    /* Primary image 2C7..2EE: saturating outdoor countdowns. Schools use
       byte 21; Katrina uses 22. Indoors this frame routine is suspended. */
    for (unsigned i = 20; i <= 22; ++i) if (s->story_flags[i]) --s->story_flags[i];
    if (s->npc.loop_timer-- == 0) btp_economy_wrap(s);
    s->npc.allowance_pending = (uint8_t)btp_economy_below_cap(s);
    if (++s->npc.phase < 3) return;
    s->npc.phase = 0;
    for (unsigned i = 0; i < 8; ++i) {
        uint8_t *pair = s->npc_pairs[i];
        if (pair[1]) {
            if (!i && s->recruitment) pair[1] = 255;
            if (--pair[1] == 0) {
                unsigned origin = pair[0] >> 4;
                s->npc.actor[i].x = m->entrance_x[origin];
                s->npc.actor[i].y = m->entrance_y[origin];
            }
        } else if (near_player(s,&s->npc.actor[i])) {
            unsigned before = s->npc.actor[i].direction;
            walk(s,m,i);
            s->npc_walk[i] = btp_walk_next(s->npc_walk[i],before,s->npc.actor[i].direction);
        }
    }
}
void btp_npc_tick(BtpState *s, const BtpMap *m)
{
    btp_npc_init(s,m);
    if (!s->npc.enabled || s->npc.fault) return;
    if (++s->npc.clock == BTP_NPC_FRAME_TICKS) {
        s->npc.clock = 0; btp_npc_frame(s,m);
    }
}
