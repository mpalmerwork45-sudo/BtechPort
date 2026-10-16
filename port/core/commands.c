#include "core/commands.h"

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
