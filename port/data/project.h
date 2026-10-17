#ifndef BTP_PROJECT_H
#define BTP_PROJECT_H
#include "data/definitions.h"
#include "data/resources.h"
typedef struct BtpProject {
    char id[32],version[32],title[96];
    uint8_t digest[32];
    BtpDefinitions definitions;
} BtpProject;
/* A CHI-dependent editable directory. Validation and runtime use the same
   loader, including decoding every explicitly declared portrait. Caller owns
   the returned project; failed loads publish neither definitions nor art. */
BtpProject *btp_project_load(const char *directory,BtpRoster *roster,BtpPortraits *portraits,BtpError *error);
int btp_project_path(const char *directory,const char *relative,char path[4096],BtpError *error);
int btp_project_export_manifest(const char *directory,const char *id,const char *version,
    const BtpCombatProfile *rules,const BtpPortraits *portraits,BtpError *error);
#endif
