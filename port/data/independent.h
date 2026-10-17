#ifndef BTP_INDEPENDENT_H
#define BTP_INDEPENDENT_H
#include "data/resources.h"
/* Package-owned pixels and tones. None are decoded from original resources.
   Index zero is transparent for sprites, but opaque for map tiles. */
typedef struct {
    unsigned loaded,tile_count;
    uint8_t source_digest[32],font[96][7],tiles[64][256];
    uint8_t sprites[5][4][256],portraits[2][4096];
    uint32_t palette[16];
    uint8_t locations[11];
    uint16_t sound_hz[18][8],sound_ms[18][8];uint8_t sound_count[18];
    int8_t people_x[8],people_y[8],mechs_x[4],mechs_y[4];
    char personal_label[12];unsigned personal_damage,personal_range;
} BtpIndependent;
int btp_independent_load(const char *path,BtpIndependent *out,char error[256]);
void btp_independent_resources(BtpResources *resources);
#endif
