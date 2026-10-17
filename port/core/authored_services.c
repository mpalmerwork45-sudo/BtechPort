#include "core/authored_services.h"
#include "core/party.h"
#include "core/roster_game.h"
#include <string.h>

unsigned btp_authored_service(BtpState *s,const BtpResources *r,const BtpEventNode *e)
{
    if (!s->event.enabled || !s->party.enabled || e->op<BTP_EVENT_REPAIR || e->op>BTP_EVENT_SALVAGE) return 1;
    /* Stage only the affected records. Failed/no-op services never consume
       money or mutate crew, ammunition or unrelated campaign state. */
    uint8_t mechs[4][125],people[8][17];unsigned changed=0,eligible=0;
    for (unsigned i=0;i<4;++i) memcpy(mechs[i],btp_party_mech(s,i),125);
    memcpy(people,s->party.people,sizeof people);
    unsigned salvage_bay=4;
    if (e->op==BTP_EVENT_SALVAGE) {
        if (e->x>=r->roster.count) return 1;
        for (unsigned i=0;i<4;++i) if (!btp_broker_owned(s,i)) { salvage_bay=i;break; }
        if (salvage_bay==4) return 1;
        /* The author chooses a recoverable chassis on a victory branch.
           Recovery delivers half armour, empty bins and no assigned crew. */
        uint8_t *m=mechs[salvage_bay];memcpy(m,r->roster.mechs[e->x].record,125);
        for (unsigned i=17;i<28;++i) m[i]=(uint8_t)(m[i]/2u);
        for (unsigned i=39;i<49;++i) if (m[i]!=255) m[i]=0;
        m[121]=m[122]=255;changed=eligible=1;
    } else if (e->op==BTP_EVENT_HEAL) {
        for (unsigned i=0;i<8;++i) if ((!e->argument || e->argument==i+1u) && people[i][0]!=255 && people[i][15]) {
            ++eligible;unsigned maximum=10u*people[i][1];
            if (people[i][15]<maximum) { people[i][15]=(uint8_t)maximum;++changed; }
        }
    } else for (unsigned i=0;i<4;++i) {
        uint8_t *m=mechs[i];
        if ((e->argument && e->argument!=i+1u) || !btp_broker_owned(s,i) || m[0]==255) continue;
        ++eligible;uint8_t before[125];memcpy(before,m,125);
        if (e->op==BTP_EVENT_REPAIR) {
            memcpy(m+17,m+86,19);m[36]=m[105];m[37]=m[106];
            for (unsigned k=51;k<86;++k) m[k]&=127u;
            m[117]=m[118]=m[119]=0;
        } else for (unsigned k=0;k<10;++k) if (m[39+k]!=255) m[39+k]=m[107+k];
        changed+=memcmp(before,m,125)!=0;
    }
    if (!eligible) return 1;
    if (!changed) return 2;
    if (s->credits<e->value) return 1;
    for (unsigned i=0;i<4;++i) memcpy(btp_party_mech(s,i),mechs[i],125);
    memcpy(s->party.people,people,sizeof people);s->credits-=e->value;
    if (salvage_bay<4) { s->party.mech_types[salvage_bay]=mechs[salvage_bay][0];s->campaign.owned=s->story_flags[24]=1; }
    return 0;
}
