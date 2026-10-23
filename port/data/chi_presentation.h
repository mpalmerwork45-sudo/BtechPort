#ifndef BTP_CHI_PRESENTATION_H
#define BTP_CHI_PRESENTATION_H
#include "data/project.h"
BtpGraphic *btp_chi_graphic(BtpResources *r,const char *name);
int btp_chi_presentation_load(const char *root,const char *file,BtpProject *project,
    BtpPortraits *portraits,BtpDigest *digest,BtpError *error);
/* Palette names describe native display indices, not the storage packing. */
unsigned btp_chi_palette(unsigned palette,unsigned index);
#endif
