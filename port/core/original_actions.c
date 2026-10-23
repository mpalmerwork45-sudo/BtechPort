#include "core/original_actions.h"
#include "core/commands.h"
#include "core/talk.h"
#include "core/bank.h"
#include "core/school.h"
#include "core/training.h"
#include "core/party.h"
#include "core/campaign.h"
#include "core/service.h"
#include "core/audio.h"
#include "core/menu.h"
#include "core/story.h"
#include "core/yard.h"
#include "core/cache.h"
#include "core/shop.h"
#include <string.h>

void btp_original_checkpoint(BtpState *s)
{
    memcpy(s->story_checkpoint,s->story_flags,BTP_STORY_BYTES); s->checkpoint_valid = 1;
    s->checkpoint_talk_result = s->talk_result; s->checkpoint_credits = s->credits;
    s->checkpoint_allowance_cap = s->allowance_cap; s->checkpoint_weapon = s->weapon;
    s->checkpoint_armor = s->armor; s->checkpoint_armor_points = s->armor_points;
    memcpy(s->checkpoint_investments,s->investments,sizeof s->investments);
    memcpy(s->checkpoint_skills,s->skills,sizeof s->skills);
    memcpy(s->checkpoint_mech_skills,s->mech_skills,sizeof s->mech_skills);
    s->checkpoint_technician=s->technician;s->checkpoint_apprentice=s->apprentice;
    s->campaign.checkpoint_owned=s->campaign.owned;
    memcpy(s->campaign.checkpoint_mech,s->campaign.mech,125);
    s->party_checkpoint=s->party;
}
void btp_original_native_input(BtpState *s,const BtpResources *r,BtpAction a)
{
    if (s->cache.active && s->script.native_action==BTP_NATIVE_PHOENIX) {
        if (a==BTP_ACCEPT || a==BTP_CANCEL || a==BTP_OPEN_MENU) {
            s->cache.phase=BTP_CACHE_WALK;btp_script_native_return(&s->script,btp_state_bld(r,s),s->story_flags);
        }
    } else if (s->script.native_action == BTP_NATIVE_TALK) btp_talk_input(s,r,a);
    else if (s->service.phase) btp_service_input(s,r,a);
    else if (s->bank.phase) btp_bank_input(s,r,a);
}

