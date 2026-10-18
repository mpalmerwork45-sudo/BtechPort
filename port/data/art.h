#ifndef BTP_ART_H
#define BTP_ART_H
#include <stdint.h>
enum { BTP_ART_IMAGES=4096, BTP_ART_FRAMES=256, BTP_ART_PIXELS=1048576,
    BTP_ART_NONE=65535, BTP_ART_BINDINGS=6, BTP_ART_TRACKS=512 };
enum { BTP_ANIM_IDLE, BTP_ANIM_WALK, BTP_ANIM_FIRE, BTP_ANIM_JUMP,
    BTP_ANIM_DAMAGE, BTP_ANIM_DESTRUCTION, BTP_ANIM_ACTIONS };
typedef struct {
    uint8_t directions,count[8],ticks[8][32],sound;
    uint16_t frames[8][32];
} BtpArtTrack;
typedef struct {
    char id[64],name[96];
    uint16_t width,height,count,kind,frame_ticks; /* Tile loop: 32 ms ticks, default 8. */
    uint32_t frames[BTP_ART_FRAMES];
    uint16_t tracks[BTP_ANIM_ACTIONS]; /* One based; zero preserves old layouts. */
} BtpArtImage;
/* Package pixels use straight-alpha ARGB. A single total pixel budget bounds
   every frame together, including large screens and cloned animation frames. */
typedef struct {
    unsigned loaded,count,used,track_count;
    uint8_t source_digest[32];
    uint16_t bindings[BTP_ART_BINDINGS];
    BtpArtImage images[BTP_ART_IMAGES];
    BtpArtTrack tracks[BTP_ART_TRACKS];
    uint32_t pixels[BTP_ART_PIXELS];
} BtpArt;
int btp_art_load(const char *path,BtpArt *out,char error[256]);
unsigned btp_art_find(const BtpArt *art,const char *id);
const BtpArtTrack *btp_art_track(const BtpArt *art,unsigned image,unsigned action);
unsigned btp_art_frame(const BtpArt *art,unsigned image,unsigned action,unsigned direction,unsigned ticks,unsigned fallback);
unsigned btp_art_tile_frame(const BtpArt *art,unsigned image,unsigned ticks);
#endif
