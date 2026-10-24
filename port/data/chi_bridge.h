#ifndef BTP_CHI_BRIDGE_H
#define BTP_CHI_BRIDGE_H
#include "data/resources.h"
#include "data/digest.h"
enum { BTP_CHI_BINDINGS=64, BTP_CHI_CALLS=64 };
typedef struct {
    char id[64];
    uint16_t event;
    uint8_t map,entrance;
} BtpChiBinding;
typedef struct {
    char id[64],program[64],label[64],return_label[64];
    uint16_t entry,end;
    uint8_t building,action;
} BtpChiCall;
typedef struct {
    unsigned binding_count,call_count;
    BtpChiBinding bindings[BTP_CHI_BINDINGS];
    BtpChiCall calls[BTP_CHI_CALLS];
} BtpChiBridge;
struct BtpProject;
int btp_chi_bridge_load(const char *root,const char *file,struct BtpProject *project,BtpDigest *digest,BtpError *error);
int btp_chi_bridge_resolve(struct BtpProject *project,BtpError *error);
int btp_chi_bridge_action(unsigned action);
#endif
