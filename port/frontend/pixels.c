#include "frontend/pixels.h"
#include <stdio.h>
#include <string.h>

const uint32_t btp_palette[16] = {
    0xff000000,0xff0000aa,0xff00aa00,0xff00aaaa,0xffaa0000,0xffaa00aa,0xffaa5500,0xffaaaaaa,
    0xff555555,0xff5555ff,0xff55ff55,0xff55ffff,0xffff5555,0xffff55ff,0xffffff55,0xffffffff
};
/* VERIFIED for MAP1 terrain in the captured VGA reference frames. Resource
   indices stay unchanged; this is a display palette mapping, not decoding. */
static const uint8_t terrain_palette[16] = {0,1,2,3,4,9,6,7,8,1,10,11,12,13,14,15};

/* Small independently drawn 5x7 diagnostic font; no BIOS/reference font copied. */
static const char alphabet[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789:./- ";
static const uint8_t glyphs[][7] = {
 {14,17,17,31,17,17,17},{30,17,17,30,17,17,30},{14,17,16,16,16,17,14},
 {30,17,17,17,17,17,30},{31,16,16,30,16,16,31},{31,16,16,30,16,16,16},
 {14,17,16,23,17,17,15},{17,17,17,31,17,17,17},{14,4,4,4,4,4,14},
 {7,2,2,2,2,18,12},{17,18,20,24,20,18,17},{16,16,16,16,16,16,31},
 {17,27,21,21,17,17,17},{17,25,21,19,17,17,17},{14,17,17,17,17,17,14},
 {30,17,17,30,16,16,16},{14,17,17,17,21,18,13},{30,17,17,30,20,18,17},
 {15,16,16,14,1,1,30},{31,4,4,4,4,4,4},{17,17,17,17,17,17,14},
 {17,17,17,17,17,10,4},{17,17,17,21,21,21,10},{17,17,10,4,10,17,17},
 {17,17,10,4,4,4,4},{31,1,2,4,8,16,31},{14,17,19,21,25,17,14},
 {4,12,4,4,4,4,14},{14,17,1,2,4,8,31},{30,1,1,14,1,1,30},
 {2,6,10,18,31,2,2},{31,16,16,30,1,1,30},{14,16,16,30,17,17,14},
 {31,1,2,4,8,8,8},{14,17,17,14,17,17,14},{14,17,17,15,1,1,14},
 {0,4,4,0,4,4,0},{0,0,0,0,0,4,4},{1,2,2,4,8,8,16},
 {0,0,0,31,0,0,0},{0,0,0,0,0,0,0}
};
static void pixel(uint32_t *f, int x, int y, uint32_t color)
{
    if (x >= 0 && x < 320 && y >= 0 && y < 200) f[y * 320 + x] = color;
}
static void text(uint32_t *f, int x, int y, const char *str, unsigned color)
{
    for (; *str; ++str, x += 6) {
        const char *p = strchr(alphabet, *str);
        if (!p) continue;
        size_t i = (size_t)(p - alphabet);
        for (int row = 0; row < 7; ++row)
            for (int col = 0; col < 5; ++col)
                if ((glyphs[i][row] >> (4 - col)) & 1) pixel(f, x + col, y + row, btp_palette[color]);
    }
}

void btp_render(const BtpResources *r, const BtpState *s, int debug, uint32_t f[BTP_PIXELS])
{
    int camera_x = (int)s->x_half * 8 - 96, camera_y = (int)s->y_half * 8 - 96;
    for (int y = 0; y < 200; ++y)
        for (int x = 0; x < 320; ++x) {
            uint32_t color = btp_palette[0];
            if (x >= 104) {
                int wx = camera_x + x - 104, wy = camera_y + y;
                if (wx >= 0 && wy >= 0 && wx < r->map.width * 16 && wy < r->map.height * 16) {
                    unsigned tile = btp_map_tile(&r->map, wx / 16, wy / 16);
                    if (tile < 250) {
                        unsigned index = tile * 256 + (unsigned)(wy % 16) * 16 + (unsigned)(wx % 16);
                        unsigned value = r->tiles.pixels[index] & 15;
                        color = btp_palette[terrain_palette[value]];
                        if (debug && tile >= s->gate && (wx % 16 == 0 || wy % 16 == 0))
                            color = btp_palette[13];
                    }
                }
            } else if (x < 3 || x >= 100 || y < 3 || y >= 197 || y == 100 || y == 101)
                color = btp_palette[7];
            f[y * 320 + x] = color;
        }
    /* Approximate marker until ANIMATE.ICN sprite selection/masking is verified. */
    for (int y = 97; y <= 102; ++y)
        for (int x = 211; x <= 213; ++x) pixel(f, x, y, btp_palette[y < 99 ? 15 : 1]);
    text(f, 8, 9, "BTECHPORT M1", 15);
    text(f, 8, 24, "TRAINING", 14);
    text(f, 8, 36, "SCHOOL", 14);
    text(f, 8, 57, "ARROWS MOVE", 7);
    text(f, 8, 69, "F3 DEBUG", 7);
    text(f, 8, 81, "R RESTART", 7);
    text(f, 8, 111, "MAP 1", 15);
    char line[64];
    snprintf(line, sizeof line, "X %u.%u", s->x_half / 2, (s->x_half % 2) * 5);
    text(f, 8, 125, line, 15);
    snprintf(line, sizeof line, "Y %u.%u", s->y_half / 2, (s->y_half % 2) * 5);
    text(f, 8, 137, line, 15);
    if (s->blocked) text(f, 8, 151, s->blocked == BTP_EDGE ? "MAP EDGE" : "BLOCKED", 12);
    if (btp_entrance(s, &r->map) >= 0) {
        text(f, 8, 166, "INTERIOR", 14); text(f, 8, 178, "UNAVAILABLE", 14);
    } else if (debug) {
        snprintf(line, sizeof line, "GATE %u", s->gate); text(f, 8, 166, line, 14);
        snprintf(line, sizeof line, "TICK %u", s->tick); text(f, 8, 178, line, 14);
    }
}

int btp_write_ppm(const char *path, const uint32_t f[BTP_PIXELS])
{
    FILE *out = fopen(path, "wb");
    if (!out) return 0;
    int ok = fprintf(out, "P6\n320 200\n255\n") > 0;
    for (unsigned i = 0; i < BTP_PIXELS && ok; ++i) {
        uint8_t rgb[] = {(uint8_t)(f[i] >> 16), (uint8_t)(f[i] >> 8), (uint8_t)f[i]};
        ok = fwrite(rgb, 1, 3, out) == 3;
    }
    if (fclose(out)) ok = 0;
    return ok;
}
