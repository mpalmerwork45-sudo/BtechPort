#ifndef BTP_RESOURCES_H
#define BTP_RESOURCES_H
#include <stddef.h>
#include <stdint.h>
#include "core/combat_rules.h"
#include "data/roster.h"
#include "data/combat_profile.h"

/* Stored MTPs remain at most 64x64. The transient invasion battle includes
   surrounding generated terrain so a waypoint can cross every town edge. */
enum { BTP_MAP_MAX = 128, BTP_PACKED_BYTES = 32000, BTP_PIXELS = 64000, BTP_BLD_MAX = 9000 };
typedef struct {
    uint8_t width, height;
    uint8_t authored; /* Rule maps use complete actor footprints at edges. */
    uint8_t tiles[BTP_MAP_MAX * BTP_MAP_MAX]; /* normalized row order */
    uint16_t entrance_x[16], entrance_y[16]; /* original packed words */
    uint8_t npc_names[8][16], places[16][16], room_map[16], npc_routes[8];
} BtpMap;
typedef struct {
    uint8_t format;
    uint8_t pixels[BTP_PIXELS]; /* format 1: 16x4000; format 2: 320x200 */
} BtpGraphic;
typedef struct {
    uint16_t length;
    uint8_t bytes[BTP_BLD_MAX]; /* decrypted payload; address zero excludes size word */
    const uint16_t *origin_map; /* Optional project-owned original -> compiled offsets. */
    const uint16_t *origin_ends; /* Distinguish resumes before an inserted instruction. */
    uint16_t origin_length;
} BtpBld;
typedef struct { char text[256]; } BtpError;
enum { BTP_ANM_COUNT = 22, BTP_ANM_BYTES = 16128, BTP_ANM_FRAMES = 31, BTP_ANM_PACKED = 3872 };
typedef struct {
    uint16_t length, end[BTP_ANM_FRAMES], units[BTP_ANM_FRAMES];
    uint8_t count, bytes[BTP_ANM_BYTES];
} BtpAnm;
/* Optional Updated art has its own slots; original O*.ANM indices and saved
   cutscene identities keep their original meanings. */
enum { BTP_PORTRAIT_BROKER, BTP_PORTRAIT_TRAINING, BTP_PORTRAIT_LOUNGE,
    BTP_PORTRAIT_PRISON, BTP_PORTRAIT_INVENTOR, BTP_PORTRAIT_CINEMA,
    BTP_PORTRAIT_HOSPITAL, BTP_PORTRAIT_COMSTAR, BTP_PORTRAIT_CLOTHES,
    BTP_PORTRAIT_VIDEO_HUT, BTP_PORTRAIT_MAYOR, BTP_PORTRAIT_COUNT };
typedef struct { BtpAnm image[BTP_PORTRAIT_COUNT]; } BtpPortraits;
/* 43 earlier bank/Talk strings plus 12 class transcript/rank/subject strings. */
enum { BTP_TALK_LEGACY_STRINGS = 373, BTP_TALK_STRINGS = 375, BTP_TALK_MAX = 16384 };
typedef struct {
    uint8_t bytes[BTP_TALK_MAX];
    uint8_t font[2048];
    uint16_t length, offset[BTP_TALK_STRINGS], size[BTP_TALK_STRINGS], count;
} BtpDialogue;
enum { BTP_WORLD_SIDE=192, BTP_WORLD_ORIGIN=704, BTP_CITADEL_ORIGIN=768 };
typedef struct {
    uint32_t seed;
    uint8_t loaded, native, tiles[BTP_WORLD_SIDE*BTP_WORLD_SIDE];
    uint8_t coarse[336], flips[96];
    uint16_t textures[1024],special[64]; /* Custom tile handles retain all 16 bits. */
    uint8_t noise[256], heights[144*144];
    uint8_t mini_colors[256];
} BtpWorldData;
typedef struct {
    BtpMap map;
    BtpMap destroyed;
    BtpMap local[14];
    BtpGraphic tiles, destroyed_tiles, terrain_animation, sprites, quiz_diagram, border, title, logo, tinyland;
    BtpGraphic cache_tiles, maproom_tiles, phoenix;
    BtpMap maproom;
    uint8_t music[4356];uint16_t music_length;
    BtpBld citadel, armor, weapon, comstar, training, barracks, lounge, repair;
    BtpBld buildings[26];
    BtpDialogue dialogue;
    BtpAnm animations[BTP_ANM_COUNT];
    BtpCombatData combat;
    BtpWorldData world;
    BtpRoster roster; /* Empty in Original; immutable for a running session. */
    struct BtpProject *project; /* Owned by BtpContent; NULL for released editions. */
    BtpCombatProfile combat_profile; /* Optional authored Updated rules. */
    /* Cosmetic Updated-pack art, separate from original O*.ANM and save IDs. */
    BtpPortraits portraits;
    /* Explicit edition capabilities for loaded games. Zero retains the old
       low-level resource/test API; imported Original never infers its edition
       from the presence of editable definitions. This is not saved state. */
    uint8_t features;
    uint8_t sound_map[18]; /* Zero means the released program at this slot. */
    uint16_t sound_speed; /* Percent; zero retains the original timing. */
} BtpResources;
enum { BTP_FEATURE_BROKER=1, BTP_FEATURE_ENHANCED=2, BTP_FEATURE_EXPLICIT=128 };
int btp_resources_feature(const BtpResources *resources,unsigned feature);
typedef int (*BtpResourceRead)(void *context,const char *path,uint8_t **bytes,size_t *length,BtpError *error);
int btp_resources_load_reader(const char *directory,BtpResources *resources,
    BtpResourceRead reader,void *context,BtpError *error);

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
unsigned btp_generated_joined_tile(const BtpWorldData *data,int x,int y,unsigned neighbours);
#endif
