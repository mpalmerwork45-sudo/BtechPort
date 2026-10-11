#ifndef BTP_SAVE_H
#define BTP_SAVE_H
#include "core/game.h"

/* One internal save slot. Loading commits only after complete validation.
   Saving writes an exclusive sibling temporary file before replacing the slot. */
int btp_save_write(const char *path, const BtpState *state,
    const BtpResources *resources, BtpError *error);
int btp_save_load(const char *path, BtpState *state,
    const BtpResources *resources, BtpError *error);
#endif
