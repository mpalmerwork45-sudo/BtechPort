#ifndef BTP_LUA_EVENTS_H
#define BTP_LUA_EVENTS_H
#include "core/game.h"
int btp_lua_compile(const char *source,size_t length,char error[256]);
int btp_lua_event(const BtpResources *resources,const BtpState *state,unsigned *next,char error[256]);
#endif
