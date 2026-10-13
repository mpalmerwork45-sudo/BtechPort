#include "core/story.h"
#include "core/party.h"
#include "core/service.h"
#include "core/menu.h"
#include "core/npc.h"
#include <string.h>
void btp_laser_finish(BtpState *s,const BtpResources *r)
{
    /* 14D3:1432 caps each living character at (6 + random bit) times
       constitution after the laser-shop gifts. It never heals wounds. */
    for (unsigned i=0;i<8;++i) if (s->party.people[i][0]!=255) {
        unsigned health=(6u+(btp_rng_next(s->npc.rng)&1u))*s->party.people[i][1];
        if (s->party.people[i][15]>health) s->party.people[i][15]=(uint8_t)health;
    }
    s->weapon=s->party.people[0][11];s->service=(BtpServiceState){0};
    btp_script_native_return(&s->script,btp_state_bld(r,s),s->story_flags);
}
void btp_laser_next(BtpState *s,const BtpResources *r)
{
    BtpServiceState *v=&s->service;
    if (++v->mech>=v->kind) { btp_laser_finish(s,r);return; }
    v->item=(uint8_t)(13u-(btp_rng_next(s->npc.rng)&1u));v->phase=10;v->selected=0;v->outcome=0;
}
int btp_later_native(BtpState *s,const BtpResources *r)
{
    unsigned kind=btp_building_kind(r,s),action=s->script.native_action;
    if (kind==4 && (action==13 || action==32)) {
        if (!s->service.phase) btp_service_begin(s,r);
        return 1;
    }
    if (kind==4 && action==31) {
        /* 14D3:0EDA copies the selected person's armour ID to flag 31. */
        btp_party_init(s);s->story_flags[31]=s->party.people[s->party.selected][13];
    } else if (action==36 || action==38) {
        unsigned id=action==36 ? s->story_flags[37]<8 ? s->party.people[s->story_flags[37]][0] : 255u : s->party.next_id;
        if (id>=10) return 0;
        s->script.has_name=1;s->script.name_id=(uint8_t)id;s->script.name_after=s->script.text_count;
    } else if (kind==13 && action==37) {
        btp_party_init(s);s->party.people[0][0]=255;
    } else if ((kind==13 && action==39) || (kind==10 && action==27)) {
        if (s->menu.from_story==2) s->menu.from_story=0;
        else {
            /* 0C67:0002(1) clears both crew seats and all memberships before
               the post-theft allocator. Garage checkout passes 0 instead. */
            if (action==39) {
                for (unsigned i=0;i<4;++i) btp_party_mech(s,i)[121]=btp_party_mech(s,i)[122]=255;
                for (unsigned i=0;i<8;++i) s->party.people[i][12]=8;
                s->campaign.mounted=0;
            }
            btp_menu_open(s);s->campaign.ui=BTP_MENU_ALLOCATE;s->menu.from_story=1;return 1;
        }
    } else if (kind==14 && action==47) {
        /* 14D3:174E is the mayor-house chow aftermath: the meal reduces
           Jason's health by four only while it exceeds five. Preserve this
           original effect even though the menu describes eating a meal. */
        if (s->party.people[0][15]>5) s->party.people[0][15]-=4;
    } else if (kind==15 && action==41) {
        if (s->service.phase) return 1;
        /* 14D3:140D, reached by WEAPON2.BLD after payment. With friends
           the original hands out one laser per person through 07DC:15E6's
           recipient/swap menu. Alone it asks before replacing Jason's gun. */
        unsigned n=btp_party_count(&s->party);
        s->service=(BtpServiceState){.phase=(uint8_t)(n>1 ? 10 : 9),.action=41,.kind=(uint8_t)n,.item=13};
        return 1;
    } else if (kind==16 && action==42) {
        /* 14D3:1515 places the eight outdoor slots at the cinema exit and
           records room/counter 0x77 with each slot's ID, then advances south. */
        unsigned x=s->campaign.world_x,y=s->campaign.world_y;
        unsigned px=(x/128u)*256u+(x&127u),py=(y/128u)*4096u+(y&127u);
        for (unsigned i=0;i<8;++i) {
            s->npc_pairs[i][0]=0x77;s->npc_pairs[i][1]=(uint8_t)i;
            /* The same native action moves the live outdoor slots. Actors
               still waiting inside remain hidden until their timer expires. */
            if (s->npc.enabled==2) s->npc.actor[i]=(BtpNpc){i ? 0 : (uint16_t)px,i ? 0 : (uint16_t)py,0};
            if (s->original.valid) {
                unsigned at=1u+0xd390u-0xc614u+26u*i;
                s->original.bytes[at]=(uint8_t)px;s->original.bytes[at+1]=(uint8_t)(px>>8);
                s->original.bytes[at+2]=(uint8_t)py;s->original.bytes[at+3]=(uint8_t)(py>>8);
            }
        }
        ++s->campaign.world_y;++s->y_half;
        s->script.position_x=(uint16_t)px;s->script.position_y=(uint16_t)(py+1u);
    } else if (kind!=9) return 0;
    else if (action==13) {
        /* Resume the existing selector on arrows; reopening it here would
           reset every choice to Jason before the next input. */
        if (!s->service.phase) btp_service_begin(s,r);
        return 1;
    }
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
        if (s->service.phase==12) return 1;
        unsigned skill=s->story_flags[26];if (skill>7) return 0;
        if (!skill) btp_service_heal(s,r,0,0);
        else if (s->credits>=r->combat.medical_prices[skill]) { s->credits-=r->combat.medical_prices[skill];btp_service_heal(s,r,skill,0); }
        else s->credits+=25;
        if (s->service.phase) return 1;
    } else if (action==25) s->party.medical_kit=1;
    else if (action==26) s->party.advanced_kit=1;
    else return 0;
    btp_script_native_return(&s->script,btp_state_bld(r,s),s->story_flags);return 1;
}
