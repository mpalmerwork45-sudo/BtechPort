#ifndef BTP_CHI_SCRIPTS_H
#define BTP_CHI_SCRIPTS_H
#include "data/resources.h"
#include "data/digest.h"
enum { BTP_CHI_PROGRAMS=26, BTP_BLD_SOURCE_NODES=2048 };
typedef struct {
    char id[64];
    uint16_t offset,length,origin,original_size;
    uint8_t opcode;
} BtpChiInstruction;
typedef struct {
    char id[64],name[96];
    uint16_t count,original_length;
    BtpChiInstruction *nodes;
    uint16_t *offsets; /* Original byte offset -> compiled offset, including end. */
    uint16_t *ends; /* Original instruction end -> compiled instruction end. */
} BtpChiProgram;
typedef struct { BtpChiProgram programs[BTP_CHI_PROGRAMS]; } BtpChiScripts;
int btp_chi_scripts_load(const char *root,const char *file,BtpChiScripts *scripts,
    BtpResources *resources,BtpDigest *digest,BtpError *error);
void btp_chi_scripts_free(BtpChiScripts *scripts);
/* Native context guards retain their original semantic anchors after edits. */
unsigned btp_bld_offset(const BtpBld *script,unsigned original);
unsigned btp_bld_after(const BtpBld *script,unsigned original);
#endif
