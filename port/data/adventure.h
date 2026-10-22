#ifndef BTP_ADVENTURE_H
#define BTP_ADVENTURE_H
#include "data/resources.h"
#include "data/definitions.h"
#include "data/adventure_limits.h"

/* Bounded, immutable authored scenes. Visual tiles and rule tiles are
   separate: artwork never determines whether a roof can be walked through. */
typedef struct { char id[64],image[64];uint16_t graphic;uint8_t key,sheet,terrain,color; } BtpSceneTile;
typedef struct { char id[64],name[25],image[64];uint8_t x,y,person;uint16_t event,icon; } BtpSceneEntrance;
typedef struct {
    char id[64],name[64];unsigned origin_x,origin_y;
    BtpMap visual,rules;uint16_t cells[4096];
    unsigned entrance_count,world,explore_offset,explore_width,explore_height;BtpSceneEntrance entrances[64];
} BtpScene;
typedef struct { char id[64],name[64];unsigned width,height,base,explore_offset; } BtpAuthoredWorld;
typedef struct { char id[64],name[64];uint16_t cells[64]; } BtpJigsaw;
typedef struct { char id[64],name[32],image[64];uint16_t graphic;uint8_t record[17]; } BtpScenePerson;
typedef struct { char id[64];unsigned count;uint16_t stock[256]; } BtpSceneShop;
enum { BTP_OBJECTIVE_INACTIVE, BTP_OBJECTIVE_ACTIVE, BTP_OBJECTIVE_COMPLETE, BTP_OBJECTIVE_FAILED };
typedef struct { char id[64],title[49],text[385];unsigned active,complete,explicit_state,initial; } BtpObjective;
typedef struct { char id[64],name[64];unsigned boolean,initial,maximum; } BtpMissionVariable;
/* Rectangle coordinates are local map tiles; triggers use the party leader's
   half-tile anchor, including when a city is embedded in a world. */
typedef struct {
    char id[64],name[64];unsigned map,x,y,width,height,repeat;
    uint16_t enter,leave; /* BTP_EVENT_NODES means no trigger. */
} BtpMissionRegion;
enum { BTP_CONDITION_FLAG, BTP_CONDITION_VARIABLE, BTP_CONDITION_OBJECTIVE, BTP_CONDITION_REGION,
    BTP_CONDITION_GROUP_ALIVE, BTP_CONDITION_GROUP_DESTROYED, BTP_CONDITION_GROUP_DEPLOYED,
    BTP_CONDITION_GROUP_ARRIVED, BTP_CONDITION_COMBAT_ROUND };
typedef struct { unsigned kind,argument,compare,value; } BtpMissionCondition;
typedef struct { uint8_t x,y,infantry;uint16_t definition; } BtpSceneEnemy;
typedef struct {
    char id[64];unsigned map,x,y,count,scripted;BtpSceneEnemy enemies[12];
} BtpSceneBattle;
enum { BTP_SIDE_HOSTILE, BTP_SIDE_FRIENDLY, BTP_SIDE_NEUTRAL };
enum { BTP_HOOK_START, BTP_HOOK_ROUND_START, BTP_HOOK_ROUND_END, BTP_HOOK_DESTROYED, BTP_HOOK_ARRIVAL };
typedef struct {
    BtpSceneEnemy unit;
    unsigned waypoint_count,movement;uint8_t waypoints[BTP_ACTOR_WAYPOINTS][2];
} BtpMissionActor;
typedef struct {
    char id[64],name[64];unsigned battle,side,reserve,count;
    BtpMissionActor actors[12];
} BtpCombatGroup;
typedef struct {
    char id[64];unsigned battle,when,group,first,every,repeat;uint16_t event;
} BtpCombatHook;
typedef enum { BTP_EVENT_END, BTP_EVENT_SAY, BTP_EVENT_CHOICE, BTP_EVENT_IF,
    BTP_EVENT_FLAG, BTP_EVENT_REWARD, BTP_EVENT_RECRUIT, BTP_EVENT_TRANSFER,
    BTP_EVENT_SHOP, BTP_EVENT_BATTLE, BTP_EVENT_LUA, BTP_EVENT_FINISH, BTP_EVENT_PICTURE,
    BTP_EVENT_REPAIR, BTP_EVENT_REARM, BTP_EVENT_HEAL, BTP_EVENT_SALVAGE,
    BTP_EVENT_VARIABLE, BTP_EVENT_OBJECTIVE, BTP_EVENT_CHECK,
    BTP_EVENT_REINFORCE, BTP_EVENT_BATTLE_END } BtpEventOp;
typedef struct {
    char id[64],text[1024],labels[BTP_EVENT_OPTIONS][25];
    char image[64];uint16_t picture;
    uint16_t next[BTP_EVENT_OPTIONS];
    unsigned op,argument,value,x,y,count,portrait;
    BtpMissionCondition conditions[BTP_CONDITIONS];
} BtpEventNode;
typedef struct {
    unsigned loaded,map_count,tile_count,person_count,shop_count,battle_count,node_count,flag_count;
    unsigned version,local_count,jigsaw_count,world_count,explore_cells,objective_count;
    BtpObjective objectives[BTP_OBJECTIVES];
    unsigned mission_state,variable_count,region_count;
    BtpMissionVariable variables[BTP_VARIABLES];
    BtpMissionRegion regions[BTP_REGIONS];
    unsigned combat_missions,group_count,hook_count;
    BtpCombatGroup groups[BTP_COMBAT_GROUPS];BtpCombatHook hooks[BTP_COMBAT_HOOKS];
    BtpAuthoredWorld worlds[BTP_WORLDS];
    uint8_t source_digest[32];
    unsigned start_map,start_x,start_y,start_event,credits,party_count;
    uint8_t party[8];uint16_t mechs[8]; /* 256 means on foot. */
    BtpSceneTile tiles[BTP_SCENE_TILES];BtpScene maps[BTP_SCENES];
    BtpJigsaw jigsaws[BTP_JIGSAWS];uint16_t pieces[128*128];
    BtpScenePerson people[BTP_SCENE_PEOPLE];BtpSceneShop shops[BTP_SCENE_SHOPS];
    BtpSceneBattle battles[BTP_SCENE_BATTLES];BtpEventNode nodes[BTP_EVENT_NODES];
    char flags[BTP_EVENT_FLAGS][64];
} BtpAdventure;
int btp_adventure_load(const char *path,const BtpDefinitions *definitions,BtpAdventure *out,char error[256]);
int btp_scene_stand(const BtpScene *scene,int x,int y,int mech);
/* Compiled world sectors keep the original tactical window small. Tile IDs
   remain 16-bit throughout composition and graphics never become rule IDs. */
int btp_adventure_world_at(const BtpAdventure *adventure,unsigned world,int x,int y);
const BtpSceneTile *btp_scene_tile(const BtpAdventure *adventure,const BtpScene *scene,int x,int y);
/* Shared wrapping keeps validation, saved page indices and rendering aligned. */
unsigned btp_event_lines(const char *text,char lines[96][28]);
#endif