void btp_original_services(BtpState *s,const BtpResources *r)
{
    /* Preserve the sixteen-call budget and held states exactly. This adapter
       owns legacy PCs/native IDs; the game loop still owns tick advancement,
       animation dispatch, position publication and final script recovery. */
    for (unsigned service = 0; service < 16 && (s->script.status == BTP_SCRIPT_NATIVE || s->script.status>=BTP_SCRIPT_MONEY); ++service) {
        if (s->script.status==BTP_SCRIPT_RECRUIT) {
            if (s->service.phase==8) break;
            unsigned skill=s->script.money_amount;
            if ((btp_building_kind(r,s)!=5 && btp_building_kind(r,s)!=9 && btp_building_kind(r,s)!=13) || skill>6) {
                s->script.status=BTP_SCRIPT_ERROR;s->script.error=BTP_SCRIPT_NATIVE_CONTEXT;break;
            }
            unsigned recruited=(unsigned)btp_party_recruit_resources(s,r,skill);
            if (!recruited) {
                /* The original full-party scan exits without a new agent or
                   a spy coin. It does not fault the building interpreter. */
                btp_script_condition_return(&s->script,btp_state_bld(r,s),s->story_flags,0);continue;
            }
            unsigned member=recruited-1u;
            s->service=(BtpServiceState){.phase=8,.action=0xe9,.mech=(uint8_t)member,.kind=(uint8_t)skill};
            s->script.money_amount=0;break;
        }
        if (s->script.status==BTP_SCRIPT_CONDITION) {
            unsigned index=s->script.money_amount&255u,threshold=s->script.money_amount>>8;int yes=s->script.money_kind==0xe8;
            if (s->script.money_kind==0xe8) yes=!btp_party_has_person(s,index);
            if (s->script.money_kind==0xed) yes=btp_party_has_skill(s,index,threshold);
            if (s->script.money_kind==0xeb) yes=s->party.advanced_kit!=0;
            if (s->script.money_kind==0xec) yes=s->party.medical_kit!=0;
            btp_script_condition_return(&s->script,btp_state_bld(r,s),s->story_flags,yes);continue;
        }
        if (s->script.status==BTP_SCRIPT_EFFECT) {
            /* Original E4 calls the blocking 17C5 sound routine. Suspend the
               BLD until that clip ends; adjacent effects must not accumulate
               behind the next movie, dialogue, or building exit. */
            if (s->script.money_amount) { btp_audio_effect(s,s->script.money_amount);s->script.money_amount=0; }
            if (s->audio.sound_count) break;
            s->script.status=BTP_SCRIPT_NATIVE;btp_script_native_return(&s->script,btp_state_bld(r,s),s->story_flags);continue;
        }
        if (s->script.status==BTP_SCRIPT_MONEY) {
            btp_script_money_return(&s->script,btp_state_bld(r,s),s->story_flags,&s->credits);continue;
        }
        if (s->script.native_action == BTP_NATIVE_TALK) {
            if (!s->checkpoint_valid) btp_original_checkpoint(s);
            if (!s->talk.phase) btp_talk_begin(s,r);
            break;
        }
        if (s->cache.active && s->script.native_action==BTP_NATIVE_PHOENIX && btp_building_kind(r,s)==22) { s->cache.phase=BTP_CACHE_PHOENIX;break; }
        if ((s->script.native_action >= BTP_NATIVE_MISSION && s->script.native_action <= BTP_NATIVE_TRAINING_RETURN) || s->script.native_action==BTP_NATIVE_CADET_RETURN) {
            btp_training_native(s,r);
            if (s->mode == BTP_MISSION) break;
        } else if (s->script.native_action == BTP_NATIVE_CLASS_PRICES || s->script.native_action == BTP_NATIVE_CLASS_TAKE) btp_school_native(s,r);
        else if (s->script.native_action >= BTP_NATIVE_ACCOUNTS && s->script.native_action <= BTP_NATIVE_SELL_SHARES) {
            if (!s->bank.phase) btp_bank_native(s,r);
            if (s->script.status == BTP_SCRIPT_NATIVE) break;
        } else if (s->story_flags[4] && btp_building_kind(r,s)==5 &&
            (s->script.native_action==BTP_NATIVE_SERVICE_SELECT || s->script.native_action==BTP_NATIVE_REPAIR || s->script.native_action==BTP_NATIVE_REFIT || s->script.native_action==BTP_NATIVE_TECH_PAYMENT || s->script.native_action==BTP_NATIVE_AMMO)) {
            if (!s->service.phase) btp_service_begin(s,r);
            break;
        } else if (s->script.native_action==BTP_NATIVE_REX && btp_building_kind(r,s)==11 && s->story_flags[4]) {
            btp_campaign_rex(s,r);break;
        } else if (s->script.native_action==BTP_NATIVE_PARTY_COUNT && s->story_flags[4]) {
            s->story_flags[14]=(uint8_t)(btp_party_count(&s->party)-1u);
            btp_script_native_return(&s->script,btp_state_bld(r,s),s->story_flags);
        } else if (!btp_yard_native(s,r) && !btp_later_native(s,r)) btp_shop_native(s,r);
        if (s->mode==BTP_ACTIONS || s->mode==BTP_YARD || s->mode==BTP_ENCOUNTER || s->service.phase) break;
    }
    if (s->script.status == BTP_SCRIPT_NATIVE && s->script.native_action != BTP_NATIVE_TALK && !s->bank.phase && !s->service.phase && s->mode != BTP_MISSION && s->mode!=BTP_ENCOUNTER && s->mode!=BTP_YARD && !s->menu.from_story && !(s->cache.active && s->script.native_action==BTP_NATIVE_PHOENIX)) {
        s->script.status = BTP_SCRIPT_ERROR; s->script.error = BTP_SCRIPT_BUDGET;
        s->script.fault_pc = s->script.pc;
    }
}
