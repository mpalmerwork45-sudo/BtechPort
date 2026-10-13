#include "core/spy.h"
#include "core/party.h"
#include "core/combat.h"
#include "core/campaign.h"
#include <string.h>

int btp_spy_unit(const BtpState *s,unsigned unit)
{
    if (!s->story_flags[39] || s->story_flags[37]>=8 || unit>=s->combat.count) return 0;
    unsigned spy=s->story_flags[37],id=btp_combat_id(&s->combat,unit);
    const BtpCombatUnit *u=&s->combat.unit[unit];
    return id==4u+spy || (id<4 && (u->record[121]==spy || u->record[122]==spy));
}
unsigned btp_spy_outcome(const BtpState *s)
{
    unsigned spy=s->story_flags[37];if (spy>=8) return 0;
    unsigned bay=s->party.people[spy][12];if (bay>=4) return 1;
    const uint8_t *mech=btp_party_mech((BtpState *)s,bay);
    if (mech[121]!=spy) return 5;
    unsigned rider=mech[122];
    return rider>=8 ? 2u : s->party.people[rider][8] ? 4u : 3u;
}
void btp_spy_resolve(BtpState *s)
{
    if (!s->story_flags[39] || !s->spy_discovered || s->story_flags[37]>=8) return;
    unsigned spy=s->story_flags[37],bay=s->party.people[spy][12];
    /* Executed 103B:08A0..0CDB: the original has separate on-foot,
       pilot and passenger outcomes. An armed rider can preserve the mech;
       an unarmed rider ejects when it must be destroyed. */
    if (bay<4) {
        uint8_t *mech=btp_party_mech(s,bay);
        if (mech[121]==spy) {
            unsigned rider=mech[122];
            if (rider<8 && s->party.people[rider][8]) { mech[121]=(uint8_t)rider;mech[122]=255; }
            else {
                mech[0]=255;s->party.mech_types[bay]=255;
                if (rider<8) s->party.people[rider][12]=8;
            }
        } else mech[122]=255;
    }
    s->party.people[spy][0]=255;s->story_flags[39]=0;s->story_flags[36]=127;
    s->spy_discovered=0;
}
int btp_spy_begin(BtpState *s)
{
    if (!s->campaign.encounter || !s->story_flags[39] || !s->spy_discovered || s->story_flags[37]>=8) return 0;
    s->combat.phase=BTP_COMBAT_SPY;s->combat.notice=(uint8_t)(9u+btp_spy_outcome(s));
    s->combat.notice_return=0;s->combat.flash=0;return 1;
}
void btp_spy_combat_finish(BtpState *s)
{
    unsigned spy=s->story_flags[37],bay=s->party.people[spy][12];BtpCombatState *c=&s->combat;
    if (bay<4) {
        unsigned vehicle=btp_combat_target(c,bay);
        /* The DOS branch edits the shared live vehicle. Carry current damage
           and ammunition into the seat change instead of restoring the
           party's pre-battle copy over the combat record. */
        if (vehicle<c->count) memcpy(btp_party_mech(s,bay),c->unit[vehicle].record,125);
    }
    btp_spy_resolve(s);
    unsigned person=btp_combat_target(c,4u+spy);
    if (person<c->count) btp_campaign_destroy(s,person);
    if (bay<4) {
        unsigned vehicle=btp_combat_target(c,bay);
        if (vehicle<c->count) {
            if (btp_party_mech(s,bay)[0]==255) {
                /* Keep the wreck's original crew until the existing ejection
                   pass has placed the surviving rider on the ground. */
                btp_campaign_destroy(s,vehicle);
            } else memcpy(c->unit[vehicle].record,btp_party_mech(s,bay),125);
        }
    }
    c->notice=c->notice_return=0;c->phase=BTP_COMBAT_ROUND;c->step=12;
}
