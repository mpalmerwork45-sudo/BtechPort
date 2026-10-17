#ifndef BTP_PORTRAITS_H
#define BTP_PORTRAITS_H
#include "data/resources.h"

/* Loads optional art beside the selected roster. The caller owns/frees the
   returned allocation; failure returns NULL without publishing partial art. */
BtpPortraits *btp_portraits_load(const char *roster_path,BtpError *error);
const BtpAnm *btp_portrait_for_building(const BtpResources *resources,unsigned building);
#endif
