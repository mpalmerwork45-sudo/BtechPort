#ifndef BTP_CHI_H
#define BTP_CHI_H
#include "data/resources.h"
#include "data/json.h"
#include "data/digest.h"
/* Full private snapshots, hashed and decoded from the same bytes. No fallback
   to the user's DOS directory is allowed for this opt-in package extension. */
BtpResources *btp_chi_project_load(const char *root,BtpJson *manifest,
    BtpDigest *digest,unsigned *edition,BtpError *error);
const char *btp_chi_resource_name(unsigned index);
enum { BTP_CHI_FILES=79 };
#endif
