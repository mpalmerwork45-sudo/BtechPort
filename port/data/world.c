#include "data/resources.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned word(const uint8_t *b) { return b[0]+256u*b[1]; }
int btp_world_data_decode(const uint8_t *b,size_t n,BtpWorldData *w,BtpError *e)
{
    static const uint8_t tags[64]={
        0x15,0xa1,0x71,0x26,0x82,0xcf,0x1f,0xe5,0x0c,0xa9,0xe6,0xa6,0x8a,0x4b,0x31,0xd3,
        0xbe,0xf7,0x91,0x24,0x01,0x91,0x5e,0xdf,0x7b,0xb6,0x24,0x2b,0xe1,0x93,0x56,0x2a,
        0x67,0xaf,0x94,0x79,0xe4,0xd5,0x4c,0xa0,0xc9,0x3d,0x70,0x9b,0x76,0x82,0xf8,0x0d,
        0xde,0xa0,0x42,0x65,0xf0,0x1a,0xad,0xca,0x0c,0x1f,0x1d,0xb9,0x7f,0x15,0x54,0x2c
    };
    uint32_t seed=0;
    if (b && n>=16) for (unsigned i=0;i<4;++i) seed|=(uint32_t)b[12+i]<<(8*i);
    if (!b || !w || n!=80u+BTP_WORLD_SIDE*BTP_WORLD_SIDE || memcmp(b,"BTW1",4) ||
        word(b+4)!=BTP_WORLD_ORIGIN || word(b+6)!=BTP_WORLD_ORIGIN ||
        word(b+8)!=BTP_WORLD_SIDE || word(b+10)!=BTP_WORLD_SIDE ||
        !seed || seed>=UINT32_C(16777216) || memcmp(b+16,tags,64)) {
        if (e) snprintf(e->text,sizeof e->text,"Invalid Citadel surroundings cache");
        return 0;
    }
    for (unsigned i=80;i<n;++i) if (b[i]>=250) {
        if (e) snprintf(e->text,sizeof e->text,"Invalid generated terrain tile");
        return 0;
    }
    memcpy(w->tiles,b+80,sizeof w->tiles);w->seed=seed;w->loaded=1;return 1;
}
int btp_world_data_load(const char *path,BtpWorldData *w,BtpError *e)
{
    uint8_t *bytes;size_t length;
    if (!btp_read_file(path,&bytes,&length,e)) return 0;
    int ok=btp_world_data_decode(bytes,length,w,e);free(bytes);return ok;
}
