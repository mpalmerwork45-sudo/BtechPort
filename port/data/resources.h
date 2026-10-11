#ifndef BTP_RESOURCES_H
#define BTP_RESOURCES_H
#include <stddef.h>
#include <stdint.h>

enum { BTP_MAP_MAX = 64, BTP_PACKED_BYTES = 32000, BTP_PIXELS = 64000, BTP_BLD_MAX = 9000 };
typedef struct {
    uint8_t width, height;
    uint8_t tiles[BTP_MAP_MAX * BTP_MAP_MAX]; /* normalized row order */
    uint16_t entrance_x[8], entrance_y[8]; /* original packed words */
} BtpMap;
typedef struct {
    uint8_t format;
    uint8_t pixels[BTP_PIXELS]; /* format 1: 16x4000; format 2: 320x200 */
} BtpGraphic;
typedef struct {
    uint16_t length;
    uint8_t bytes[BTP_BLD_MAX]; /* decrypted payload; address zero excludes size word */
} BtpBld;
typedef struct { char text[256]; } BtpError;
typedef struct {
    BtpMap map;
    BtpGraphic tiles;
    BtpBld citadel;
} BtpResources;

int btp_map_decode(const uint8_t *bytes, size_t length, BtpMap *map, BtpError *error);
int btp_graphic_decode(const uint8_t *bytes, size_t length, BtpGraphic *graphic, BtpError *error);
int btp_bld_decode(const uint8_t *bytes, size_t length, BtpBld *script, BtpError *error);
uint8_t btp_map_tile(const BtpMap *map, int x, int y); /* 255 outside the map */
int btp_read_file(const char *path, uint8_t **bytes, size_t *length, BtpError *error);
int btp_resources_load(const char *directory, BtpResources *resources, BtpError *error);
#endif
