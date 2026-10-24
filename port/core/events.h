#ifndef BTP_EVENTS_H
#define BTP_EVENTS_H
#include "core/game.h"
#include "data/adventure.h"
enum { BTP_EVENT_INACTIVE, BTP_EVENT_ENTRY, BTP_EVENT_TEXT, BTP_EVENT_SELECT,
    BTP_EVENT_TRADING, BTP_EVENT_FIGHTING, BTP_EVENT_FAULT, BTP_EVENT_COMPLETE, BTP_EVENT_PRESENTATION };
typedef void (*BtpEventObserver)(void *context,const BtpState *state,const BtpResources *resources,const BtpEventNode *node);
typedef void (*BtpBattleObserver)(void *context,const BtpState *state,const BtpResources *resources,const BtpSceneBattle *encounter);
/* Optional diagnostics receive command-entry snapshots; never change rules,
   RNG or saved state. The single-game frontend owns the observer lifetime. */
void btp_events_observe(BtpEventObserver observer,void *context);
/* Final combat state is observed before authored result cleanup discards it.
   Diagnostic observers must not change simulation or persistence behavior. */
void btp_events_observe_battles(BtpBattleObserver observer,void *context);
unsigned btp_journal_count(const BtpState *state,const BtpResources *resources);
void btp_journal_text(const BtpState *state,const BtpResources *resources,unsigned page,char text[1024]);
const BtpAdventure *btp_adventure(const BtpResources *resources);
const BtpScene *btp_scene(const BtpResources *resources,const BtpState *state);
void btp_events_start(BtpState *state,const BtpResources *resources);
/* Scenario seeds enter before the first event (including an immediate battle).
   NULL retains the normal game's original initial random state. */
void btp_events_start_seeded(BtpState *state,const BtpResources *resources,const uint8_t seed[3]);
int btp_events_preview(BtpState *state,const BtpResources *resources,const char *map,unsigned x,unsigned y);
void btp_events_tick(BtpState *state,const BtpResources *resources,BtpAction action);
void btp_events_continue(BtpState *state,const BtpResources *resources);
void btp_events_jump(BtpState *state,unsigned node);
int btp_events_valid(const BtpState *state,const BtpResources *resources);
void btp_events_encode(const BtpState *state,uint8_t bytes[128]);
int btp_events_decode(BtpState *state,const uint8_t bytes[128]);
unsigned btp_events_catalogue(const BtpState *state,const BtpResources *resources,unsigned weight_class,unsigned limit,unsigned indices[256]);
int btp_events_stock(const BtpState *state,const BtpResources *resources,unsigned definition);
#endif
