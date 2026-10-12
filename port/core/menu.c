#include "core/menu.h"
#include "core/party.h"
#include "core/world.h"
#include <string.h>
#include <stdlib.h>
static int active_mechs(const BtpState *s)
{
    if (!s->campaign.owned) return 0;
    for (unsigned i=0;i<4;++i) {
        const uint8_t *m=i ? s->party.mechs[i-1] : s->campaign.mech;
        if (m[0]!=255 && (!i || s->party.mech_types[i]!=255)) return 1;
    }
    return 0;
}
static unsigned root_item(const BtpState *s,unsigned item)
{
    return item+(unsigned)(!active_mechs(s) && item>=2);
}
unsigned btp_actions_count(const BtpState *s)
{
    switch (s->campaign.ui) {
    case BTP_MENU_ROOT:return active_mechs(s) ? 8u : 7u;
    case BTP_MENU_ALLOCATE:return 9;
    case BTP_MENU_CREW:return 6;
    case BTP_MENU_SEAT:case BTP_MENU_ABANDON:return 2;
    case BTP_MENU_TRANSFER:return 3;
    case BTP_MENU_RECIPIENT:return 9;
    case BTP_MENU_PERSON:case BTP_MENU_EQUIPMENT:case BTP_MENU_HEAL:return s->party.enabled ? 8u : 1u;
    case BTP_MENU_SETTINGS:return 6;
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
    case BTP_MENU_ROOT:return root[root_item(s,item)];
    case BTP_MENU_SETTINGS:return item==2 && !s->menu.sound ? "Turn Sound On" : settings[item];
    case BTP_MENU_STEPS:return steps[item];
    case BTP_MENU_SPEED:return speed[item];
    case BTP_MENU_OUTTAKES:return frequency[item];
    case BTP_MENU_LOAD:case BTP_MENU_SAVE:return slots[item];
    case BTP_MENU_ALLOCATE:case BTP_MENU_RECIPIENT:return item==8 ? "Done" : btp_party_name(&s->party,item);
    case BTP_MENU_CREW: {
        if (item>=4) return item==4 ? "Travel on foot" : "Cancel";
        const uint8_t *m=item ? s->party.mechs[item-1] : s->campaign.mech;
        return m[0]==255 ? "Empty" : m[0]=='L' ? "Locust" : m[0]=='C' ? "Commando" : m[0]=='W' ? "Wasp" : m[0]=='S' ? "Chameleon" : m[0]=='J' ? "Jenner" : "Owned 'Mech";
    }
    case BTP_MENU_SEAT:case BTP_MENU_ABANDON:return item ? "No" : "Yes";
    case BTP_MENU_TRANSFER:return item==0 ? "Give weapon" : item==1 ? "Give armour" : "Return to game";
    case BTP_MENU_QUIT:return item ? "No" : "Yes";
    default:return s->party.enabled ? btp_party_name(&s->party,item) : "Jason";
    }
}
void btp_menu_open(BtpState *s)
{
    s->mode=BTP_ACTIONS;s->campaign.ui=BTP_MENU_ROOT;s->campaign.selected=0;s->menu.notice=0;
}
void btp_menu_close(BtpState *s)
{
    s->campaign.ui=s->campaign.selected=s->campaign.member=0;s->menu.io=s->menu.notice=0;
    s->mode=BTP_EXPLORE;
}
static void page(BtpState *s,unsigned phase,unsigned selected)
{
    s->campaign.ui=(uint8_t)phase;s->campaign.selected=(uint8_t)selected;s->menu.notice=0;
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
    if (c->ui==BTP_MENU_INSPECT && s->party.enabled && btp_party_count(&s->party)>1 && (a==BTP_UP || a==BTP_DOWN)) { page(s,BTP_MENU_TRANSFER,0);return; }
    if (c->ui==BTP_MENU_MAP) {
        if (a==BTP_ACCEPT || a==BTP_CANCEL || a==BTP_OPEN_MENU) btp_menu_close(s);
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
    case BTP_MENU_ROOT:
        switch (root_item(s,item)) {
        case 0:btp_menu_close(s);break;
        case 1:page(s,BTP_MENU_SETTINGS,0);break;
        case 2:
            btp_party_init(s);
            if (btp_world_populated(r,s)) { page(s,BTP_MENU_MESSAGE,0);s->menu.notice=4; }
            else page(s,BTP_MENU_ALLOCATE,0);
            break;
        case 3:page(s,BTP_MENU_PERSON,s->party.selected);break;
        case 4:
            (void)btp_party_heal(s,r,0);page(s,BTP_MENU_MESSAGE,0);s->menu.notice=3;break;
        case 5:page(s,BTP_MENU_LOAD,s->menu.slot);break;
        case 6:page(s,BTP_MENU_SAVE,s->menu.slot);break;
        case 7:
            s->menu.map_x=s->story_flags[4] ? c->world_x : (uint16_t)(1536+s->x_half);
            s->menu.map_y=s->story_flags[4] ? c->world_y : (uint16_t)(1536+s->y_half);
            page(s,BTP_MENU_MAP,0);break;
        }
        break;
    case BTP_MENU_SETTINGS:
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
        if (s->party.enabled && s->party.people[item][0]==255) break;
        s->party.selected=(uint8_t)item;c->member=(uint8_t)item;page(s,BTP_MENU_INSPECT,0);break;
    case BTP_MENU_INSPECT:btp_menu_close(s);break;
    case BTP_MENU_HEAL:s->menu.notice=3;page(s,BTP_MENU_MESSAGE,0);s->menu.notice=3;break;
    case BTP_MENU_QUIT:if (!item) s->menu.quit=1;btp_menu_close(s);break;
    case BTP_MENU_ALLOCATE: {
        if (item<8) { if (s->party.people[item][0]!=255) { c->member=(uint8_t)item;page(s,BTP_MENU_CREW,0); }break; }
        unsigned pilots=0,mechs=0,missing=0;
        for (unsigned i=0;i<8;++i) pilots+=s->party.people[i][0]!=255 && s->party.people[i][8]!=0;
        for (unsigned i=0;i<4;++i) if (btp_party_mech(s,i)[0]!=255) { ++mechs;missing|=btp_party_mech(s,i)[121]==255; }
        if (!missing) btp_menu_close(s);
        else if (pilots<mechs) page(s,BTP_MENU_ABANDON,1);
        else { page(s,BTP_MENU_MESSAGE,0);s->menu.notice=4; }
        break;
    }
    case BTP_MENU_CREW:
        if (item==5) { page(s,BTP_MENU_ALLOCATE,0);break; }
        if (item<4 && btp_party_mech(s,item)[0]==255) break;
        s->party.giver=(uint8_t)item;
        if (item<4 && s->party.people[c->member][8] && btp_party_mech(s,item)[121]!=255 && btp_party_mech(s,item)[121]!=c->member) { page(s,BTP_MENU_SEAT,1);break; }
        btp_party_allocate(s,c->member,item,item<4 && s->party.people[c->member][8] ? 121u : 122u);page(s,BTP_MENU_ALLOCATE,c->member);break;
    case BTP_MENU_SEAT:btp_party_allocate(s,c->member,s->party.giver,item ? 122u : 121u);page(s,BTP_MENU_ALLOCATE,c->member);break;
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
        if (item==8) btp_menu_close(s);
        else if (s->party.people[item][0]!=255) { btp_party_transfer(s,s->party.giver,item,s->party.item);btp_menu_close(s); }
        break;
    default:btp_menu_close(s);break;
    }
}
int btp_actions_valid(const BtpState *s)
{
    const BtpMenuState *m=&s->menu;
    if ((m->steps!=1 && m->steps!=2 && m->steps!=4) || m->sound>1 || m->speed>5 || m->outtakes>2 ||
        m->slot>5 || m->io>2 || m->notice>4 || m->quit>1 || m->map_x>2047 || m->map_y>2047) return 0;
    if ((s->mode==BTP_ACTIONS)!=(s->campaign.ui!=0)) return 0;
    if (s->campaign.ui>BTP_MENU_RECIPIENT || (s->campaign.ui && s->campaign.selected>=btp_actions_count(s))) return 0;
    return !m->io || (s->mode==BTP_ACTIONS && s->campaign.ui==(m->io==BTP_MENU_IO_SAVE ? BTP_MENU_SAVE : BTP_MENU_LOAD));
}
