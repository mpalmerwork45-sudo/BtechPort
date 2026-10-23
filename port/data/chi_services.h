#ifndef BTP_CHI_SERVICES_H
#define BTP_CHI_SERVICES_H
#include "data/resources.h"
#include "data/digest.h"
#include "data/chi_service_ids.h"
enum { BTP_SVC_SOURCE_CONSTANT,BTP_SVC_SOURCE_AMMO,BTP_SVC_SOURCE_REFIT,BTP_SVC_SOURCE_MEDICAL_PRICE,BTP_SVC_SOURCE_MEDICAL_CODE };
typedef struct { const char *id,*label,*group;unsigned low,high,initial,source,index; } BtpChiParameter;
typedef struct { unsigned action,buildings;const char *id,*name,*group,*consumer,*requires,*outputs,*mutations,*yields,*errors; } BtpChiAction;
typedef struct {
    uint32_t values[BTP_SVC_COUNT],defaults[BTP_SVC_COUNT];
    unsigned stock_count,stock_limited;
    char stock_ids[256][64];uint8_t stock[256];
} BtpChiServices;
extern const BtpChiParameter btp_chi_parameters[BTP_SVC_COUNT];
extern const BtpChiAction btp_chi_actions[47];
unsigned btp_chi_service(const BtpResources *resources,unsigned parameter);
unsigned btp_chi_service_default(const BtpResources *resources,unsigned parameter);
int btp_chi_services_load(const char *root,const char *file,BtpChiServices *services,BtpResources *resources,BtpDigest *digest,BtpError *error);
int btp_chi_services_stock(BtpChiServices *services,const BtpRoster *roster,BtpError *error);
int btp_chi_broker_stock(const BtpResources *resources,unsigned definition);
/* Tool output is the shared catalogue for GUI, CLI and source builders. */
void btp_chi_services_catalogue(const BtpResources *resources);
int btp_chi_service_reference(const BtpResources *resources,const char *id,unsigned *value);
int btp_chi_service_expand(const BtpResources *resources,const char *source,char *output,size_t capacity);
int btp_chi_service_dialogue(BtpResources *resources,BtpError *error);
#endif
