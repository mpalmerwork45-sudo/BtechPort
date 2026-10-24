#ifndef BTP_CHI_MISSIONS_H
#define BTP_CHI_MISSIONS_H
#include "data/resources.h"
#include "data/digest.h"
#include "data/unit_data.h"
#include "data/chi_mission_ids.h"
typedef struct { const char *id,*label,*group;unsigned low,high,initial;size_t offset;unsigned width; } BtpChiMissionParameter;
typedef struct { const char *id,*label;BtpMechTemplate kind;unsigned index; } BtpChiMissionUnit;
typedef struct {
    unsigned values[BTP_MIS_COUNT],defaults[BTP_MIS_COUNT];
    char units[BTP_MUNIT_COUNT][64];
    uint8_t records[BTP_MUNIT_COUNT][125],overridden[BTP_MUNIT_COUNT];
} BtpChiMissions;
extern const BtpChiMissionParameter btp_chi_mission_parameters[BTP_MIS_COUNT];
extern const BtpChiMissionUnit btp_chi_mission_units[BTP_MUNIT_COUNT];
unsigned btp_chi_mission(const BtpResources *r,unsigned key);
unsigned btp_chi_mission_default(const BtpResources *r,unsigned key);
unsigned btp_chi_training(const BtpResources *r,unsigned assignment,unsigned field);
unsigned btp_chi_training_enemy(const BtpResources *r,unsigned assignment,unsigned enemy,unsigned axis);
const uint8_t *btp_chi_mission_unit(const BtpResources *r,unsigned role);
unsigned btp_chi_training_unit(unsigned assignment,unsigned enemy);
int btp_chi_missions_load(const char *root,const char *file,BtpChiMissions *m,BtpResources *r,BtpDigest *digest,BtpError *e);
int btp_chi_missions_resolve(BtpChiMissions *m,const BtpResources *r,const BtpRoster *roster,BtpError *e);
void btp_chi_missions_catalogue(const BtpResources *r);
int btp_chi_mission_reference(const BtpResources *r,const char *id,unsigned *value);
#endif
