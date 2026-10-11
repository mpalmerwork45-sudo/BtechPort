#ifndef BTP_ANM_H
#define BTP_ANM_H
#include "data/resources.h"
int btp_anm_decode(const uint8_t *bytes, size_t length, BtpAnm *animation, BtpError *error);
int btp_anm_frame(const BtpAnm *animation, unsigned index, uint8_t packed[BTP_ANM_PACKED]);
#endif
