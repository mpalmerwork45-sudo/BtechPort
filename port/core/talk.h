#ifndef BTP_TALK_H
#define BTP_TALK_H
#include "core/game.h"
void btp_talk_begin(BtpState *state, const BtpResources *resources);
void btp_talk_input(BtpState *state, const BtpResources *resources, BtpAction action);
int btp_talk_valid(const BtpState *state, const BtpMap *map);
#endif
