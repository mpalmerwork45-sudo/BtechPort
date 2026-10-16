#include "core/roster_game.h"
#include "core/party.h"
#include "core/npc.h"
#include "core/menu.h"
#include "core/economy.h"
#include <string.h>

int btp_broker_available(const BtpState *s,const BtpResources *r)
{
    return r->roster.count && s->map_id==2 && s->story_flags[4] && !s->yard.active &&
        !s->cache.active && !s->combat.phase && !s->campaign.encounter &&
        (s->mode==BTP_EXPLORE || s->mode==BTP_ACTIONS);
}
unsigned btp_broker_buy(BtpState *s,const BtpResources *r,unsigned definition)
{
    if (!btp_broker_available(s,r) || definition>=r->roster.count) return BTP_BROKER_UNAVAILABLE;
    const BtpRosterMech *d=&r->roster.mechs[definition];
    if (s->credits<d->price) return BTP_BROKER_NO_FUNDS;
    unsigned bay=0;
    if (s->party.enabled) { while (bay<4 && s->party.mech_types[bay]!=255) ++bay; }
    else bay=s->campaign.owned ? 1u : 0u;
    if (bay==4) return BTP_BROKER_FULL;
    /* Publish ownership and payment together. Starport forbids mechs on its
       streets: new purchases join the parked roster, with no crew assigned.
       The existing garage/exit allocation restores their complete records. */
    btp_party_init(s);
    uint8_t *m=btp_party_mech(s,bay);memcpy(m,d->record,125);
    s->party.mech_types[bay]=m[0];m[0]=255;
    s->campaign.owned=1;s->story_flags[24]=1;s->credits-=d->price;
    if (s->npc.enabled) s->npc.allowance_pending=(uint8_t)btp_economy_below_cap(s);
    return BTP_BROKER_BOUGHT;
}
const uint8_t *btp_roster_enemy(BtpState *s,const BtpResources *r)
{
    if (!r->roster.count || !s->story_flags[4] || s->map_id==2) return NULL;
    unsigned weight=0,eligible[BTP_ROSTER_MAX],count=0;
    for (unsigned i=0;i<4;++i) if (s->party.mech_types[i]!=255) {
        const uint8_t *m=btp_party_mech(s,i);if (m[16]>weight) weight=m[16];
    }
    for (unsigned i=0;i<r->roster.count;++i) if (r->roster.mechs[i].record[16]<=weight+15u) eligible[count++]=i;
    /* An optional quarter of eligible outdoor mech spawns. Do not consume
       any new random draws in Original or in fixed story/training battles. */
    if (!count || (btp_rng_next(s->npc.rng)&3u)) return NULL;
    return r->roster.mechs[eligible[btp_rng_next(s->npc.rng)%count]].record;
}
static int record_valid(const uint8_t m[125],const BtpRoster *r)
{
    if (!btp_roster_custom(m)) return 1;
    const BtpRosterMech *d=btp_roster_definition(r,m);
    /* The live record can lose its first name byte when parked/destroyed.
       Identity, maxima and presentation must still resolve to the saved pack. */
    return d && !memcmp(m+1,d->record+1,16) && !memcmp(m+86,d->record+86,31) &&
        m[49]==d->record[49] && m[50]==d->record[50] && m[38]==d->record[38] && m[124]==d->record[124];
}
int btp_roster_state_valid(const BtpState *s,const BtpResources *r)
{
    if (s->campaign.ui>=BTP_MENU_UPDATED_ROOT && !btp_broker_available(s,r)) return 0;
    if (s->campaign.ui==BTP_MENU_BROKER || s->campaign.ui==BTP_MENU_BROKER_CONFIRM || s->campaign.ui==BTP_MENU_BROKER_RESULT) {
        if (!btp_broker_available(s,r) || s->menu.map_x!=r->roster.count ||
            s->menu.map_y>=r->roster.count || s->campaign.member*7u>=r->roster.count) return 0;
    }
    if (!record_valid(s->campaign.mech,&r->roster) || !record_valid(s->campaign.checkpoint_mech,&r->roster)) return 0;
    for (unsigned i=0;i<3;++i) if (!record_valid(s->party.mechs[i],&r->roster) || !record_valid(s->party_checkpoint.mechs[i],&r->roster)) return 0;
    for (unsigned i=0;i<4;++i) if (!record_valid(s->yard.mechs[i],&r->roster)) return 0;
    for (unsigned i=0;i<BTP_COMBAT_UNITS;++i) if (!s->combat.unit[i].infantry && !record_valid(s->combat.unit[i].record,&r->roster)) return 0;
    return 1;
}
