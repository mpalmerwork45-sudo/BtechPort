#ifndef BTP_AUTHORED_SERVICES_H
#define BTP_AUTHORED_SERVICES_H
#include "core/game.h"
#include "data/adventure.h"
/* Branch offsets: success, failure, nothing to do. Prices are author-defined
   flat fees; these commands do not change the original campaign's services. */
unsigned btp_authored_service(BtpState *state,const BtpResources *resources,const BtpEventNode *event);
#endif
