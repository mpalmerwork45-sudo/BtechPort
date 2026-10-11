#include "core/npc.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks;
#define CHECK(x) do { ++checks; if (!(x)) { fprintf(stderr,"FAIL %s:%d: %s\n",__FILE__,__LINE__,#x); exit(1); } } while (0)
enum { FIELDS = 65 };
static void synthetic(void)
{
    uint8_t rng[3] = {71,10,175};
    CHECK(btp_rng_next(rng) == 182 && !memcmp(rng,(uint8_t[]){163,21,95},3));
    CHECK(btp_rng_next(rng) == 123 && !memcmp(rng,(uint8_t[]){81,42,191},3));
    CHECK(btp_rng_next(rng) == 125 && !memcmp(rng,(uint8_t[]){40,85,126},3));
    BtpMap map = {.width=64,.height=64};
    for (unsigned i = 0; i < 8; ++i) {
        map.entrance_x[i] = (uint16_t)(0xc00+11+7*i);
        map.entrance_y[i] = (uint16_t)(0xc000+17+3*i);
        map.npc_routes[i] = (uint8_t)((i+1)%8);
    }
    BtpState s; btp_start(&s); btp_npc_init(&s,&map);
    CHECK(s.npc.enabled == 2 && btp_npc_valid(&s,&map));
    memset(s.npc.actor,0,sizeof s.npc.actor);
    /* Primary first rollover has three account draws; cap reached thereafter. */
    s.npc.phase = 0; s.npc.loop_timer = 0;
    memcpy(s.npc.rng,(uint8_t[]){179,241,193},3);
    btp_npc_frame(&s,&map);
    CHECK(s.npc.loop_timer == 255 && !s.npc.allowance_pending &&
        !memcmp(s.npc.rng,(uint8_t[]){251,28,25},3));
    s.npc.phase = 0; s.npc.loop_timer = 0;
    memcpy(s.npc.rng,(uint8_t[]){219,237,193},3);
    btp_npc_frame(&s,&map);
    CHECK(s.npc.loop_timer == 255 && !memcmp(s.npc.rng,(uint8_t[]){237,219,131},3));
    s.npc.actor[1] = (BtpNpc){0xc0f,0xc06d,0};
    BtpNpcState before = s.npc;
    for (unsigned i = 0; i < 3; ++i) btp_npc_frame(&s,&map);
    CHECK(s.npc.actor[1].x == before.actor[1].x && s.npc.actor[1].y == before.actor[1].y &&
        s.npc.search == before.search && memcmp(s.npc.rng,before.rng,3));
    /* Arrival, exact second draw, route change and hidden coordinates. */
    s.x_half = 18; s.y_half = 25; s.npc.phase = 2; s.npc.search = 100;
    memcpy(s.npc.rng,(uint8_t[]){71,10,175},3);
    s.npc_pairs[1][0] = 1;
    s.npc.actor[1] = (BtpNpc){map.entrance_x[1],(uint16_t)(map.entrance_y[1]+1),0};
    btp_npc_frame(&s,&map);
    CHECK(s.npc_pairs[1][0] == 0x12 && s.npc_pairs[1][1] == 27 &&
        !s.npc.actor[1].x && !s.npc.actor[1].y && !memcmp(s.npc.rng,(uint8_t[]){81,42,191},3));
    memcpy(s.npc.rng,(uint8_t[]){54,59,118},3); s.npc.phase = 2;
    s.npc_pairs[1][0] = 1; s.npc_pairs[1][1] = 0;
    s.npc.actor[1] = (BtpNpc){map.entrance_x[1],(uint16_t)(map.entrance_y[1]+1),0};
    btp_npc_frame(&s,&map);
    CHECK(s.npc_pairs[1][0] == 0x12 && !s.npc_pairs[1][1] && !s.npc.actor[1].x &&
        !memcmp(s.npc.rng,(uint8_t[]){13,237,219},3)); /* Original zero-delay arrival. */
    /* Offscreen timers expire independently; respawn is a separate update. */
    s.x_half = 100; s.y_half = 100; s.npc.phase = 2; s.npc_pairs[1][1] = 1;
    btp_npc_frame(&s,&map);
    CHECK(!s.npc_pairs[1][1] && s.npc.actor[1].x == map.entrance_x[1] &&
        s.npc.actor[1].y == map.entrance_y[1] && !s.npc.actor[1].direction);
    /* Recruitment's slot-0 timer guard, without claiming recruitment dialogue. */
    s.recruitment = 1; s.npc.phase = 2; s.npc_pairs[0][1] = 1;
    btp_npc_frame(&s,&map); CHECK(s.npc_pairs[0][1] == 254);
    s.recruitment = 0; s.npc_pairs[0][1] = 0;
    uint8_t encoded[BTP_STATE_BYTES], again[BTP_STATE_BYTES]; BtpState restored;
    btp_state_encode(&s,encoded);
    CHECK(btp_state_decode(encoded,sizeof encoded,&map,NULL,&restored));
    btp_state_encode(&restored,again); CHECK(!memcmp(encoded,again,sizeof again));
    const unsigned corrupt[] = {151,152,158,164,201,202};
    const uint8_t invalid[] = {3,4,1,8,2,1};
    for (unsigned i = 0; i < sizeof corrupt/sizeof corrupt[0]; ++i) {
        memcpy(again,encoded,sizeof again); again[corrupt[i]] = invalid[i];
        CHECK(!btp_state_decode(again,sizeof again,&map,NULL,&restored));
    }
    memcpy(again,encoded,sizeof again); again[160+5] ^= 128;
    CHECK(!btp_state_decode(again,sizeof again,&map,NULL,&restored));
    /* BTP4 preserves Talk pairs but cannot resume a travel clock it never stored. */
    uint8_t legacy[160]; memcpy(legacy,encoded,sizeof legacy); memset(legacy+150,0,10);
    memcpy(legacy,"BTP4",4); legacy[4] = 4;
    CHECK(btp_state_decode(legacy,sizeof legacy,&map,NULL,&restored));
    CHECK(!restored.npc.enabled && !memcmp(restored.npc_pairs,s.npc_pairs,16));
    BtpResources *r = calloc(1,sizeof *r); CHECK(r != NULL); r->map = map;
    s.mode = BTP_ENTRY; btp_state_encode(&s,encoded); btp_game_tick(&s,r,BTP_IDLE);
    btp_state_encode(&s,again); CHECK(!memcmp(encoded+150,again+150,52));
    free(r);
    puts("NPC synthetic: original RNG vectors, proximity freeze, arrival, expiry, clock persistence and legacy migration.");
}
static int row(FILE *f, unsigned v[FIELDS])
{
    char line[2048];
    do { if (!fgets(line,sizeof line,f)) return 0; } while (line[0] == '#');
    char *at = line;
    for (unsigned i = 0; i < FIELDS; ++i) {
        char *end; unsigned long value = strtoul(at,&end,10);
        if (end == at || value > 65535 || (i+1 < FIELDS ? *end != ',' : *end != '\n')) {
            fputs("Malformed numeric NPC fixture\n",stderr); exit(1);
        }
        v[i] = (unsigned)value; at = end+1;
    }
    return 1;
}
static void from_row(BtpState *s, const unsigned v[FIELDS], uint8_t allowance_pending)
{
    *s = (BtpState){.x_half=(uint16_t)(v[7]&127u),.y_half=(uint16_t)(v[8]&127u),.map_id=1,.gate=85,
        .credits=allowance_pending ? 35u : 50u,.allowance_cap=50};
    s->npc = (BtpNpcState){.enabled=2,.phase=(uint8_t)v[0],.loop_timer=(uint8_t)v[1],.allowance_pending=allowance_pending,
        .rng={(uint8_t)v[2],(uint8_t)v[3],(uint8_t)v[4]},.search=(uint16_t)v[5],.bias=(uint8_t)v[6]};
    for (unsigned i = 0; i < 8; ++i) {
        unsigned at = 9+7*i;
        s->npc.actor[i] = (BtpNpc){(uint16_t)v[at],(uint16_t)v[at+1],(uint8_t)v[at+4]};
        s->npc_pairs[i][0] = (uint8_t)v[at+5]; s->npc_pairs[i][1] = (uint8_t)v[at+6];
    }
}
static int matches(const BtpState *s, const BtpMap *m, const unsigned v[FIELDS], unsigned line)
{
    if (s->npc.phase != v[0] || s->npc.loop_timer != v[1] || memcmp(s->npc.rng,(uint8_t[]){(uint8_t)v[2],(uint8_t)v[3],(uint8_t)v[4]},3) ||
        s->npc.search != v[5] || s->npc.bias != v[6] || s->npc.fault) {
        fprintf(stderr,"Frame %u clock/RNG/search: phase %u/%u rng %u,%u,%u/%u,%u,%u search %u,%u/%u,%u fault %u\n",
            line,s->npc.phase,v[0],s->npc.rng[0],s->npc.rng[1],s->npc.rng[2],v[2],v[3],v[4],s->npc.search,s->npc.bias,v[5],v[6],s->npc.fault);
        return 0;
    }
    for (unsigned i = 0; i < 8; ++i) {
        unsigned at = 9+7*i, destination = s->npc_pairs[i][0]&7u;
        const BtpNpc *n = &s->npc.actor[i];
        if (n->x != v[at] || n->y != v[at+1] || n->direction != v[at+4] ||
            s->npc_pairs[i][0] != v[at+5] || s->npc_pairs[i][1] != v[at+6] ||
            m->entrance_x[destination] != v[at+2] || m->entrance_y[destination] != v[at+3]) {
            fprintf(stderr,"Frame %u NPC %u: pos %04x,%04x/%04x,%04x dir %u/%u pair %u,%u/%u,%u\n",
                line,i,n->x,n->y,v[at],v[at+1],n->direction,v[at+4],s->npc_pairs[i][0],s->npc_pairs[i][1],v[at+5],v[at+6]);
            return 0;
        }
    }
    return 1;
}
static void trace(const char *dir, const char *path)
{
    BtpResources *r = malloc(sizeof *r); BtpError e;
    CHECK(r && btp_resources_load(dir,r,&e));
    FILE *f = fopen(path,"r"); CHECK(f != NULL);
    unsigned old[FIELDS], next[FIELDS]; CHECK(row(f,old));
    BtpState s; from_row(&s,old,1); CHECK(btp_npc_valid(&s,&r->map));
    unsigned frames = 0, cursor_only = 0, skipped = 0, arrivals = 0, sample = 1;
    while (row(f,next)) {
        ++sample;
        unsigned delta = (old[1]-next[1])&255u;
        if (delta > 1 && (old[7] != next[7] || old[8] != next[8])) {
            /* Never infer an unknown intermediate player position. */
            uint8_t pending = delta > old[1] ? 0 : s.npc.allowance_pending;
            ++skipped; from_row(&s,next,pending);
        } else {
            s.x_half = (uint16_t)(next[7]&127u); s.y_half = (uint16_t)(next[8]&127u);
            if (delta) {
                uint8_t pairs[8][2]; memcpy(pairs,s.npc_pairs,sizeof pairs);
                for (unsigned j = 0; j < delta; ++j) {
                    uint8_t encoded[BTP_STATE_BYTES], again[BTP_STATE_BYTES]; BtpState restored;
                    btp_state_encode(&s,encoded);
                    CHECK(btp_state_decode(encoded,sizeof encoded,&r->map,NULL,&restored));
                    btp_npc_frame(&s,&r->map); btp_npc_frame(&restored,&r->map); ++frames;
                    btp_state_encode(&s,encoded); btp_state_encode(&restored,again);
                    CHECK(!memcmp(encoded,again,sizeof again));
                }
                for (unsigned i = 0; i < 8; ++i) if (pairs[i][0] != s.npc_pairs[i][0]) ++arrivals;
            } else ++cursor_only;
            if (!matches(&s,&r->map,next,sample)) {
                fprintf(stderr,"Previous player %u,%u; next %u,%u; delta %u\n",old[7],old[8],next[7],next[8],delta);
                exit(1);
            }
            ++checks;
            s.x_half = (uint16_t)(next[7]&127u); s.y_half = (uint16_t)(next[8]&127u);
        }
        memcpy(old,next,sizeof old);
    }
    CHECK(!ferror(f)); CHECK(fclose(f) == 0);
    printf("NPC oracle: %u complete frame steps, %u cursor-only observations, %u skipped gaps, %u arrivals.\n",
        frames,cursor_only,skipped,arrivals);
    CHECK(frames >= 450 && arrivals >= 1);
    free(r);
}
int main(int argc, char **argv)
{
    synthetic();
    if (argc == 3) trace(argv[1],argv[2]);
    printf("PASS %u NPC checks\n",checks);
    return 0;
}
