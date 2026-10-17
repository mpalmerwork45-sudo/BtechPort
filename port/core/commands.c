#include "core/commands.h"
#include "core/party.h"
#include <string.h>

int btp_party_has_person(const BtpState *s, unsigned identity)
{
    for (unsigned i=0;i<8;++i)
        if (s->party.people[i][0]!=255 && s->party.people[i][0]==identity) return 1;
    return 0;
}
int btp_party_has_skill(const BtpState *s, unsigned skill, unsigned minimum)
{
    if (skill>6) return 0;
    for (unsigned i=0;i<8;++i)
        if (s->party.people[i][0]!=255 && s->party.people[i][4+skill]>=minimum) return 1;
    return 0;
}
int btp_try_spend_credits(BtpState *s, uint32_t amount)
{
    if (s->credits<amount) return 0;
    s->credits-=amount;
    return 1;
}
int btp_grant_credits(BtpState *s,uint32_t amount)
{
    if (s->credits>UINT32_MAX-amount) return 0;
    s->credits+=amount;return 1;
}
int btp_recruit_person(BtpState *s,const uint8_t person[17])
{
    btp_party_init(s);
    if (btp_party_has_person(s,person[0])) return 0;
    for (unsigned i=1;i<8;++i) if (s->party.people[i][0]==255) {
        memcpy(s->party.people[i],person,17);s->party.x[i]=s->campaign.world_x;s->party.y[i]=s->campaign.world_y;
        return (int)i+1;
    }
    return 0;
}
