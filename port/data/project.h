#ifndef BTP_PROJECT_H
#define BTP_PROJECT_H
#include "data/definitions.h"
#include "data/resources.h"
#include "data/adventure.h"
#include "data/independent.h"
#include "data/art.h"
#include "data/chi_spatial.h"
#include "data/chi_scripts.h"
enum { BTP_LUA_SCRIPTS=16, BTP_LUA_SOURCE=8192 };
typedef struct { char id[64],source[BTP_LUA_SOURCE+1];size_t length; } BtpLuaScript;
typedef struct BtpProject {
    char id[32],version[32],title[96];
    uint8_t digest[32];
    BtpDefinitions definitions;
    BtpAdventure adventure;
    BtpIndependent independent;
    BtpArt graphics;
    unsigned script_count;
    BtpLuaScript scripts[BTP_LUA_SCRIPTS];
    unsigned chi_edition; /* 0: ordinary project, 1: Original, 2: Updated */
    BtpResources *chi_resources; /* Decoded once while validating; transferred on load. */
    BtpChiSpatial *chi_spatial; /* Native maps/world, independent of authored events. */
    BtpChiScripts *chi_scripts; /* Label/source maps own the BLD relocation arrays. */
    uint16_t chi_animations[BTP_ANM_COUNT]; /* One-based package images, zero native. */
    uint16_t chi_portraits[BTP_PORTRAIT_COUNT];
} BtpProject;
/* A CHI-dependent editable directory. Validation and runtime use the same
   loader, including decoding every explicitly declared portrait. Caller owns
   the returned project; failed loads publish neither definitions nor art. */
BtpProject *btp_project_load(const char *directory,BtpRoster *roster,BtpPortraits *portraits,BtpError *error);
void btp_project_free(BtpProject *project);
int btp_project_path(const char *directory,const char *relative,char path[4096],BtpError *error);
int btp_project_export_manifest(const char *directory,const char *id,const char *version,
    const BtpCombatProfile *rules,const BtpPortraits *portraits,BtpError *error);
#endif
