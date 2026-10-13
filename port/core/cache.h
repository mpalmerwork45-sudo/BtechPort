#ifndef BTP_CACHE_H
#define BTP_CACHE_H
#include "core/game.h"
enum { BTP_CACHE_WALK,BTP_CACHE_NOTICE,BTP_CACHE_TERMINAL,BTP_CACHE_DOOR,
    BTP_CACHE_PEER,BTP_CACHE_CLIMB,BTP_CACHE_EXIT,BTP_CACHE_PHOENIX };
void btp_cache_begin(BtpState *state,const BtpResources *resources);
void btp_cache_restore_party(BtpState *state,const BtpResources *resources);
void btp_cache_script_end(BtpState *state,const BtpResources *resources);
void btp_cache_input(BtpState *state,const BtpResources *resources,BtpAction action);
unsigned btp_cache_tile(const BtpResources *resources,const BtpState *state,int x,int y);
int btp_cache_terminal(BtpState *state,const BtpResources *resources,unsigned x,unsigned y);
int btp_cache_door(BtpState *state,const BtpResources *resources,unsigned x,unsigned y,int door);
void btp_cache_toggle(BtpState *state,unsigned x,unsigned y);
int btp_cache_password(BtpState *state,const BtpResources *resources);
int btp_cache_valid(const BtpState *state);
int btp_cache_text(const BtpState *state,const BtpResources *resources,uint8_t *output,size_t capacity,size_t *length);
#endif
