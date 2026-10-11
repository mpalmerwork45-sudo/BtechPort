#include "data/resources.h"
#include "data/anm.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int fail(BtpError *e, const char *message)
{
    if (e) snprintf(e->text, sizeof e->text, "%s", message);
    return 0;
}
static uint16_t le16(const uint8_t *p) { return (uint16_t)(p[0] | (uint16_t)p[1] << 8); }

int btp_map_decode(const uint8_t *b, size_t n, BtpMap *m, BtpError *e)
{
    if (!b || !m || n < 541) return fail(e, "MTP: truncated 541-byte header (raw MAP15 is unsupported)");
    unsigned w = b[3], h = b[4];
    if (b[0] || b[1] || b[2] || !w || !h || w > 64 || h > 64 || w % 8 || h % 8)
        return fail(e, "MTP: unsupported dimensions/header");
    if (n != 541 + (size_t)w * h) return fail(e, "MTP: payload length does not match dimensions");
    BtpMap result = {0};
    result.width = (uint8_t)w; result.height = (uint8_t)h;
    for (unsigned y = 0; y < h; ++y)
        for (unsigned x = 0; x < w; ++x) {
            size_t offset = ((y / 8) * (w / 8) + x / 8) * 64 + (y % 8) * 8 + x % 8;
            result.tiles[y * w + x] = b[541 + offset];
        }
    for (unsigned i = 0; i < 8; ++i) {
        result.entrance_x[i] = le16(b + 389 + 2 * i);
        result.entrance_y[i] = le16(b + 421 + 2 * i);
        memcpy(result.npc_names[i], b + 5 + 16*i, 16);
        memcpy(result.places[i], b + 133 + 16*i, 16);
        result.room_map[i] = b[517+i];
        result.npc_routes[i] = b[533+i];
    }
    *m = result;
    return 1;
}

int btp_graphic_decode(const uint8_t *b, size_t n, BtpGraphic *g, BtpError *e)
{
    if (!b || !g || n < 3 || n > 65537 || le16(b) != n - 2)
        return fail(e, "ICN/CMP: invalid size word or truncated header");
    if (b[2] != 1 && b[2] != 2) return fail(e, "ICN/CMP: unsupported format");
    uint8_t packed[BTP_PACKED_BYTES];
    size_t in = 3, out = 0;
    while (in < n) {
        unsigned code = b[in++];
        size_t count;
        if (code > 0 && code < 128) {
            count = code;
            if (count > n - in || count > sizeof packed - out)
                return fail(e, "ICN/CMP: truncated or overflowing literal run");
            memcpy(packed + out, b + in, count);
            in += count;
        } else {
            if (code == 0) {
                if (n - in < 3) return fail(e, "ICN/CMP: truncated long repeat");
                count = le16(b + in); in += 2;
                if (!count) return fail(e, "ICN/CMP: zero-length repeat");
            } else count = 256 - code;
            if (in == n || count > sizeof packed - out)
                return fail(e, "ICN/CMP: truncated or overflowing repeat");
            memset(packed + out, b[in++], count);
        }
        out += count;
    }
    if (out != sizeof packed) return fail(e, "ICN/CMP: expected exactly 32000 packed bytes");
    g->format = b[2];
    for (size_t i = 0; i < sizeof packed; ++i) {
        size_t index = g->format == 1 ? 2 * i : (i % 200) * 320 + (i / 200) * 2;
        g->pixels[index] = packed[i] >> 4;
        g->pixels[index + 1] = packed[i] & 15;
    }
    return 1;
}

uint8_t btp_map_tile(const BtpMap *m, int x, int y)
{
    if (!m || x < 0 || y < 0 || x >= m->width || y >= m->height) return 255;
    return m->tiles[(size_t)y * m->width + (size_t)x];
}

int btp_bld_decode(const uint8_t *b, size_t n, BtpBld *script, BtpError *e)
{
    if (!b || !script || n < 3 || n > BTP_BLD_MAX + 2 || le16(b) != n - 2)
        return fail(e, "BLD: invalid size word or payload length");
    script->length = (uint16_t)(n - 2);
    for (size_t i = 2; i < n; ++i)
        script->bytes[i - 2] = (uint8_t)((uint8_t)(b[i] + 41u) ^ 233u);
    return 1;
}

