#include "data/anm.h"
#include <stdio.h>
#include <string.h>

static int fail(BtpError *e, const char *message)
{
    if (e) snprintf(e->text,sizeof e->text,"ANM: %s",message);
    return 0;
}
/* Independently derived from original 187F:23EC. Frame boundaries, rather
   than a marker, terminate each XOR delta. Extended repeats use big endian. */
static int delta(const uint8_t *b, size_t n, size_t *at, uint8_t *frame)
{
    size_t out = 0;
    while (out < BTP_ANM_PACKED) {
        if (*at >= n) return 0;
        unsigned code = b[(*at)++];
        int repeat = !code || code >= 128;
        size_t count;
        if (!code) {
            if (n-*at < 2) return 0;
            count = (size_t)b[*at]*256u+b[*at+1]; *at += 2;
            if (!count) count = 65536; /* Original LOOP with initial CX=0. */
        } else count = repeat ? 256u-code : code;
        if (count > BTP_ANM_PACKED-out) count = BTP_ANM_PACKED-out;
        size_t needed = repeat ? 1u : count;
        if (needed > n-*at) return 0;
        for (size_t i = 0; i < count; ++i) frame[out+i] ^= b[*at+(repeat ? 0u : i)];
        out += count; *at += needed;
    }
    return 1;
}
int btp_anm_decode(const uint8_t *b, size_t n, BtpAnm *a, BtpError *e)
{
    if (!b || !a || n < 51 || n > BTP_ANM_BYTES) return fail(e,"invalid resource size");
    BtpAnm result = {0};
    for (unsigned i = 0; i < 32 && b[i]; ++i) {
        if (i == BTP_ANM_FRAMES || b[i] < 'A' || b[i] > 'R') return fail(e,"invalid sequence");
        ++result.count;
    }
    if (!result.count || b[result.count]) return fail(e,"missing sequence terminator");
    uint8_t packed[BTP_ANM_PACKED] = {0}; size_t at = 51;
    for (unsigned i = 0; i < result.count; ++i) {
        unsigned duration = b[32+b[i]-'A'], scale = b[50];
        if (duration > 127 || scale > 127 || !delta(b,n,&at,packed)) return fail(e,"invalid timing or truncated delta");
        result.end[i] = (uint16_t)at;
        result.units[i] = (uint16_t)(duration*scale*3u/4u);
    }
    result.length = (uint16_t)n; memcpy(result.bytes,b,n); *a = result;
    if (e) e->text[0] = 0;
    return 1;
}
int btp_anm_frame(const BtpAnm *a, unsigned index, uint8_t packed[BTP_ANM_PACKED])
{
    if (!a || !packed || !a->count || a->count > BTP_ANM_FRAMES || index >= a->count ||
        a->length < 51 || a->length > BTP_ANM_BYTES) return 0;
    memset(packed,0,BTP_ANM_PACKED); size_t at = 51;
    for (unsigned i = 0; i <= index; ++i)
        if (!delta(a->bytes,a->length,&at,packed) || at != a->end[i]) return 0;
    return 1;
}
