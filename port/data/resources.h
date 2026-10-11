#ifndef BTP_RESOURCES_H
#define BTP_RESOURCES_H
#include <stddef.h>
#include <stdint.h>

enum { BTP_MAP_MAX = 64, BTP_PACKED_BYTES = 32000, BTP_PIXELS = 64000, BTP_BLD_MAX = 9000 };
typedef struct {
    uint8_t width, height;
    uint8_t tiles[BTP_MAP_MAX * BTP_MAP_MAX]; /* normalized row order */
    uint16_t entrance_x[8], entrance_y[8]; /* original packed words */
    uint8_t npc_names[8][16], places[8][16], room_map[8], npc_routes[8];
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
enum { BTP_ANM_COUNT = 22, BTP_ANM_BYTES = 16128, BTP_ANM_FRAMES = 31, BTP_ANM_PACKED = 3872 };
typedef struct {
    uint16_t length, end[BTP_ANM_FRAMES], units[BTP_ANM_FRAMES];
    uint8_t count, bytes[BTP_ANM_BYTES];
} BtpAnm;
/* 43 earlier bank/Talk strings plus 12 class transcript/rank/subject strings. */
enum { BTP_TALK_STRINGS = 87, BTP_TALK_MAX = 4096 };
typedef struct {
    uint8_t bytes[BTP_TALK_MAX];
    uint8_t font[2048];
    uint16_t length, offset[BTP_TALK_STRINGS], size[BTP_TALK_STRINGS];
} BtpDialogue;
typedef struct {
    BtpMap map;
    BtpGraphic tiles, sprites, quiz_diagram, border;
    BtpBld citadel, armor, weapon, comstar, training, barracks, lounge;
    BtpDialogue dialogue;
    BtpAnm animations[BTP_ANM_COUNT];
} BtpResources;

int btp_map_decode(const uint8_t *bytes, size_t length, BtpMap *map, BtpError *error);
int btp_graphic_decode(const uint8_t *bytes, size_t length, BtpGraphic *graphic, BtpError *error);
int btp_bld_decode(const uint8_t *bytes, size_t length, BtpBld *script, BtpError *error);
uint8_t btp_map_tile(const BtpMap *map, int x, int y); /* 255 outside the map */
int btp_read_file(const char *path, uint8_t **bytes, size_t *length, BtpError *error);
int btp_resources_load(const char *directory, BtpResources *resources, BtpError *error);
int btp_dialogue_decode(const uint8_t *bytes, size_t length, BtpDialogue *dialogue, BtpError *error);
int btp_dialogue_load(const char *path, BtpDialogue *dialogue, BtpError *error);
#endif