int btp_read_file(const char *path, uint8_t **bytes, size_t *length, BtpError *e)
{
    FILE *f = fopen(path, "rb");
    if (!f) {
        if (e) snprintf(e->text, sizeof e->text, "Cannot read %.190s", path);
        return 0;
    }
    if (fseek(f, 0, SEEK_END)) { fclose(f); return fail(e, "Cannot seek resource"); }
    long size = ftell(f);
    if (size <= 0 || size > 1024 * 1024 || fseek(f, 0, SEEK_SET)) {
        fclose(f); return fail(e, "Resource must be 1 byte .. 1 MiB");
    }
    uint8_t *data = malloc((size_t)size);
    if (!data) { fclose(f); return fail(e, "Resource allocation failed"); }
    size_t got = fread(data, 1, (size_t)size, f);
    int bad = ferror(f);
    int close_bad = fclose(f);
    if (got != (size_t)size || bad || close_bad) { free(data); return fail(e, "Resource read failed"); }
    *bytes = data; *length = got;
    return 1;
}

int btp_resources_load(const char *dir, BtpResources *r, BtpError *e)
{
    memset(&r->dialogue, 0, sizeof r->dialogue);
    memset(&r->combat,0,sizeof r->combat);
    char path[4096]; uint8_t *data; size_t n;
    const char *names[] = {"MAP1.MTP", "BTTLTECH.ICN", "CITADEL.BLD", "ARMOR.BLD", "WEAPON.BLD", "COMSTAR.BLD", "MECHSHAP.CMP", "TRAINING.BLD", "BARRACKS.BLD", "LOUNGE.BLD", "BTSTATS.CMP", "BTBORDER.CMP", "REPAIR.BLD", "ANIMATE.ICN"};
    for (unsigned i = 0; i < 14; ++i) {
        int len = snprintf(path, sizeof path, "%s/%s", dir, names[i]);
        if (len < 0 || (size_t)len >= sizeof path) return fail(e, "Resource directory path too long");
        if (!btp_read_file(path, &data, &n, e)) return 0;
        int ok = i == 0 ? btp_map_decode(data, n, &r->map, e) :
            i == 1 ? btp_graphic_decode(data, n, &r->tiles, e) :
            i == 6 ? btp_graphic_decode(data, n, &r->sprites, e) :
            i == 10 ? btp_graphic_decode(data,n,&r->quiz_diagram,e) :
            i == 11 ? btp_graphic_decode(data,n,&r->border,e) :
            i == 13 ? btp_graphic_decode(data,n,&r->terrain_animation,e) :
            btp_bld_decode(data, n, i == 2 ? &r->citadel : i == 3 ? &r->armor : i == 4 ? &r->weapon :
                i == 5 ? &r->comstar : i == 7 ? &r->training : i == 8 ? &r->barracks : i == 9 ? &r->lounge : &r->repair, e);
        free(data);
        if (!ok) return 0;
    }
    for (unsigned i = 0; i < BTP_ANM_COUNT; ++i) {
        int len = snprintf(path,sizeof path,"%s/O%u.ANM",dir,i);
        if (len < 0 || (size_t)len >= sizeof path) return fail(e,"Resource directory path too long");
        if (!btp_read_file(path,&data,&n,e)) return 0;
        int ok = btp_anm_decode(data,n,&r->animations[i],e); free(data);
        if (!ok) return 0;
    }
    if (r->sprites.format != 2) return fail(e,"MECHSHAP requires format-2 320x200 graphics");
    if (r->quiz_diagram.format != 2) return fail(e,"BTSTATS requires format-2 320x200 graphics");
    if (r->border.format != 1) return fail(e,"BTBORDER requires format-1 320x200 graphics");
    if (r->terrain_animation.format != 1) return fail(e,"ANIMATE requires format-1 tile graphics");
    if (r->map.width != 64 || r->map.height != 64 || r->tiles.format != 1)
        return fail(e, "M2a requires the authentic 64x64 MAP1 and format-1 BTTLTECH tiles");
    if (r->map.entrance_x[1] != 0x0c45 || r->map.entrance_y[1] != 0xc014)
        return fail(e, "M2a requires the verified MAP1 Citadel entrance words");
    if (r->map.entrance_x[3] != 0x0c20 || r->map.entrance_y[3] != 0xc02c ||
        r->map.entrance_x[4] != 0x0c32 || r->map.entrance_y[4] != 0xc07c ||
        r->map.room_map[3] != 3 || r->map.room_map[4] != 4)
        return fail(e, "M2e requires the verified MAP1 shop entrances and room mapping");
    if (r->map.entrance_x[2] != 0x0c66 || r->map.entrance_y[2] != 0xc014 || r->map.room_map[2] != 2)
        return fail(e,"M2f requires the verified MAP1 ComStar entrance and room mapping");
    if (r->map.entrance_x[0] != 0x0c2e || r->map.entrance_y[0] != 0xc072 ||
        r->map.entrance_x[6] != 0x0c11 || r->map.entrance_y[6] != 0xc00d ||
        r->map.entrance_x[7] != 0x0c11 || r->map.entrance_y[7] != 0xc059 ||
        r->map.room_map[0] != 0 || r->map.room_map[6] != 6 || r->map.room_map[7] != 7)
        return fail(e,"M2j requires the verified MAP1 training, barracks and lounge entries");
    for (unsigned i = 0; i < 4096; ++i)
        if (r->map.tiles[i] >= 250) return fail(e, "MAP1 references a tile outside the 250-tile sheet");
    return 1;
}

