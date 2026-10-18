#ifndef BTP_ART_ACTIONS_H
#define BTP_ART_ACTIONS_H
#include "core/game.h"
#include "data/art.h"
unsigned btp_unit_image(const BtpResources *r,const uint8_t record[125]);
unsigned btp_person_image(const BtpResources *r,unsigned person);
unsigned btp_actor_image(const BtpResources *r,const BtpState *s,unsigned actor);
unsigned btp_actor_action(const BtpState *s,unsigned actor,unsigned *elapsed);
unsigned btp_action_duration(const BtpResources *r,const BtpState *s,unsigned actor,unsigned action);
unsigned btp_action_sound(const BtpResources *r,const BtpState *s,unsigned actor,unsigned action,unsigned fallback);
#endif
