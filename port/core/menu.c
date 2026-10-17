#include "core/menu.h"
#include "core/npc.h"
#include "core/service.h"
#include "core/party.h"
#include "core/world.h"
#include "core/roster_game.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
unsigned btp_menu_mech_count(const BtpState *s)
{
    if (!s->campaign.owned) return 0;
    unsigned n=0;
    for (unsigned i=0;i<4;++i) {
        const uint8_t *m=i ? s->party.mechs[i-1] : s->campaign.mech;
        if (m[0]!=255 && (!i || s->party.mech_types[i]!=255)) ++n;
    }
    return n;
}
unsigned btp_menu_mech_slot(const BtpState *s,unsigned ordinal)
{
    for (unsigned i=0;i<4;++i) if (btp_party_mech((BtpState *)s,i)[0]!=255) {
        if (!ordinal) return i;
        --ordinal;
    }
    return 4;
}
static unsigned root_item(const BtpState *s,unsigned item)
{
    return item+(unsigned)(!btp_menu_mech_count(s) && item>=2);
}
unsigned btp_actions_count(const BtpState *s)
{
    switch (s->campaign.ui) {
    case BTP_MENU_UPDATED_ROOT:return btp_menu_mech_count(s) ? 9u : 8u;
    case BTP_MENU_BROKER: {
        unsigned first=s->campaign.member,n=s->menu.map_x>=first ? s->menu.map_x+1u-first : 0u;
        return n>BTP_BROKER_ROWS ? BTP_BROKER_ROWS : n;
    }
    case BTP_MENU_BROKER_CONFIRM:case BTP_MENU_BROKER_SELL_CONFIRM:return 2;
    case BTP_MENU_BROKER_HUB:return 3;
    case BTP_MENU_BROKER_CLASSES:return 5;
    case BTP_MENU_BROKER_SELL:return btp_broker_count(s)+1u;
    case BTP_MENU_ROOT:return btp_menu_mech_count(s) ? 8u : 7u;
    case BTP_MENU_ALLOCATE:return btp_party_count(&s->party)+1u;
    case BTP_MENU_CREW:return btp_menu_mech_count(s)+1u;
    case BTP_MENU_INSPECT_KIND:return 2;
    case BTP_MENU_MECH_PICK:return btp_menu_mech_count(s);
    case BTP_MENU_SEAT:case BTP_MENU_ABANDON:return 2;
    case BTP_MENU_TRANSFER:return 3;
    case BTP_MENU_RECIPIENT:return btp_party_count(&s->party)+1u;
    case BTP_MENU_PERSON:case BTP_MENU_EQUIPMENT:case BTP_MENU_HEAL:return s->party.enabled ? btp_party_count(&s->party) : 1u;
    case BTP_MENU_SETTINGS:return 6;
    case BTP_MENU_UPDATED_SETTINGS:return 7;
    case BTP_MENU_COMBAT_RULES:return 3;
    case BTP_MENU_STEPS:case BTP_MENU_OUTTAKES:return 3;
    case BTP_MENU_SPEED:return 6;
    case BTP_MENU_LOAD:case BTP_MENU_SAVE:return 7;
    case BTP_MENU_QUIT:return 2;
    default:return 1;
    }
}
const char *btp_actions_label(const BtpState *s,unsigned item)
{
    static const char *const root[]={"Return to game","Change game settings","Allocate men in 'Mechs",
        "Inspect Character","Heal Characters","Load Game","Save Game","Show Overhead Map"};
    static const char *const settings[]={"Change movement rate","Set combat speed","Turn Sound Off",
        "Set outtake frequency","Quit game","Cancel"};
    static const char *const steps[]={"One step","Two steps","Four steps"};
    static const char *const speed[]={"Fastest","Faster","Normal","Slower","Slowest","Keypress"};
    static const char *const frequency[]={"Very Frequently","Frequently","Infrequently"};
    static const char *const slots[]={"One","Two","Three","Four","Five","Six","Cancel"};
    if (item>=btp_actions_count(s)) return "";
    switch (s->campaign.ui) {
    case BTP_MENU_UPDATED_ROOT:
        if (item==btp_actions_count(s)-1u) return "Visit 'Mech broker";
        /* The original entries retain their wording and order. */
        return root[root_item(s,item)];
    case BTP_MENU_ROOT:return root[root_item(s,item)];
    case BTP_MENU_SETTINGS:return item==2 && !s->menu.sound ? "Turn Sound On" : settings[item];
    case BTP_MENU_UPDATED_SETTINGS:
        if (item==4) return s->combat_profile ? "Combat rules: Enhanced" : "Combat rules: Legacy";
        return item==2 && !s->menu.sound ? "Turn Sound On" : settings[item-(item>4)];
    case BTP_MENU_COMBAT_RULES:return item==0 ? "Enhanced" : item==1 ? "Legacy" : "Cancel";
    case BTP_MENU_BROKER_CLASSES:return item<4 ? btp_roster_class_name(item+1u) : "Back";
    case BTP_MENU_STEPS:return steps[item];
    case BTP_MENU_SPEED:return speed[item];
    case BTP_MENU_OUTTAKES:return frequency[item];
    case BTP_MENU_LOAD:case BTP_MENU_SAVE:return slots[item];
    case BTP_MENU_ALLOCATE:case BTP_MENU_RECIPIENT:return item==btp_party_count(&s->party) ? "Done" : btp_party_name(&s->party,btp_party_slot(&s->party,item));
    case BTP_MENU_CREW:case BTP_MENU_MECH_PICK: {
        if (item==btp_menu_mech_count(s)) return "None";
        unsigned slot=btp_menu_mech_slot(s,item);const uint8_t *m=btp_party_mech((BtpState *)s,slot);
        static char name[48];char model[16];memcpy(model,m,15);model[15]=0;
        /* 0C67:0B98 looks up the pilot slot directly in the name table,
           including its original slot/character-ID alias. */
        if (s->campaign.ui==BTP_MENU_MECH_PICK && m[121]<8) {
            snprintf(name,sizeof name,"%s's %s",btp_character_name(m[121]),model);
        } else snprintf(name,sizeof name,"%s",model);
        return name;
    }
    case BTP_MENU_INSPECT_KIND:return item ? "No" : "Yes";
    case BTP_MENU_SEAT:case BTP_MENU_ABANDON:return item ? "No" : "Yes";
    case BTP_MENU_TRANSFER:return item==0 ? "Give weapon" : item==1 ? "Give armour" : "Return to game";
    case BTP_MENU_QUIT:return item ? "No" : "Yes";
    default:return s->party.enabled ? btp_party_name(&s->party,btp_party_slot(&s->party,item)) : "Jason";
    }
}
void btp_menu_open(BtpState *s)
{
    if (s->mode==BTP_EXPLORE) btp_world_reveal(s);
    s->mode=BTP_ACTIONS;s->campaign.ui=BTP_MENU_ROOT;s->campaign.selected=0;s->menu.notice=0;
}
void btp_menu_close(BtpState *s)
{
    if (btp_broker_page(s->campaign.ui)) {
        s->campaign.building=0;s->entry_slot=0;s->script=(BtpScriptState){0};
    }
    if (s->service.phase==12 && s->service.action==48) s->service=(BtpServiceState){0};
    unsigned intro=s->menu.from_intro;s->menu.from_intro=0;
    s->campaign.ui=s->campaign.selected=s->campaign.member=0;s->menu.io=s->menu.notice=0;
    s->menu.broker_class=0;
    s->mode=(uint8_t)(intro ? BTP_BEGIN : s->menu.from_story ? BTP_BUILDING : s->cache.active ? BTP_CACHE : BTP_EXPLORE);
    if (s->menu.from_story) s->menu.from_story=2;
}
static void page(BtpState *s,unsigned phase,unsigned selected)
{
    s->campaign.ui=(uint8_t)phase;s->campaign.selected=(uint8_t)selected;s->menu.notice=0;
    if (phase==BTP_MENU_BROKER_HUB || phase==BTP_MENU_BROKER_CLASSES) {
        s->campaign.member=0;s->menu.broker_class=0;
    }
}
void btp_broker_select(BtpState *s,unsigned item)
{
    /* Scroll only when the cursor leaves the eight visible rows. Back is the
       final catalogue item, so Up/Down traverses every model without paging
       controls or intermediate Back rows interrupting the list. */
    unsigned total=s->menu.map_x+1u,first=s->campaign.member;
    if (item>=total) item=total-1u;
    unsigned last=total>BTP_BROKER_ROWS ? total-BTP_BROKER_ROWS : 0u;
    if (first>last) first=last;
    if (item<first) first=item;
    if (item>=first+BTP_BROKER_ROWS) first=item+1u-BTP_BROKER_ROWS;
    s->campaign.member=(uint8_t)first;s->campaign.selected=(uint8_t)(item-first);
}
void btp_broker_browse(BtpState *s,const BtpResources *r,unsigned item)
{
    unsigned indices[BTP_ROSTER_MAX];
    unsigned count=btp_roster_catalogue(&r->roster,s->menu.broker_class,r->roster.count,indices);
    s->menu.map_x=(uint16_t)count;btp_broker_select(s,item);
    item=s->campaign.member+s->campaign.selected;
    if (item<count) s->menu.map_y=(uint16_t)indices[item];
}
static void broker_return(BtpState *s,const BtpResources *r)
{
    unsigned indices[BTP_ROSTER_MAX],item=0;
    unsigned count=btp_roster_catalogue(&r->roster,s->menu.broker_class,r->roster.count,indices);
    while (item<count && indices[item]!=s->menu.map_y) ++item;
    page(s,BTP_MENU_BROKER,0);btp_broker_browse(s,r,item);
}
static void broker_back(BtpState *s)
{
    unsigned weight_class=s->menu.broker_class;
    page(s,weight_class ? BTP_MENU_BROKER_CLASSES : BTP_MENU_BROKER_HUB,weight_class ? weight_class-1u : 0u);
}
void btp_menu_person(const BtpState *s,unsigned member,uint8_t p[17])
{
    if (s->party.enabled) { memcpy(p,s->party.people[member&7u],17);return; }
    static const uint8_t jason[17]={0,8,9,7,0,0,0,0,1,0,0,0,8,0,0,80,0};
    memcpy(p,jason,17);memcpy(p+4,s->skills,3);memcpy(p+7,s->mech_skills,2);
    p[9]=s->technician;p[11]=s->weapon;p[13]=s->armor;p[14]=s->armor_points;p[16]=s->apprentice;
}
void btp_menu_input(BtpState *s,const BtpResources *r,BtpAction a)
{
    ++s->tick;BtpCampaignState *c=&s->campaign;if (s->menu.io) return;
    if (btp_broker_page(c->ui) && a==BTP_CANCEL) {
        if (c->ui==BTP_MENU_BROKER_HUB) btp_menu_close(s);
        else if (c->ui==BTP_MENU_BROKER_CONFIRM || c->ui==BTP_MENU_BROKER_RESULT) broker_return(s,r);
        else if (c->ui==BTP_MENU_BROKER) broker_back(s);
        else if (c->ui==BTP_MENU_BROKER_SELL_CONFIRM) page(s,BTP_MENU_BROKER_SELL,0);
        else page(s,BTP_MENU_BROKER_HUB,0);
        return;
    }
    if (c->ui==BTP_MENU_BROKER && (a==BTP_UP || a==BTP_DOWN || a==BTP_LEFT || a==BTP_RIGHT)) {
        unsigned total=s->menu.map_x+1u,item=c->member+c->selected;
        if (a==BTP_UP) item=item ? item-1u : total-1u;
        else if (a==BTP_DOWN) item=(item+1u)%total;
        else if (a==BTP_LEFT) item=item>BTP_BROKER_ROWS ? item-BTP_BROKER_ROWS : 0u;
        else item=item+BTP_BROKER_ROWS<total ? item+BTP_BROKER_ROWS : total-1u;
        btp_broker_browse(s,r,item);return;
    }
    if (c->ui>=BTP_MENU_UPDATED_ROOT && a==BTP_OPEN_MENU) a=BTP_ACCEPT;
    if (c->ui==BTP_MENU_INSPECT && (a==BTP_LEFT || a==BTP_RIGHT)) {
        uint8_t p[17];btp_menu_person(s,c->member,p);
        if (s->campaign.owned && p[12]<4 && btp_party_mech(s,p[12])[0]!=255) {
            c->member=p[12];page(s,BTP_MENU_MECH,0);
        }
        return;
    }
    if (c->ui==BTP_MENU_MECH) {
        if (a!=BTP_IDLE) btp_menu_close(s);
        return;
    }
    if (c->ui==BTP_MENU_INSPECT && s->party.enabled && btp_party_count(&s->party)>1 && (a==BTP_UP || a==BTP_DOWN)) { page(s,BTP_MENU_TRANSFER,0);return; }
    if (c->ui==BTP_MENU_MAP) {
        if (a==BTP_ACCEPT || a==BTP_CANCEL || a==BTP_OPEN_MENU) { btp_menu_close(s);return; }
        /* Original 0000:4553 uses RNG & 15 for each marker redraw. Advance
           on logical polls so a save/replay is independent of rendering FPS. */
        s->menu.notice=(uint8_t)(btp_rng_next(s->npc.rng)&15u);
        if (btp_action_moves(a)) {
            int x=(int)s->menu.map_x+256*btp_action_dx(a),y=(int)s->menu.map_y+256*btp_action_dy(a);
            s->menu.map_x=(uint16_t)(x<0 ? 0 : x>2047 ? 2047 : x);
            s->menu.map_y=(uint16_t)(y<0 ? 0 : y>2047 ? 2047 : y);
        }
        return;
    }
    unsigned count=btp_actions_count(s);
    if (a==BTP_UP || a==BTP_LEFT) c->selected=(uint8_t)((c->selected+count-1)%count);
    if (a==BTP_DOWN || a==BTP_RIGHT) c->selected=(uint8_t)((c->selected+1)%count);
    if (a==BTP_CANCEL || a==BTP_OPEN_MENU) { btp_menu_close(s);return; }
    if (a!=BTP_ACCEPT) return;
    unsigned item=c->selected;
    switch (c->ui) {
    case BTP_MENU_ROOT:case BTP_MENU_UPDATED_ROOT:
        switch (root_item(s,item)) {
        case 0:btp_menu_close(s);break;
        case 1:page(s,r->roster.count && r->combat_profile.fingerprint ? BTP_MENU_UPDATED_SETTINGS : BTP_MENU_SETTINGS,0);break;
        case 2:
            btp_party_init(s);
            if (btp_world_populated(r,s)) { page(s,BTP_MENU_MESSAGE,0);s->menu.notice=4; }
            else page(s,BTP_MENU_ALLOCATE,0);
            break;
        case 3:
            /* 0000:378D tests action 17 before selecting a character. */
            if (btp_menu_mech_count(s)) page(s,BTP_MENU_INSPECT_KIND,0);
            else if (btp_party_count(&s->party)>1) page(s,BTP_MENU_PERSON,btp_party_ordinal(&s->party,s->party.selected));
            else { c->member=0;page(s,BTP_MENU_INSPECT,0); }
            break;
        case 4:
            btp_service_heal(s,r,0,1);page(s,BTP_MENU_MESSAGE,0);s->menu.notice=3;break;
        case 5:page(s,BTP_MENU_LOAD,s->menu.slot);break;
        case 6:page(s,BTP_MENU_SAVE,s->menu.slot);break;
        case 7:
            s->menu.map_x=s->story_flags[4] ? c->world_x : (uint16_t)(1536+s->x_half);
            s->menu.map_y=s->story_flags[4] ? c->world_y : (uint16_t)(1536+s->y_half);
            page(s,BTP_MENU_MAP,0);break;
        }
        break;
    case BTP_MENU_BROKER_HUB:
        c->member=0;s->menu.map_x=(uint16_t)r->roster.count;s->menu.map_y=0;
        if (!item) page(s,BTP_MENU_BROKER_CLASSES,0);
        else if (item==1) page(s,BTP_MENU_BROKER_SELL,0);
        else btp_menu_close(s);
        break;
    case BTP_MENU_BROKER_CLASSES:
        if (item==4) page(s,BTP_MENU_BROKER_HUB,0);
        else {
            s->menu.broker_class=(uint8_t)(item+1u);s->menu.map_y=0;c->member=0;
            page(s,BTP_MENU_BROKER,0);btp_broker_browse(s,r,0);
        }
        break;
    case BTP_MENU_BROKER:
        if (c->member+item==s->menu.map_x) broker_back(s);
        else {
            btp_broker_browse(s,r,c->member+item);
            page(s,BTP_MENU_BROKER_CONFIRM,1);
        }
        break;
    case BTP_MENU_BROKER_CONFIRM:
        if (item) broker_return(s,r);
        else {
            unsigned outcome=btp_broker_buy(s,r,s->menu.map_y);
            page(s,BTP_MENU_BROKER_RESULT,0);s->menu.notice=(uint8_t)outcome;
        }
        break;
    case BTP_MENU_BROKER_RESULT:broker_return(s,r);break;
    case BTP_MENU_BROKER_SELL:
        if (item==count-1u) page(s,BTP_MENU_BROKER_HUB,1);
        else { s->menu.map_y=(uint16_t)btp_broker_slot(s,item);page(s,BTP_MENU_BROKER_SELL_CONFIRM,1); }
        break;
    case BTP_MENU_BROKER_SELL_CONFIRM:
        if (item) page(s,BTP_MENU_BROKER_SELL,0);
        else {
            unsigned outcome=btp_broker_sell(s,r,s->menu.map_y);
            page(s,BTP_MENU_BROKER_SELL_RESULT,0);s->menu.notice=(uint8_t)outcome;
        }
        break;
    case BTP_MENU_BROKER_SELL_RESULT:page(s,BTP_MENU_BROKER_SELL,0);break;
    case BTP_MENU_COMBAT_RULES:
        if (item<2) (void)btp_set_combat_profile(s,r,item==0);
        page(s,BTP_MENU_UPDATED_SETTINGS,4);break;
    case BTP_MENU_SETTINGS:case BTP_MENU_UPDATED_SETTINGS:
        if (c->ui==BTP_MENU_UPDATED_SETTINGS) {
            if (item==4) { page(s,BTP_MENU_COMBAT_RULES,s->combat_profile ? 0u : 1u);break; }
            if (item>4) --item;
        }
        if (item==0) page(s,BTP_MENU_STEPS,s->menu.steps==4 ? 2u : s->menu.steps-1u);
        else if (item==1) page(s,BTP_MENU_SPEED,s->menu.speed);
        else if (item==2) { s->menu.sound^=1u;btp_menu_close(s); }
        else if (item==3) page(s,BTP_MENU_OUTTAKES,s->menu.outtakes);
        else if (item==4) page(s,BTP_MENU_QUIT,1);
        else btp_menu_close(s);
        break;
    case BTP_MENU_STEPS:
        s->menu.steps=(uint8_t)(s->story_flags[66] ? 1u : 1u<<item);btp_menu_close(s);break;
    case BTP_MENU_SPEED:s->menu.speed=(uint8_t)item;btp_menu_close(s);break;
    case BTP_MENU_OUTTAKES:s->menu.outtakes=(uint8_t)item;btp_menu_close(s);break;
    case BTP_MENU_LOAD:case BTP_MENU_SAVE:
        if (item==6) btp_menu_close(s);
        else { s->menu.slot=(uint8_t)item;s->menu.io=(uint8_t)(c->ui==BTP_MENU_SAVE ? BTP_MENU_IO_SAVE : BTP_MENU_IO_LOAD); }
        break;
    case BTP_MENU_PERSON:case BTP_MENU_EQUIPMENT:
        item=btp_party_slot(&s->party,item);
        if (s->party.enabled && s->party.people[item][0]==255) break;
        s->party.selected=(uint8_t)item;c->member=(uint8_t)item;page(s,BTP_MENU_INSPECT,0);
        if (s->story_flags[39] && item==s->story_flags[37]) s->spy_discovered=1;
        break;
    case BTP_MENU_INSPECT_KIND:
        if (!item) page(s,BTP_MENU_MECH_PICK,0);
        else if (btp_party_count(&s->party)>1) page(s,BTP_MENU_PERSON,btp_party_ordinal(&s->party,s->party.selected));
        else { c->member=0;page(s,BTP_MENU_INSPECT,0); }
        break;
    case BTP_MENU_MECH_PICK:c->member=(uint8_t)btp_menu_mech_slot(s,item);page(s,BTP_MENU_MECH,0);break;
    case BTP_MENU_INSPECT:btp_menu_close(s);break;
    case BTP_MENU_HEAL:s->menu.notice=3;page(s,BTP_MENU_MESSAGE,0);s->menu.notice=3;break;
    case BTP_MENU_QUIT:if (!item) s->menu.quit=1;btp_menu_close(s);break;
    case BTP_MENU_ALLOCATE: {
        if (item<btp_party_count(&s->party)) { c->member=(uint8_t)btp_party_slot(&s->party,item);page(s,BTP_MENU_CREW,0);break; }
        unsigned pilots=0,mechs=0,missing=0;
        for (unsigned i=0;i<8;++i) pilots+=s->party.people[i][0]!=255 && s->party.people[i][8]!=0;
        for (unsigned i=0;i<4;++i) if (btp_party_mech(s,i)[0]!=255) { ++mechs;missing|=btp_party_mech(s,i)[121]==255; }
        if (!missing) btp_menu_close(s);
        else if (pilots<mechs) page(s,BTP_MENU_ABANDON,1);
        else { page(s,BTP_MENU_MESSAGE,0);s->menu.notice=4; }
        break;
    }
    case BTP_MENU_CREW:
        item=item==btp_menu_mech_count(s) ? 4u : btp_menu_mech_slot(s,item);
        s->party.giver=(uint8_t)item;
        if (item<4 && s->party.people[c->member][8] && btp_party_mech(s,item)[121]!=255 && btp_party_mech(s,item)[121]!=c->member) { page(s,BTP_MENU_SEAT,0);break; }
        btp_party_allocate(s,c->member,item,item<4 && s->party.people[c->member][8] ? 121u : 122u);page(s,BTP_MENU_ALLOCATE,btp_party_ordinal(&s->party,c->member));break;
    case BTP_MENU_SEAT:btp_party_allocate(s,c->member,s->party.giver,item ? 122u : 121u);page(s,BTP_MENU_ALLOCATE,btp_party_ordinal(&s->party,c->member));break;
    case BTP_MENU_ABANDON:
        if (!item) for (unsigned i=0;i<4;++i) if (btp_party_mech(s,i)[0]!=255 && btp_party_mech(s,i)[121]==255) {
            btp_party_mech(s,i)[0]=255;s->party.mech_types[i]=255;for (unsigned j=0;j<8;++j) if (s->party.people[j][12]==i) s->party.people[j][12]=8;
        }
        btp_menu_close(s);break;
    case BTP_MENU_TRANSFER:
        if (item==2) btp_menu_close(s);
        else { s->party.giver=c->member;s->party.item=(uint8_t)item;page(s,BTP_MENU_RECIPIENT,0); }
        break;
    case BTP_MENU_RECIPIENT:
        if (item==btp_party_count(&s->party)) btp_menu_close(s);
        else { item=btp_party_slot(&s->party,item);btp_party_transfer(s,s->party.giver,item,s->party.item);btp_menu_close(s); }
        break;
    default:btp_menu_close(s);break;
    }
}
int btp_actions_valid(const BtpState *s)
{
    /* Both prison and garage explicitly invoke allocation inside their BLD;
       the normal outdoor population restriction does not apply to this call. */
    if (s->menu.from_story>2 || (s->menu.from_story &&
        (!((s->campaign.building==13 && s->script.native_action==39) || (s->campaign.building==8 && s->script.native_action==46) ||
           (s->campaign.building==10 && s->script.native_action==27)) ||
         s->script.status!=BTP_SCRIPT_NATIVE || s->mode!=(s->menu.from_story==1 ? BTP_ACTIONS : BTP_BUILDING)))) return 0;
    const BtpMenuState *m=&s->menu;
    if ((m->steps!=1 && m->steps!=2 && m->steps!=4) || m->sound>1 || m->speed>5 || m->outtakes>2 ||
        m->slot>5 || m->io>2 || m->notice>(s->mode==BTP_ACTIONS && s->campaign.ui==BTP_MENU_MAP ? 15u : s->campaign.ui==BTP_MENU_BROKER_SELL_RESULT ? BTP_BROKER_CREDIT_LIMIT : 5u) || m->quit>1 || m->map_x>2047 || m->map_y>2047 || m->from_intro>1) return 0;
    if (m->from_intro && (s->mode!=BTP_ACTIONS || (s->campaign.ui!=BTP_MENU_LOAD && s->campaign.ui!=BTP_MENU_MESSAGE))) return 0;
    if ((s->mode==BTP_ACTIONS)!=(s->campaign.ui!=0)) return 0;
    if (s->campaign.ui>BTP_MENU_BROKER_CLASSES || (s->campaign.ui && s->campaign.selected>=btp_actions_count(s))) return 0;
    if (m->broker_class>BTP_ROSTER_ASSAULT || (m->broker_class &&
        (s->campaign.ui<BTP_MENU_BROKER || s->campaign.ui>BTP_MENU_BROKER_RESULT))) return 0;
    if (s->campaign.ui==BTP_MENU_MECH && (s->campaign.member>=4 || !s->campaign.owned || btp_party_mech((BtpState *)s,s->campaign.member)[0]==255)) return 0;
    return !m->io || (s->mode==BTP_ACTIONS && s->campaign.ui==(m->io==BTP_MENU_IO_SAVE ? BTP_MENU_SAVE : BTP_MENU_LOAD));
}
