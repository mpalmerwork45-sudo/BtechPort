#ifndef BTP_CHI_SPATIAL_H
#define BTP_CHI_SPATIAL_H
#include "data/resources.h"
#include "data/json.h"
#include "data/digest.h"
enum { BTP_CHI_TILES=4096, BTP_CHI_MAPS=15, BTP_CHI_PIECES=1024 };
typedef struct {
    char id[64],name[96],image[64];
    uint16_t graphic;uint8_t sheet,rule,water,mini_color; /* 2: native depth; 255: native mini colour. */
} BtpChiTile;
typedef struct {
    char id[64],name[64];
    uint16_t cells[4096],original_x,original_y;
    uint8_t width,height,source_width,source_height;
} BtpChiMap;
typedef struct {
    unsigned loaded,tile_count;
    BtpChiTile tiles[BTP_CHI_TILES];BtpChiMap maps[BTP_CHI_MAPS];
    uint16_t land[250];
    /* The sparse editing document is compiled once into an O(1) underlay.
       Zero means generated; nonzero stores tile index + 1. This object is
       heap allocated, and these content overrides never enter save state. */
    uint16_t world_cells[1024*1024];
    uint8_t start_x,start_y;
    uint8_t broker_configured,broker_enabled,broker_x,broker_y;
    char broker_name[17];
} BtpChiSpatial;
int btp_chi_spatial_load(const char *root,const char *file,BtpChiSpatial *spatial,
    BtpResources *resources,BtpDigest *digest,BtpError *error);
const BtpChiTile *btp_chi_map_cell(const BtpResources *r,unsigned map,int x,int y);
const BtpChiTile *btp_chi_generated_cell(const BtpResources *r,unsigned tile);
unsigned btp_chi_world_rule(const BtpResources *r,unsigned tile);
/* Zero means no override; otherwise a full generated-cell handle (256+ID). */
unsigned btp_chi_world_override(const BtpResources *r,int x,int y);
/* Translate native story destinations by the edited town's sector delta.
   Rooms retain their internal coordinate system; callers only use this for
   outdoor transfers. The source origins are immutable import metadata. */
void btp_chi_position(const BtpResources *r,unsigned *x,unsigned *y);
int btp_chi_map_offset(const BtpResources *r,unsigned map,unsigned axis);
#endif
