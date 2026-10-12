#include "core/story.h"
#include "core/party.h"
#include "core/service.h"
#include "core/menu.h"
#include <string.h>
int btp_later_native(BtpState *s,const BtpResources *r)
{
    unsigned kind=btp_building_kind(r,s),action=s->script.native_action;
    if (action==36 || action==38) {
        unsigned id=action==36 ? s->story_flags[37]<8 ? s->party.people[s->story_flags[37]][0] : 255u : s->party.next_id;
        if (id>=10) return 0;
        s->script.has_name=1;s->script.name_id=(uint8_t)id;s->script.name_after=s->script.text_count;
    } else if (kind==13 && action==37) {
        btp_party_init(s);s->party.people[0][0]=255;
    } else if (kind==13 && action==39) {
        if (s->menu.from_story==2) s->menu.from_story=0;
        else { btp_menu_open(s);s->campaign.ui=BTP_MENU_ALLOCATE;s->menu.from_story=1;return 1; }
    } else if (kind!=9) return 0;
    else if (action==13) { btp_service_begin(s,r);return 1; }
    else if (action==21 || action==22) {
        unsigned member=s->party.selected;if (member>=8 || s->party.people[member][0]==255) return 0;
        uint8_t *p=s->party.people[member];
        if (action==22) s->story_flags[15]=p[16]&2u;
        if (action==21) {
            s->story_flags[14]=0;
            if (s->credits>=500) { s->credits-=500;++p[10];p[16]|=2u;s->story_flags[14]=1; }
        }
    } else if (action==23) {
        s->story_flags[25]=0;
        for (unsigned i=0;i<8;++i) if (s->party.people[i][0]!=255 && s->party.people[i][15]!=10u*s->party.people[i][1]) s->story_flags[25]=1;
    } else if (action==24) {
        unsigned skill=s->story_flags[26];if (skill>7) return 0;
        if (!skill) (void)btp_party_heal(s,r,0);
        else if (s->credits>=r->combat.medical_prices[skill]) { s->credits-=r->combat.medical_prices[skill];(void)btp_party_heal(s,r,skill); }
        else s->credits+=25;
    } else if (action==25) s->party.medical_kit=1;
    else if (action==26) s->party.advanced_kit=1;
    else return 0;
    btp_script_native_return(&s->script,btp_state_bld(r,s),s->story_flags);return 1;
}
