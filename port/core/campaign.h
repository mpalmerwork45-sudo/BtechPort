#ifndef BTP_CAMPAIGN_H
#define BTP_CAMPAIGN_H
#include "core/game.h"
void btp_campaign_rex(BtpState *state,const BtpResources *resources);
/* Shared combat initialization; authored encounters supply their own map,
   enemy placements and outcome continuation after creating the party. */
void btp_campaign_begin(BtpState *state,const BtpResources *resources,unsigned event);
int btp_campaign_random(BtpState *state,const BtpResources *resources);
unsigned btp_campaign_candidates(BtpState *state,const BtpResources *resources,BtpCombatUnit units[12],uint8_t ids[12],int *x,int *y);
void btp_campaign_result(BtpState *state,const BtpResources *resources);
void btp_campaign_avoid(BtpState *state);
unsigned btp_aftermath_cash(uint8_t rng[3],unsigned count);
int btp_salvage_eligible(const uint8_t record[125],unsigned skill);
void btp_salvage_copy(BtpState *state,unsigned slot,unsigned pilot,const uint8_t record[125],unsigned kind);
void btp_campaign_destroy(BtpState *state,unsigned unit);
void btp_campaign_eject(BtpState *state);
void btp_aftermath_input(BtpState *state,const BtpResources *resources,BtpAction action);
int btp_aftermath_valid(const BtpState *state);
unsigned btp_aftermath_cash_resources(uint8_t rng[3],unsigned count,const BtpResources *r);
int btp_salvage_eligible_resources(const uint8_t record[125],unsigned skill,const BtpResources *r);
void btp_campaign_destroy_resources(BtpState *s,unsigned unit,const BtpResources *r);
int btp_aftermath_valid_resources(const BtpState *s,const BtpResources *r);
#endif
