#ifndef BTP_CORE_CHI_BRIDGE_H
#define BTP_CORE_CHI_BRIDGE_H
#include "core/game.h"
enum { BTP_BRIDGE_BLD=1, BTP_BRIDGE_EVENT_CALL=2, BTP_BRIDGE_ENTRANCE=3, BTP_BRIDGE_NATIVE=4 };
void btp_bridge_initialize(BtpState *state,const BtpResources *resources);
int btp_bridge_entrance(BtpState *state,const BtpResources *resources);
int btp_bridge_script(BtpState *state,const BtpResources *resources);
int btp_bridge_call(BtpState *state,const BtpResources *resources,unsigned native);
void btp_bridge_return(BtpState *state,const BtpResources *resources,unsigned outcome);
void btp_bridge_pump(BtpState *state,const BtpResources *resources);
void btp_bridge_clear_checkpoint(BtpState *state);
int btp_bridge_cancel(BtpState *state,const BtpResources *resources,BtpAction action);
void btp_bridge_scene(BtpState *state,unsigned scene);
void btp_bridge_capture(const BtpState *state,BtpBridgePosition *position);
void btp_bridge_restore(BtpState *state,const BtpBridgePosition *position);
int btp_bridge_valid(const BtpState *state,const BtpResources *resources);
void btp_bridge_encode(const BtpState *state,uint8_t bytes[BTP_BRIDGE_BYTES]);
int btp_bridge_decode(BtpState *state,const uint8_t bytes[BTP_BRIDGE_BYTES]);
#endif