int btp_dialogue_decode(const uint8_t *b, size_t n, BtpDialogue *d, BtpError *e)
{
    /* BTT6: source tags, 87 text ranges and original 256x8 font bytes.
       Conversion validates the audited EXE. Tags identify that source, not a
       cryptographic integrity check of the generated cache. */
    static const uint8_t tags[64] = {
        0x15,0xa1,0x71,0x26,0x82,0xcf,0x1f,0xe5,0x0c,0xa9,0xe6,0xa6,0x8a,0x4b,0x31,0xd3,
        0xbe,0xf7,0x91,0x24,0x01,0x91,0x5e,0xdf,0x7b,0xb6,0x24,0x2b,0xe1,0x93,0x56,0x2a,
        0x10,0x0f,0x0d,0xf2,0x44,0xe4,0xb0,0xc8,0x69,0x3d,0x1b,0x50,0x13,0xfb,0x07,0x3f,
        0x48,0x6b,0x35,0xd6,0xf5,0xc5,0x38,0xec,0xd5,0x3d,0x03,0xf8,0x5e,0xd5,0x4b,0xfa
    };
    const unsigned header = 72+4*BTP_TALK_STRINGS;
    if (!b || !d || n < header || memcmp(b,"BTT6",4) || le16(b+6) != BTP_TALK_STRINGS ||
        memcmp(b+8,tags,sizeof tags) || !le16(b+4) || le16(b+4) > BTP_TALK_MAX ||
        n != header+le16(b+4)+2048u) return fail(e,"Native dialogue: invalid cache/provenance header");
    BtpDialogue result = {0}; result.length = le16(b+4);
    memcpy(result.bytes,b+header,result.length);
    memcpy(result.font,b+header+result.length,sizeof result.font);
    unsigned next = 0;
    for (unsigned i = 0; i < BTP_TALK_STRINGS; ++i) {
        unsigned at = le16(b+72+4*i), length = le16(b+74+4*i);
        if (at != next || at >= result.length || length >= result.length-at ||
            result.bytes[at+length]) return fail(e,"Native dialogue: invalid string range");
        for (unsigned j = 0; j < length; ++j) {
            unsigned c = result.bytes[at+j];
            if (c != 13 && !(i >= 17 && (c == 6 || c == 15)) && (c < 32 || c >= 127))
                return fail(e,"Native dialogue: invalid character");
        }
        result.offset[i] = (uint16_t)at; result.size[i] = (uint16_t)length;
        next = at+length+1;
    }
    if (next != result.length) return fail(e,"Native dialogue: trailing data");
    *d = result; return 1;
}
int btp_dialogue_load(const char *path, BtpDialogue *d, BtpError *e)
{
    uint8_t *bytes; size_t length;
    if (!btp_read_file(path,&bytes,&length,e)) return 0;
    int ok = btp_dialogue_decode(bytes,length,d,e); free(bytes); return ok;
}
int btp_combat_data_load(const char *path, BtpCombatData *d, BtpError *e)
{
    uint8_t *b;size_t n;
    if (!btp_read_file(path,&b,&n,e)) return 0;
    int ok=btp_combat_data_decode(b,n,d);free(b);
    return ok ? 1 : fail(e,"Combat: invalid original data cache");
}
