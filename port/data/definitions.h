#ifndef BTP_DEFINITIONS_H
#define BTP_DEFINITIONS_H
#include "data/roster.h"
#include "data/combat_profile.h"

/* Authoring model, independent of DOS record offsets and numeric weapon IDs.
   Owned damage/crew/ammunition remain in game instances, never here. The CHI
   adapter is intentionally limited to capabilities the player implements. */
enum { BTP_DEFINITION_LIMIT=256, BTP_CONTENT_NAME=96 };
typedef struct { char id[64];unsigned price; } BtpAmmoDefinition;
typedef struct { char id[64],image[64];unsigned sprite,independent,graphic; } BtpPresentationDefinition;
typedef struct {
    char id[64],name[BTP_CONTENT_NAME],label[12],ammunition[64];
    unsigned behavior,damage,projectiles,heat,near_range,medium_range,far_range;
} BtpAuthoredWeapon;
typedef struct { unsigned weapon,location,ammo; } BtpMountDefinition;
typedef struct { char id[64],name[BTP_CONTENT_NAME],label[12];unsigned behavior; } BtpEquipmentDefinition;
typedef struct {
    char id[64],name[BTP_CONTENT_NAME],label[16];
    unsigned mass,walk,jump,sinks,presentation,price,count,vehicle;
    unsigned armor[11],structure[8],actuators[2],external_sinks[8];
    BtpMountDefinition mounts[10];
} BtpMechDefinition;
typedef struct BtpDefinitions {
    char id[32],version[32],broker[64],reload[64];
    unsigned weapon_count,mech_count,ammo_count,presentation_count,equipment_count;
    BtpCombatProfile rules;
    uint8_t source_digest[32];
    BtpAuthoredWeapon weapons[BTP_DEFINITION_LIMIT];
    BtpMechDefinition mechs[BTP_DEFINITION_LIMIT];
    BtpAmmoDefinition ammo[BTP_DEFINITION_LIMIT];
    BtpPresentationDefinition presentations[BTP_DEFINITION_LIMIT];
    BtpEquipmentDefinition equipment[BTP_DEFINITION_LIMIT];
    /* Compiled mount order belongs to the adapter, never the JSON contract. */
    uint16_t mount_weapon[BTP_DEFINITION_LIMIT][10];
    uint8_t mount_location[BTP_DEFINITION_LIMIT][10];
} BtpDefinitions;
struct BtpCombatData;
int btp_definitions_load(const char *path,BtpDefinitions *out,char error[256]);
int btp_definitions_compile(BtpDefinitions *definitions,BtpRoster *roster,char error[256]);
const BtpAuthoredWeapon *btp_authored_weapon(const BtpDefinitions *definitions,const uint8_t record[125],unsigned mount);
const char *btp_behavior_name(unsigned behavior);
const char *btp_body_name(unsigned location);
/* Exclusive creation: export never overwrites an author's existing file. */
int btp_definitions_export(const char *path,const BtpRoster *roster,const struct BtpCombatData *combat,const BtpCombatProfile *rules,char error[256]);
#endif
