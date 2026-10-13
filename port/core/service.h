#ifndef BTP_SERVICE_H
#define BTP_SERVICE_H
#include "core/game.h"
unsigned btp_mech_repair(BtpState *state,unsigned mech,unsigned kind,unsigned component);
unsigned btp_armour_repair(BtpState *state,unsigned member);
unsigned btp_mech_reload(BtpState *state,const BtpResources *resources,unsigned mech,unsigned bin,unsigned amount);
int btp_mech_refit(BtpState *state,const BtpResources *resources,unsigned mech);
unsigned btp_service_mech_count(const BtpState *state);
unsigned btp_service_mech_slot(const BtpState *state,unsigned ordinal);
unsigned btp_service_weapon_count(const BtpServiceState *service);
unsigned btp_service_weapon_item(const BtpServiceState *service,unsigned ordinal);
unsigned btp_service_ammo_weapon(const BtpState *state,unsigned mech,unsigned bin);
void btp_service_upgrade(BtpState *state);
void btp_service_begin(BtpState *state,const BtpResources *resources);
void btp_service_heal(BtpState *state,const BtpResources *resources,unsigned hospital,int field);
void btp_service_input(BtpState *state,const BtpResources *resources,BtpAction action);
int btp_service_valid(const BtpState *state);
#endif
