#ifndef BTP_RESOURCES_H
#define BTP_RESOURCES_H
#include <stddef.h>
#include <stdint.h>
#include "core/combat_rules.h"

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
enum { BTP_WORLD_SIDE=192, BTP_WORLD_ORIGIN=704, BTP_CITADEL_ORIGIN=768 };
typedef struct {
    uint32_t seed;
    uint8_t loaded, native, tiles[BTP_WORLD_SIDE*BTP_WORLD_SIDE];
    uint8_t coarse[336], textures[1024], special[64], flips[96];
    uint8_t noise[256], heights[144*144];
} BtpWorldData;
typedef struct {
    BtpMap map;
    BtpMap destroyed;
    BtpGraphic tiles, terrain_animation, sprites, quiz_diagram, border;
    BtpBld citadel, armor, weapon, comstar, training, barracks, lounge, repair;
    BtpDialogue dialogue;
    BtpAnm animations[BTP_ANM_COUNT];
    BtpCombatData combat;
    BtpWorldData world;
} BtpResources;

int btp_map_decode(const uint8_t *bytes, size_t length, BtpMap *map, BtpError *error);
int btp_graphic_decode(const uint8_t *bytes, size_t length, BtpGraphic *graphic, BtpError *error);
int btp_bld_decode(const uint8_t *bytes, size_t length, BtpBld *script, BtpError *error);
uint8_t btp_map_tile(const BtpMap *map, int x, int y); /* 255 outside the map */
int btp_read_file(const char *path, uint8_t **bytes, size_t *length, BtpError *error);
int btp_resources_load(const char *directory, BtpResources *resources, BtpError *error);
int btp_dialogue_decode(const uint8_t *bytes, size_t length, BtpDialogue *dialogue, BtpError *error);
int btp_dialogue_load(const char *path, BtpDialogue *dialogue, BtpError *error);
int btp_combat_data_load(const char *path, BtpCombatData *data, BtpError *error);
int btp_world_data_load(const char *path, BtpWorldData *data, BtpError *error);
int btp_world_data_decode(const uint8_t *bytes,size_t length,BtpWorldData *data,BtpError *error);
int btp_world_generate(BtpWorldData *data,uint32_t seed);
unsigned btp_generated_tile(const BtpWorldData *data,int x,int y);
#endif
