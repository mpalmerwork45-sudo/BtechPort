#include "core/service.h"
#include "core/party.h"
#include "core/combat.h"
#include "core/npc.h"
#include <string.h>
#include <stdio.h>
unsigned btp_mech_repair(BtpState *s,unsigned slot,unsigned kind,unsigned item)
{
    uint8_t *m=btp_party_mech(s,slot);if (!m) return 0;unsigned changed=0;
    if (kind<2) {
        unsigned first=kind ? 28u : 17u,end=kind ? 36u : 28u,cost=kind ? 9u : 4u;
        for (unsigned i=first;i<end;++i) while (m[i]<m[i+69] && s->credits>=cost) { ++m[i];s->credits-=cost;++changed; }
    } else if (kind==2 && item>=16 && item<=34) {
        unsigned cost=item==34 ? 800u : 300u;
        if (s->credits<cost) return 0;
        for (unsigned i=51;i<86;++i) if (m[i]==(item|128u)) {
            m[i]&=127u;++changed;if (item==34) break;
        }
        if (changed) s->credits-=cost;
    } else if (kind==3 && (m[36]!=m[105] || m[37]!=m[106]) && s->credits>=200) {
        m[36]=m[105];m[37]=m[106];s->credits-=200;changed=1;
    }
    return changed;
}
unsigned btp_mech_reload(BtpState *s,const BtpResources *r,unsigned slot,unsigned bin,unsigned amount)
{
    uint8_t *m=btp_party_mech(s,slot);if (!m || bin>=10 || m[39+bin]==255 || m[39+bin]>m[107+bin]) return 0;
    unsigned w=0,count=0,cost;
    for (unsigned i=51;i<86;++i) {
        unsigned component=m[i]&127u;
        if (component>=16 && component<=32) {
            if (m[i]&128u) return 0;
            if (count++==bin) w=component;
        }
    }
    if (w==24) cost=2;else if (w>=26 && w<=32) cost=r->combat.ammo_prices[w-26];else return 0;
    unsigned missing=(unsigned)m[107+bin]-m[39+bin];if (amount>missing) amount=missing;
    unsigned n=0;if (!cost) return 0;
    while (n<amount && s->credits>=cost) { s->credits-=cost;++m[39+bin];++n; }
    return n;
}
int btp_mech_refit(BtpState *s,const BtpResources *r,unsigned slot)
{
    uint8_t *m=btp_party_mech(s,slot);if (!m || m[123]>3 || m[124]==3) return 0;
    unsigned choice=m[123]+(m[124]==1 ? 4u : 0u),cost=r->combat.refit_prices[choice];
    if (!cost || s->credits<cost) return 0;
    s->credits-=cost;
    switch (choice) {
    case 0:m[65]=m[51]=17;m[108]=m[107]=m[40]=m[39]=255;m[124]=1;break;
    case 1:m[79]=17;m[108]=m[40]=255;memcpy(m+17,r->combat.loans[0]+17,11);memcpy(m+86,r->combat.loans[0]+86,11);m[124]=1;break;
    case 2:m[67]=m[66]=m[52]=m[51]=16;memset(m+107,255,5);memset(m+39,255,5);m[124]=1;break;
    case 3:m[74]=m[65]=17;m[42]=m[41];m[110]=m[109];m[109]=m[108]=m[41]=m[40]=255;
        memcpy(m+17,r->combat.commando_armour,11);memcpy(m+86,r->combat.commando_armour,11);m[124]=1;break;
    case 4:m[49]=7;m[117]=0;m[73]=m[59]=16;m[111]=m[110]=m[43]=m[42]=255;m[124]|=2;break;
    case 5:m[50]=0;m[83]=m[51]=m[85]=17;memset(m+109,255,3);memset(m+41,255,3);m[124]|=2;break;
    case 6:m[50]=0;memcpy(m+17,r->combat.loans[0]+17,11);memcpy(m+86,r->combat.loans[0]+17,11);
        m[84]=m[83]=17;m[113]=m[112]=m[45]=m[44]=255;m[124]|=2;break;
    case 7:memset(m+79,16,6);m[85]=17;memset(m+107,255,10);memset(m+39,255,10);m[124]|=2;break;
    default:return 0;
    }
    return 1;
}
static void finish(BtpState *s,const BtpResources *r)
{
    s->service=(BtpServiceState){0};
    if (s->script.status==BTP_SCRIPT_RECRUIT) btp_script_condition_return(&s->script,btp_state_bld(r,s),s->story_flags,0);
    else btp_script_native_return(&s->script,btp_state_bld(r,s),s->story_flags);
}
void btp_service_begin(BtpState *s,const BtpResources *r)
{
    (void)r;s->service=(BtpServiceState){.phase=1,.action=s->script.native_action};
    if (s->script.native_action==13) s->service.phase=7;
    if (s->script.native_action==20) { s->service.phase=3;s->service.mech=s->party.giver; }
}
void btp_service_input(BtpState *s,const BtpResources *r,BtpAction a)
{
    BtpServiceState *v=&s->service;
    if (v->phase==8) {
        if (a!=BTP_ACCEPT && a!=BTP_CANCEL) { (void)btp_rng_next(s->npc.rng);return; }
        if (!s->story_flags[38] && (btp_rng_next(s->npc.rng)&1u)) {
            s->story_flags[37]=v->mech;s->story_flags[38]=s->story_flags[39]=1;s->story_flags[36]=31;
        }
        finish(s,r);return;
    }
    unsigned count=v->phase==1 ? 5u : v->phase==2 ? v->action==18 ? 6u : 11u : v->phase==3 ? 2u : v->phase==6 ? 18u : v->phase==7 ? btp_party_count(&s->party) : 1u;
    if (a==BTP_UP) v->selected=(uint8_t)((v->selected+count-1u)%count);
    if (a==BTP_DOWN) v->selected=(uint8_t)((v->selected+1u)%count);
    if (a==BTP_CANCEL && v->phase!=5) { finish(s,r);return; }
    if (v->phase==5) {
        size_t n=strlen(v->input);
        if (a>=BTP_DIGIT_0 && a<=BTP_DIGIT_9 && n<7) {
            if (v->input[0]=='0') { memset(v->input,0,sizeof v->input);n=0; }
            v->input[n]=(char)('0'+a-BTP_DIGIT_0);v->input[n+1]=0;
        }
        if (a==BTP_CANCEL && n) v->input[n-1]=0;
        if (a==BTP_CLEAR_INPUT) { memset(v->input,0,sizeof v->input);v->input[0]='0'; }
    }
    if (a!=BTP_ACCEPT) return;
    if (v->phase==7) {
        unsigned slot=btp_party_slot(&s->party,v->selected);
        if (slot>=8) return;
        s->party.selected=(uint8_t)slot;s->story_flags[14]=(uint8_t)slot;finish(s,r);return;
    }
    if (v->phase==1) {
        if (v->selected==4) { finish(s,r);return; }
        if (s->party.mech_types[v->selected]==255) return;
        v->mech=v->selected;v->selected=0;
        if (v->action==19) {
            uint8_t *m=btp_party_mech(s,v->mech);s->story_flags[18]=(uint8_t)(m[124]!=3);
            s->story_flags[17]=(uint8_t)(m[123]>3 ? 8 : m[123]+(m[124]==1 ? 4u : 0u));
            s->party.giver=v->mech;finish(s,r);return;
        }
        if (v->action==20) v->phase=3;else v->phase=2;return;
    }
    if (v->phase==2) {
        if (v->selected==(v->action==18 ? 5u : 10u)) { finish(s,r);return; }
        v->kind=v->selected;v->item=v->selected;v->selected=0;
        if (v->action==18 && v->kind==3) { v->phase=6;return; }
        v->phase=(uint8_t)(v->action==44 ? 5 : 3);if (v->phase==5) v->input[0]='0';return;
    }
    if (v->phase==6) {
        if (v->selected==17) { v->phase=2;v->selected=0;return; }
        v->item=(uint8_t)(16+v->selected);v->phase=3;v->selected=0;return;
    }
    if (v->phase==3 && v->selected) {
        if (v->action==20) { finish(s,r);return; }
        v->phase=2;v->selected=0;return;
    }
    if (v->phase==3 || v->phase==5) {
        unsigned changed=0;
        if (v->action==18) {
            if (v->kind==2) { unsigned n;do { n=btp_mech_repair(s,v->mech,2,34);changed+=n; } while (n); }
            else if (v->kind==3) changed=btp_mech_repair(s,v->mech,2,v->item);
            else changed=btp_mech_repair(s,v->mech,v->kind==4 ? 3 : v->kind,0);
        } else if (v->action==20) changed=(unsigned)btp_mech_refit(s,r,v->mech);
        else if (v->action==44) {
            unsigned amount=0;for (unsigned i=0;v->input[i];++i) amount=amount*10u+(unsigned)(v->input[i]-'0');
            changed=btp_mech_reload(s,r,v->mech,v->item,amount);
        }
        v->amount=(uint16_t)changed;v->outcome=(uint8_t)(changed!=0);v->phase=4;v->selected=0;return;
    }
    if (v->phase==4) {
        if (v->action==20) { finish(s,r);return; }
        v->phase=2;v->selected=0;memset(v->input,0,8);
    }
}
int btp_service_valid(const BtpState *s)
{
    const BtpServiceState *v=&s->service;
    if (!v->phase) return !v->action && !v->mech && !v->selected && !v->kind && !v->item && !v->outcome && !v->amount && !v->input[0];
    if (v->phase==8) return v->action==0xe9 && v->mech<8 && !v->selected && v->kind<7 && !v->item && !v->outcome && !v->amount && !v->input[0] && s->mode==BTP_BUILDING && s->script.status==BTP_SCRIPT_RECRUIT && (s->campaign.building==5 || s->campaign.building==9 || s->campaign.building==13);
    if (v->phase>7 || (v->action!=13 && v->action!=18 && v->action!=19 && v->action!=20 && v->action!=44) || v->mech>3 || v->selected>17 || v->kind>9 || v->item>32 || v->outcome>1 || s->mode!=BTP_BUILDING || s->script.status!=BTP_SCRIPT_NATIVE || (s->campaign.building!=5 && !(s->campaign.building==9 && v->action==13)) || v->action!=s->script.native_action) return 0;
    unsigned n=0;while (n<8 && v->input[n]) { if (v->input[n]<'0' || v->input[n]>'9') return 0;++n; }return n<8;
}
