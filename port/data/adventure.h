#ifndef BTP_ADVENTURE_H
#define BTP_ADVENTURE_H
#include "data/resources.h"
#include "data/definitions.h"

/* Bounded, immutable authored scenes. Visual tiles and rule tiles are
   separate: artwork never determines whether a roof can be walked through. */
enum { BTP_SCENES=16, BTP_EVENT_NODES=256, BTP_EVENT_FLAGS=64,
    BTP_SCENE_TILES=64, BTP_SCENE_PEOPLE=16, BTP_SCENE_SHOPS=16,
    BTP_SCENE_BATTLES=16, BTP_EVENT_OPTIONS=6, BTP_AUTHORED_MAP_FIRST=16 };
typedef struct { char id[64];uint8_t key,graphic,sheet,terrain,color; } BtpSceneTile;
typedef struct { char id[64],name[25];uint8_t x,y,person;uint16_t event; } BtpSceneEntrance;
typedef struct {
    char id[64],name[64];unsigned origin_x,origin_y;
    BtpMap visual,rules;uint8_t cells[4096];
    unsigned entrance_count;BtpSceneEntrance entrances[16];
} BtpScene;
typedef struct { char id[64],name[32];uint8_t record[17]; } BtpScenePerson;
typedef struct { char id[64];unsigned count;uint16_t stock[256]; } BtpSceneShop;
typedef struct { uint8_t x,y,infantry;uint16_t definition; } BtpSceneEnemy;
typedef struct {
    char id[64];unsigned map,x,y,count;BtpSceneEnemy enemies[12];
} BtpSceneBattle;
typedef enum { BTP_EVENT_END, BTP_EVENT_SAY, BTP_EVENT_CHOICE, BTP_EVENT_IF,
    BTP_EVENT_FLAG, BTP_EVENT_REWARD, BTP_EVENT_RECRUIT, BTP_EVENT_TRANSFER,
    BTP_EVENT_SHOP, BTP_EVENT_BATTLE, BTP_EVENT_LUA, BTP_EVENT_FINISH } BtpEventOp;
typedef struct {
    char id[64],text[1024],labels[BTP_EVENT_OPTIONS][25];
    uint16_t next[BTP_EVENT_OPTIONS];
    unsigned op,argument,value,x,y,count,portrait;
} BtpEventNode;
typedef struct {
    unsigned loaded,map_count,tile_count,person_count,shop_count,battle_count,node_count,flag_count;
    uint8_t source_digest[32];
    unsigned start_map,start_x,start_y,start_event,credits,party_count;
    uint8_t party[8];uint16_t mechs[8]; /* 256 means on foot. */
    BtpSceneTile tiles[BTP_SCENE_TILES];BtpScene maps[BTP_SCENES];
    BtpScenePerson people[BTP_SCENE_PEOPLE];BtpSceneShop shops[BTP_SCENE_SHOPS];
    BtpSceneBattle battles[BTP_SCENE_BATTLES];BtpEventNode nodes[BTP_EVENT_NODES];
    char flags[BTP_EVENT_FLAGS][64];
} BtpAdventure;
int btp_adventure_load(const char *path,const BtpDefinitions *definitions,BtpAdventure *out,char error[256]);
int btp_scene_stand(const BtpScene *scene,int x,int y,int mech);
/* Shared wrapping keeps validation, saved page indices and rendering aligned. */
unsigned btp_event_lines(const char *text,char lines[96][28]);
#endif
