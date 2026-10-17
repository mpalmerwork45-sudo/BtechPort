#ifndef BTP_EVENTS_H
#define BTP_EVENTS_H
#include "core/game.h"
#include "data/adventure.h"
enum { BTP_EVENT_INACTIVE, BTP_EVENT_ENTRY, BTP_EVENT_TEXT, BTP_EVENT_SELECT,
    BTP_EVENT_TRADING, BTP_EVENT_FIGHTING, BTP_EVENT_FAULT };
const BtpAdventure *btp_adventure(const BtpResources *resources);
const BtpScene *btp_scene(const BtpResources *resources,const BtpState *state);
void btp_events_start(BtpState *state,const BtpResources *resources);
void btp_events_tick(BtpState *state,const BtpResources *resources,BtpAction action);
int btp_events_valid(const BtpState *state,const BtpResources *resources);
void btp_events_encode(const BtpState *state,uint8_t bytes[128]);
int btp_events_decode(BtpState *state,const uint8_t bytes[128]);
unsigned btp_events_catalogue(const BtpState *state,const BtpResources *resources,unsigned weight_class,unsigned limit,unsigned indices[256]);
int btp_events_stock(const BtpState *state,const BtpResources *resources,unsigned definition);
#endif
