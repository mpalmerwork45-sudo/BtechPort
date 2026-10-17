#ifndef BTP_COMBAT_AI_H
#define BTP_COMBAT_AI_H
#include "core/game.h"
/* Pure, deterministic planning result. Diagnostics are not hidden AI memory;
   committed paths/orders already live in the versioned combat state. */
typedef struct {
    uint8_t movement,x,y,direction,target,orders[12],steps;
    int8_t path[12][2];
    int score;
    unsigned candidates;
} BtpAiPlan;
int btp_combat_ai_plan(const BtpState *state,const BtpResources *resources,
    const BtpMap *map,unsigned actor,BtpAiPlan *plan);
unsigned btp_combat_actor_skill(const BtpState *state,unsigned actor,unsigned weapon);
/* Automated orders may wait for an improving shot along their own path.
   Existing order/fired bytes suffice to resume this decision after a save. */
int btp_combat_ai_fire(const BtpState *state,const BtpResources *resources,const BtpMap *map,
    unsigned actor,unsigned target,unsigned mount,int movement);
#endif
