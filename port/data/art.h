#ifndef BTP_ART_H
#define BTP_ART_H
#include <stdint.h>
enum { BTP_ART_IMAGES=4096, BTP_ART_FRAMES=32, BTP_ART_PIXELS=1048576,
    BTP_ART_NONE=65535, BTP_ART_BINDINGS=6 };
typedef struct {
    char id[64],name[96];
    uint16_t width,height,count,kind;
    uint32_t frames[BTP_ART_FRAMES];
} BtpArtImage;
/* Package pixels use straight-alpha ARGB. A single total pixel budget bounds
   every frame together, including large screens and cloned animation frames. */
typedef struct {
    unsigned loaded,count,used;
    uint8_t source_digest[32];
    uint16_t bindings[BTP_ART_BINDINGS];
    BtpArtImage images[BTP_ART_IMAGES];
    uint32_t pixels[BTP_ART_PIXELS];
} BtpArt;
int btp_art_load(const char *path,BtpArt *out,char error[256]);
unsigned btp_art_find(const BtpArt *art,const char *id);
#endif
