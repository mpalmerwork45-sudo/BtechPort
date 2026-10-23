#include "core/roster_game.h"
#include "data/project.h"
#include "data/definitions.h"
#include "core/party.h"
#include "core/npc.h"
#include "core/menu.h"
#include "core/economy.h"
#include "core/events.h"
#include <string.h>

int btp_broker_page(unsigned page)
{
    return (page>=BTP_MENU_BROKER && page<=BTP_MENU_BROKER_SELL_RESULT) || page==BTP_MENU_BROKER_CLASSES;
}
int btp_broker_door(const BtpState *s,const BtpResources *r,int x,int y)
{
    if (r->project && r->project->chi_spatial && r->project->chi_spatial->broker_configured) {
        const BtpChiSpatial *c=r->project->chi_spatial;
        return btp_resources_feature(r,BTP_FEATURE_BROKER) && c->broker_enabled && s->map_id==2 && s->story_flags[4] && !s->campaign.mounted &&
            x==c->broker_x && y==c->broker_y;
    }
    /* The central three-door building already exists in MAP2's tiles, but
       has no original MTP entrance. Add a trigger, never modify the MTP. */
    return btp_resources_feature(r,BTP_FEATURE_BROKER) && s->story_flags[4] && s->map_id==2 && !s->campaign.mounted &&
        x==BTP_BROKER_X && y==BTP_BROKER_Y;
}
void btp_broker_open(BtpState *s)
{
    s->mode=BTP_ACTIONS;s->campaign.ui=BTP_MENU_BROKER_HUB;
    s->campaign.selected=s->campaign.member=0;s->menu.notice=s->menu.broker_class=0;
    s->script=(BtpScriptState){0};
}
unsigned btp_broker_owned(const BtpState *s,unsigned bay)
{
    if (bay>=4) return 0;
    if (!s->party.enabled) return !bay && s->campaign.owned;
    const uint8_t *m=bay ? s->party.mechs[bay-1] : s->campaign.mech;
    /* Both parked receipts and live records occupy a bay. Never overwrite
       a live mech merely because an imported receipt is missing. */
    return s->party.mech_types[bay]!=255 || m[0]!=255;
}
unsigned btp_broker_count(const BtpState *s)
{
    unsigned n=0;for (unsigned i=0;i<4;++i) n+=btp_broker_owned(s,i);return n;
}
unsigned btp_broker_slot(const BtpState *s,unsigned ordinal)
{
    for (unsigned i=0;i<4;++i) if (btp_broker_owned(s,i)) { if (!ordinal) return i;--ordinal; }
    return 4;
}
int btp_broker_available(const BtpState *s,const BtpResources *r)
{
    if (s->event.enabled) return btp_scene(r,s) && s->event.phase==BTP_EVENT_TRADING &&
        s->mode==BTP_ACTIONS && btp_broker_page(s->campaign.ui);
    return btp_resources_feature(r,BTP_FEATURE_BROKER) && s->map_id==2 && s->story_flags[4] && !s->yard.active &&
        !s->cache.active && !s->combat.phase && !s->campaign.encounter &&
        s->mode==BTP_ACTIONS && btp_broker_page(s->campaign.ui) &&
        s->campaign.building==BTP_BROKER_BUILDING && s->entry_slot==BTP_BROKER_ENTRY;
}
unsigned btp_broker_buy(BtpState *s,const BtpResources *r,unsigned definition)
{
    if (!btp_broker_available(s,r) || definition>=r->roster.count ||
        (s->event.enabled && !btp_events_stock(s,r,definition))) return BTP_BROKER_UNAVAILABLE;
    const BtpRosterMech *d=&r->roster.mechs[definition];
    unsigned bay=0;while (bay<4 && btp_broker_owned(s,bay)) ++bay;
    if (bay==4) return BTP_BROKER_FULL;
    if (s->credits<d->price) return BTP_BROKER_NO_FUNDS;
    /* Publish ownership and payment together. Starport forbids mechs on its
       streets: new purchases join the parked roster, with no crew assigned.
       The existing garage/exit allocation restores their complete records. */
    btp_party_init(s);
    uint8_t *m=btp_party_mech(s,bay);memcpy(m,d->record,125);
    s->party.mech_types[bay]=m[0];if (!s->event.enabled) m[0]=255;
    s->campaign.owned=1;s->story_flags[24]=1;s->credits-=d->price;
    if (s->npc.enabled) s->npc.allowance_pending=(uint8_t)btp_economy_below_cap(s);
    return BTP_BROKER_BOUGHT;
}
uint32_t btp_broker_offer(const BtpState *s,const BtpResources *r,unsigned bay)
{
    if (!btp_broker_owned(s,bay)) return 0;
    const uint8_t *m=bay ? s->party.mechs[bay-1] : s->campaign.mech;
    const BtpRosterMech *d=btp_roster_definition(&r->roster,m);
    /* Authored expansion economy: half catalogue price for an intact added
       mech, or 100 C-bills/ton for an original model. Damage lowers the offer;
       installed equipment is sold with the chassis. No original rule changes. */
    uint32_t base=d ? d->price/2u : (uint32_t)m[16]*100u;
    unsigned maximum=70,remaining=0;
    for (unsigned i=17;i<36;++i) { maximum+=m[i+69];remaining+=m[i]<m[i+69] ? m[i] : m[i+69]; }
    for (unsigned i=51;i<86;++i) {
        unsigned type=m[i]&127u;
        if ((type>=16 && type<=32) || type==34) { maximum+=10;remaining+=(m[i]&128u) ? 0u : 10u; }
    }
    for (unsigned i=0;i<2;++i) for (unsigned bit=1;bit<256;bit<<=1) if (m[105+i]&bit) {
        maximum+=2;remaining+=(m[36+i]&bit) ? 2u : 0u;
    }
    remaining+=10u*((3u-(m[117]<3 ? m[117] : 3u))+(2u-(m[118]<2 ? m[118] : 2u))+(2u-(m[119]<2 ? m[119] : 2u)));
    return (uint32_t)((uint64_t)base*remaining/maximum);
}
unsigned btp_broker_sell(BtpState *s,const BtpResources *r,unsigned bay)
{
    if (!btp_broker_available(s,r) || !btp_broker_owned(s,bay)) return BTP_BROKER_UNAVAILABLE;
    uint32_t offer=btp_broker_offer(s,r,bay);
    if (s->credits>UINT32_MAX-offer) return BTP_BROKER_CREDIT_LIMIT;
    btp_party_init(s);
    /* Clear ownership, both seats and every crew reference atomically. Other
       bays keep their indices, damage and equipment; there is no reshuffle. */
    for (unsigned i=0;i<8;++i) if (s->party.people[i][0]!=255 && s->party.people[i][12]==bay)
        s->party.people[i][12]=8;
    uint8_t *m=btp_party_mech(s,bay);memset(m,0,125);m[0]=m[121]=m[122]=255;
    s->party.mech_types[bay]=255;s->campaign.owned=(uint8_t)(btp_broker_count(s)!=0);
    s->campaign.mounted=(uint8_t)(s->party.people[0][12]<4);
    s->credits+=offer;
    if (s->npc.enabled) s->npc.allowance_pending=(uint8_t)btp_economy_below_cap(s);
    return BTP_BROKER_SOLD;
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
static int record_valid(const uint8_t m[125],const BtpRoster *r,unsigned count)
{
    if (!btp_roster_custom(m)) return 1;
    const BtpRosterMech *d=btp_roster_definition(r,m);
    /* The live record can lose its first name byte when parked/destroyed.
       Identity, maxima and presentation must still resolve to the saved pack. */
    return d && d<r->mechs+count && !memcmp(m+1,d->record+1,16) && !memcmp(m+86,d->record+86,31) &&
        m[49]==d->record[49] && m[50]==d->record[50] && m[38]==d->record[38] && m[124]==d->record[124];
}
int btp_roster_state_prefix_valid(const BtpState *s,const BtpResources *r,unsigned count)
{
    for (unsigned i=0;i<25;++i) {
        const BtpBattleText *t=i<24 ? &s->effects.text[i] : &s->effects.shown;
        if (t->authored && (!r->combat.definitions || t->content_weapon>=r->combat.definitions->weapon_count)) return 0;
    }
    if (count>r->roster.count) return 0;
    if (s->campaign.ui==BTP_MENU_UPDATED_ROOT) return 0;
    if (btp_broker_page(s->campaign.ui) && !btp_broker_available(s,r)) return 0;
    if (s->campaign.building==BTP_BROKER_BUILDING && (!r->roster.count || s->map_id!=2 ||
        !s->story_flags[4] || s->entry_slot!=BTP_BROKER_ENTRY ||
        (s->mode!=BTP_ENTRY && !btp_broker_page(s->campaign.ui)))) return 0;
    if (s->campaign.ui==BTP_MENU_BROKER_SELL_CONFIRM && !btp_broker_owned(s,s->menu.map_y)) return 0;
    if (s->campaign.ui==BTP_MENU_BROKER_SELL_RESULT && s->menu.map_y>=4) return 0;
    if (s->campaign.ui==BTP_MENU_BROKER_CLASSES && s->campaign.member) return 0;
    if (s->campaign.ui==BTP_MENU_BROKER || s->campaign.ui==BTP_MENU_BROKER_CONFIRM || s->campaign.ui==BTP_MENU_BROKER_RESULT) {
        unsigned indices[BTP_ROSTER_MAX];
        unsigned listed=btp_events_catalogue(s,r,s->menu.broker_class,count,indices);
        if (!btp_broker_available(s,r) || s->menu.map_x!=listed || s->campaign.member>
            (listed+1u>BTP_BROKER_ROWS ? listed+1u-BTP_BROKER_ROWS : 0u)) return 0;
        if (!listed) {
            if (s->campaign.ui!=BTP_MENU_BROKER || s->menu.map_y) return 0;
        } else {
            unsigned item=0;while (item<listed && indices[item]!=s->menu.map_y) ++item;
            if (item==listed) return 0;
            /* Old flat saves did not keep map_y in sync while browsing. New
               category saves do: preserve this identity through pack growth. */
            if (s->menu.broker_class && s->campaign.ui==BTP_MENU_BROKER &&
                s->campaign.member+s->campaign.selected<listed &&
                indices[s->campaign.member+s->campaign.selected]!=s->menu.map_y) return 0;
        }
    }
    if (!record_valid(s->campaign.mech,&r->roster,count) || !record_valid(s->campaign.checkpoint_mech,&r->roster,count)) return 0;
    for (unsigned i=0;i<3;++i) if (!record_valid(s->party.mechs[i],&r->roster,count) || !record_valid(s->party_checkpoint.mechs[i],&r->roster,count)) return 0;
    for (unsigned i=0;i<4;++i) if (!record_valid(s->yard.mechs[i],&r->roster,count)) return 0;
    for (unsigned i=0;i<BTP_COMBAT_UNITS;++i) if (!s->combat.unit[i].infantry && !record_valid(s->combat.unit[i].record,&r->roster,count)) return 0;
    return 1;
}
int btp_roster_state_valid(const BtpState *s,const BtpResources *r)
{
    return btp_roster_state_prefix_valid(s,r,r->roster.count);
}
