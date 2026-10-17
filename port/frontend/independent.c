#include "frontend/independent.h"
#include "frontend/art.h"
#include "data/project.h"
#include "data/unit_data.h"
#include "core/events.h"
#include "core/menu.h"
#include "core/party.h"
#include "core/combat.h"
#include "core/world.h"
#include "core/roster_game.h"
#include "core/effects.h"
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

/* Independent presentation uses only the package's palette, glyphs and pixels.
   The original renderer and its resource-index conventions are left intact. */
typedef struct { const BtpIndependent *art;uint32_t *f; } Canvas;
static void box(Canvas *c,int x,int y,int w,int h,unsigned color)
{
    for (int row=y;row<y+h && row<200;++row) for (int col=x;col<x+w && col<320;++col)
        if (row>=0 && col>=0) c->f[row*320+col]=c->art->palette[color&15u];
}
static void text(Canvas *c,int x,int y,const char *str,unsigned color)
{
    for (;*str && x<316;++str,x+=6) {
        unsigned ch=(unsigned char)*str;if (ch<32 || ch>127) ch='?';
        for (unsigned row=0;row<7;++row) for (unsigned col=0;col<5;++col)
            if (c->art->font[ch-32][row]&(16u>>col)) box(c,x+(int)col,y+(int)row,1,1,color);
    }
}
static void image(Canvas *c,const uint8_t *pixels,int x,int y,unsigned w,unsigned h,int transparent,int limit)
{
    for (unsigned row=0;row<h;++row) for (unsigned col=0;col<w;++col) {
        int px=x+(int)col,py=y+(int)row;unsigned color=pixels[row*w+col];
        if ((!transparent || color) && px>=0 && px<limit && py>=12 && py<150) box(c,px,py,1,1,color);
    }
}
static void selection(Canvas *c,unsigned row,unsigned selected,int y,const char *label)
{ if (row==selected) box(c,96,y-1,214,9,3);text(c,100,y,label,row==selected ? 15u : 7u); }
static void beam(Canvas *c,int x,int y,int tx,int ty,unsigned color)
{
    int dx=abs(tx-x),dy=-abs(ty-y),sx=x<tx ? 1 : -1,sy=y<ty ? 1 : -1,error=dx+dy;
    for (unsigned budget=0;budget<2048;++budget) {
        if (x>=0 && x<224 && y>=12 && y<150) box(c,x,y,1,1,color);
        if (x==tx && y==ty) return;
        int twice=2*error;if (twice>=dy) { error+=dy;x+=sx; }if (twice<=dx) { error+=dx;y+=sy; }
    }
}
static const char *person(const BtpResources *r,const BtpState *s,unsigned slot)
{
    if (slot>=8 || s->event.people[slot]>=r->project->adventure.person_count) return "Unassigned";
    return r->project->adventure.people[s->event.people[slot]].name;
}
static void frame(Canvas *c,const BtpResources *r,const BtpState *s)
{
    box(c,0,0,320,200,0);box(c,0,0,320,11,1);text(c,5,2,r->project->title,15);
    char line[64];snprintf(line,sizeof line,"Credits %u",s->credits);text(c,5,187,line,14);
    text(c,124,187,"SPACE select  ESC back  F5/F9",7);
}
static void portrait(Canvas *c,unsigned slot)
{
    box(c,7,19,76,76,1);image(c,c->art->portraits[slot&1u],13,25,64,64,0,90);
    text(c,10,104,slot ? "Relay Office" : "Walker Depot",14);
}
static void event(Canvas *c,const BtpResources *r,const BtpState *s)
{
    const BtpAdventure *a=&r->project->adventure;const BtpEventNode *e=&a->nodes[s->event.node];
    portrait(c,e->portrait>1);
    if (e->picture!=BTP_ART_NONE) (void)btp_art_draw(r,e->picture,s->tick/8u,8,20,8,12,96,108,c->f);
    char lines[96][28];unsigned count=btp_event_lines(e->text,lines);
    if (s->event.phase==BTP_EVENT_ENTRY) {
        const BtpSceneEntrance *door=&a->maps[s->event.origin_map].entrances[s->event.origin_entry];
        text(c,100,24,door->name,14);text(c,100,48,door->person==255 ? "Enter this building?" : "Talk to this person?",15);
        selection(c,0,s->event.selected,72,"Yes");selection(c,1,s->event.selected,84,"No");return;
    }
    if (s->event.phase==BTP_EVENT_FAULT) { text(c,100,24,"Event stopped",12);text(c,100,40,e->id,7);text(c,100,64,"ESC returns to the map.",15);return; }
    if (s->event.phase==BTP_EVENT_COMPLETE) { text(c,100,32,"The End",14);text(c,100,56,"Thanks for playing.",15);text(c,100,80,"Press any key to exit.",7);return; }
    unsigned first=s->event.page*20u,y=18;
    for (unsigned i=first;i<count && i<first+20;++i,y+=8) text(c,100,(int)y,lines[i],15);
    if (e->op==BTP_EVENT_CHOICE) for (unsigned i=0;i<e->count;++i,y+=8) selection(c,i,s->event.selected,(int)y+8,e->labels[i]);
    else text(c,100,178,(first+20<count) ? "SPACE: next page" : "SPACE: continue",14);
}
static void overview(Canvas *c,const BtpResources *r,const BtpState *s)
{
    const BtpScene *m=btp_scene(r,s);if (!m) return;
    if (btp_art_world_map(r,s,c->f)) { text(c,5,16,r->project->adventure.worlds[m->world-1].name,15);return; }
    unsigned scale=2;int left=96,top=28;
    text(c,100,16,m->name,15);
    for (unsigned y=0;y<m->visual.height;++y) for (unsigned x=0;x<m->visual.width;++x) {
        const BtpSceneTile *tile=&r->project->adventure.tiles[m->cells[y*64+x]];
        unsigned color=btp_world_seen(s,(m->origin_x+x)/8u,(m->origin_y+y)/8u) ? tile->color : 0;
        box(c,left+(int)(x*scale),top+(int)(y*scale),(int)scale,(int)scale,color);
    }
    box(c,left+(int)s->x_half,top+(int)s->y_half,3,3,(s->tick/8u)&1u ? 14u : 15u);
    text(c,100,170,"Your position flashes.",14);
}
static void map(Canvas *c,const BtpResources *r,const BtpState *s)
{
    const BtpScene *m=btp_scene(r,s);if (!m) return;
    int cx=(int)s->x_half*8-108,cy=(int)s->y_half*8-76;
    for (int y=cy/16-1;y<=cy/16+11;++y) for (int x=cx/16-1;x<=cx/16+15;++x) {
        const BtpSceneTile *t=btp_scene_tile(&r->project->adventure,m,x,y);if (!t) continue;
        int px=x*16-cx,py=y*16-cy;
        if (px<=-16 || px>=224 || py<=-16 || py>=150) continue;
        if (t->sheet==3) (void)btp_art_draw(r,t->graphic,s->tick/8u,px,py,0,12,224,150,c->f);
        else image(c,c->art->tiles[t->graphic],px,py,16,16,0,224);
    }
    for (unsigned i=0;i<m->entrance_count;++i) {
        const BtpSceneEntrance *door=&m->entrances[i];int x=(int)door->x*8-cx,y=(int)door->y*8-cy;
        int recruited=0;if (door->person!=255) for (unsigned k=0;k<8;++k) if (s->party.people[k][0]!=255 && s->event.people[k]==door->person) recruited=1;
        if (recruited) continue;
        if (door->icon!=BTP_ART_NONE) {
            const BtpArtImage *im=&r->project->graphics.images[door->icon];
            (void)btp_art_draw(r,door->icon,s->tick/8u,x-(int)im->width/2,y-(int)im->height,0,12,224,150,c->f);
        } else if (door->person!=255) {
            if (!btp_art_sprite(r,1,s->tick/16u,x,y-8,0,12,224,150,c->f)) image(c,c->art->sprites[2][(s->tick/16u)&3u],x,y-8,16,16,1,224);
        }
        else { if (x>=0 && x<220 && y>=12 && y<146) { box(c,x,y,5,3,14);box(c,x+2,y-2,1,7,15); } }
    }
    if (s->combat.phase) {
        const BtpCombatState *combat=&s->combat;
        for (unsigned i=0;i<combat->count;++i) {
            const BtpCombatUnit *u=&combat->unit[i];const BtpCombatEffect *pending=btp_effects_pending_death(s,i);
            unsigned family=u->record[0]==255 && !pending ? 4u : u->infantry ? (i<combat->friends ? 2u : 3u) : u->record[124]&1u;
            unsigned slot=family==4 ? 5u : u->infantry ? i<combat->friends ? combat->ids[i]==4 ? 0u : 1u : 2u : 3u+(family&1u);
            if ((u->infantry || family==4 || !btp_art_unit(r,u->record,combat->walk[i],u->direction,(int)u->x*8-cx-4,(int)u->y*8-cy-24,0,12,224,150,c->f)) && !btp_art_sprite(r,slot,combat->walk[i],(int)u->x*8-cx,(int)u->y*8-cy,0,12,224,150,c->f))
                image(c,c->art->sprites[family][combat->walk[i]&3u],(int)u->x*8-cx,(int)u->y*8-cy,16,16,1,224);
            if (i==combat->active_unit) { int x=(int)u->x*8-cx,y=(int)u->y*8-cy;if (x>=0 && x<220 && y>=14 && y<148) box(c,x,y-2,12,1,14); }
        }
        if (combat->phase==BTP_COMBAT_MOVE) {
            int x=(int)combat->cursor_x*8-cx,y=(int)combat->cursor_y*8-cy;
            beam(c,x-4,y,x+4,y,14);beam(c,x,y-4,x,y+4,14);
        }
        if (s->effects.count && combat->graphics) {
            const BtpCombatEffect *e=&s->effects.shots[0];
            beam(c,(int)e->x*8-cx+8,(int)e->y*8-cy+4,(int)e->tx*8-cx+8,(int)e->ty*8-cy+4,e->actor<combat->friends ? 14u : 12u);
        }
    } else {
        for (unsigned i=0;i<8;++i) if (s->party.people[i][0]!=255 && s->party.people[i][12]>=8) {
            int x=(int)(i ? s->party.x[i] : s->campaign.world_x)-(int)(2*m->origin_x);
            int y=(int)(i ? s->party.y[i] : s->campaign.world_y)-(int)(2*m->origin_y);
            unsigned walk=i ? s->party.walk[i] : s->player_walk;
            if (!btp_art_sprite(r,i ? 1u : 0u,walk,x*8-cx,y*8-cy-8,0,12,224,150,c->f)) image(c,c->art->sprites[2][walk&3u],x*8-cx,y*8-cy-8,16,16,1,224);
        }
        /* Mounted people retain stale foot coordinates. Draw each active
           vehicle once at its saved ground anchor, including an unassigned
           purchase; passengers never create another vehicle sprite. */
        for (unsigned i=0;i<4;++i) {
            const uint8_t *mech=i ? s->party.mechs[i-1] : s->campaign.mech;
            if (mech[0]==255) continue;
            unsigned pilot=mech[121],walk=pilot && pilot<8 ? s->party.walk[pilot] : s->campaign.mech_walk;
            int x=(int)s->party.mech_x[i]-(int)(2*m->origin_x);
            int y=(int)s->party.mech_y[i]-(int)(2*m->origin_y);
            if (!btp_art_unit(r,mech,walk,pilot<8 ? s->party.direction[pilot] : s->campaign.mech_direction,x*8-cx-4,y*8-cy-24,0,12,224,150,c->f) && !btp_art_sprite(r,3u+(mech[124]&1u),walk,x*8-cx,y*8-cy-16,0,12,224,150,c->f)) image(c,c->art->sprites[mech[124]&1u][walk&3u],x*8-cx,y*8-cy-16,16,16,1,224);
        }
    }
    box(c,224,12,96,170,1);text(c,229,20,"Team",14);
    for (unsigned i=0;i<8;++i) if (s->party.people[i][0]!=255) text(c,229,34+(int)i*12,person(r,s,i),15);
    text(c,5,157,m->name,15);text(c,5,170,s->combat.phase ? "Combat: choose orders below" : "Arrows travel | SPACE menu",7);
}
static void actions(Canvas *c,const BtpResources *r,const BtpState *s)
{
    const BtpCampaignState *v=&s->campaign;char line[96];unsigned indices[256];
    portrait(c,0);
    if (v->ui==BTP_MENU_MAP) { overview(c,r,s);return; }
    if (v->ui==BTP_MENU_INSPECT) {
        const uint8_t *p=s->party.people[v->member];text(c,100,20,person(r,s,v->member),14);
        const char *const labels[]={"Strength","Dexterity","Intelligence","Sidearms","Rifles","Heavy arms","Gunnery","Piloting","Technical","Medical"};
        for (unsigned i=0;i<10;++i) { snprintf(line,sizeof line,"%-14s %u",labels[i],p[i+1]);text(c,100,36+(int)i*12,line,15); }return;
    }
    if (v->ui==BTP_MENU_MECH) {
        const uint8_t *m=btp_party_mech((BtpState *)s,v->member);memcpy(line,m,15);line[15]=0;text(c,100,20,line,14);
        if (btp_vehicle_kind(m)) {
            box(c,8,20,80,95,1);(void)btp_art_unit(r,m,s->tick/8u,0,34,44,8,20,88,115,c->f);
            static const unsigned regions[]={17,18,22,23,21};
            for (unsigned i=0;i<5;++i) {
                unsigned p=regions[i];snprintf(line,sizeof line,"%-6s A%3u/%3u S%2u/%2u",btp_vehicle_location(p),m[p],m[p+69],m[p+11],m[p+80]);text(c,100,40+(int)i*18,line,15);
            }
            snprintf(line,sizeof line,"Cruise %u  Flank %u",m[49],(3u*m[49]+1)/2);text(c,100,144,line,14);
            snprintf(line,sizeof line,"Motive damage %u/2",m[118]);text(c,100,160,line,7);return;
        }
        unsigned current=0,maximum=0;for (unsigned i=0;i<11;++i) { current+=m[17+i];maximum+=m[86+i]; }
        snprintf(line,sizeof line,"Armor %u / %u",current,maximum);text(c,100,40,line,15);
        box(c,100,54,200,5,8);if (maximum) box(c,100,54,(int)(current*200u/maximum),5,10);
        snprintf(line,sizeof line,"Walk %u   Jump %u",m[49],m[50]);text(c,100,74,line,15);return;
    }
    unsigned count=btp_actions_count(s);int top=30;
    const char *heading=btp_broker_page(v->ui) ? "Unit exchange" : v->ui==BTP_MENU_INSPECT_KIND ? "Inspect a unit?" :
        v->ui==BTP_MENU_ALLOCATE ? "Choose a person to assign" : v->ui==BTP_MENU_CREW || v->ui==BTP_MENU_MECH_PICK ? "Choose a unit" :
        v->ui==BTP_MENU_SEAT ? "Assign as pilot?" : v->ui==BTP_MENU_QUIT ? "Quit this expedition?" :
        v->ui==BTP_MENU_SAVE ? "Save game - choose a slot" : v->ui==BTP_MENU_LOAD ? "Load game - choose a slot" : "Expedition menu";
    text(c,100,16,heading,14);
    if (v->ui==BTP_MENU_BROKER_HUB) {
        const char *const labels[]={"Mechs","Vehicles","Sell a unit","Leave"};for (unsigned i=0;i<4;++i) selection(c,i,v->selected,top+(int)i*12,labels[i]);return;
    }
    if (v->ui==BTP_MENU_BROKER || v->ui==BTP_MENU_BROKER_SELL) {
        unsigned stock=btp_events_catalogue(s,r,s->menu.broker_class,r->roster.count,indices);
        for (unsigned i=0;i<count;++i) {
            if ((v->ui==BTP_MENU_BROKER && v->member+i>=stock) || (v->ui==BTP_MENU_BROKER_SELL && i>=btp_broker_count(s))) strcpy(line,"Back");
            else if (v->ui==BTP_MENU_BROKER) { const BtpRosterMech *m=&r->roster.mechs[indices[v->member+i]];snprintf(line,sizeof line,"%.15s  %u",m->record,m->price); }
            else { unsigned bay=btp_broker_slot(s,i);snprintf(line,sizeof line,"%.15s  %u",btp_party_mech((BtpState *)s,bay),btp_broker_offer(s,r,bay)); }
            selection(c,i,v->selected,top+(int)i*12,line);
        }return;
    }
    if (v->ui==BTP_MENU_BROKER_CONFIRM || v->ui==BTP_MENU_BROKER_SELL_CONFIRM) {
        text(c,100,32,"Confirm this transaction?",15);
        selection(c,0,v->selected,56,"Yes");selection(c,1,v->selected,68,"No");return;
    }
    if (v->ui==BTP_MENU_BROKER_RESULT || v->ui==BTP_MENU_BROKER_SELL_RESULT) {
        text(c,100,32,s->menu.notice==BTP_BROKER_BOUGHT ? "Purchased. Assign a pilot." : s->menu.notice==BTP_BROKER_SOLD ? "Walker sold." : s->menu.notice==BTP_BROKER_NO_FUNDS ? "Insufficient credits." : "No free bay or transaction.",15);text(c,100,60,"SPACE: continue",14);return;
    }
    for (unsigned i=0;i<count && i<12;++i) {
        const char *label=btp_actions_label(s,i);
        if (v->ui==BTP_MENU_ALLOCATE || v->ui==BTP_MENU_PERSON || v->ui==BTP_MENU_HEAL || v->ui==BTP_MENU_RECIPIENT || v->ui==BTP_MENU_EQUIPMENT) {
            if (i<btp_party_count(&s->party)) label=person(r,s,btp_party_slot(&s->party,i));
        }
        if ((v->ui==BTP_MENU_MECH_PICK || v->ui==BTP_MENU_CREW) && i<btp_menu_mech_count(s)) {
            const uint8_t *record=btp_party_mech((BtpState *)s,btp_menu_mech_slot(s,i));
            snprintf(line,sizeof line,"%.15s",record);label=line;
        }
        selection(c,i,v->selected,top+(int)i*12,label);
    }
    if (v->ui==BTP_MENU_MESSAGE) text(c,100,160,"Action completed. SPACE returns.",7);
}
static void combat(Canvas *c,const BtpResources *r,const BtpState *s)
{
    const BtpCombatState *b=&s->combat;char line[96];
    map(c,r,s);box(c,0,150,320,34,0);
    if (b->phase>=BTP_COMBAT_CONTROL && b->phase<=BTP_COMBAT_GRAPHICS) {
        box(c,48,46,224,100,1);text(c,60,56,b->phase==BTP_COMBAT_CONTROL ? "Computer control?" : b->phase==BTP_COMBAT_MESSAGES ? "Combat reports" : "Show combat graphics?",15);
        const char *const verbosity[]={"None","Brief","Detailed"};unsigned count=b->phase==BTP_COMBAT_MESSAGES ? 3u : 2u;
        for (unsigned i=0;i<count;++i) { if (i==b->selected) box(c,60,74+(int)i*12,198,9,3);text(c,64,75+(int)i*12,b->phase==BTP_COMBAT_MESSAGES ? verbosity[i] : i ? "No" : "Yes",15); }return;
    }
    if (b->phase==BTP_COMBAT_MENU) {
        const char *const labels[]={"Walk","Run","Jump","Weapons","Kick","Computer","Scan","Next unit","Retreat","Execute","Clear move"};
        for (unsigned i=0;i<btp_combat_menu_count(b);++i) {
            unsigned id=btp_combat_menu_command(b,i);int x=(int)(i%5)*64,y=154+(int)(i/5)*13;
            if (id==b->selected) box(c,x,y-1,63,10,3);
            text(c,x+2,y,labels[id],15);
        }return;
    }
    if (b->phase==BTP_COMBAT_WEAPONS) {
        const BtpCombatUnit *u=&b->unit[b->active_unit];unsigned n=btp_combat_weapon_count(u);
        snprintf(line,sizeof line,"Choose weapon %u/%u - arrows, SPACE",b->weapon_selected+1u,n);text(c,4,154,line,15);
        if (b->weapon_selected<n) { BtpWeaponDefinition w=btp_unit_weapon_definition(&r->combat,u,b->weapon_selected);snprintf(line,sizeof line,"%.11s  Damage %u  Heat %u",w.name,w.damage,w.heat);text(c,4,168,line,14); }
        else text(c,4,168,"Return to combat orders",14);
        return;
    }
    if (b->phase==BTP_COMBAT_TARGET || b->phase==BTP_COMBAT_KICK || b->phase==BTP_COMBAT_OVERRIDE || b->phase==BTP_COMBAT_REPLACE || b->phase==BTP_COMBAT_SCAN_CHOICE || b->phase==BTP_COMBAT_SCAN || b->phase==BTP_COMBAT_SCAN_DETAIL || b->phase==BTP_COMBAT_PICK) {
        box(c,48,30,224,114,1);
        unsigned unit=b->phase==BTP_COMBAT_SCAN || b->phase==BTP_COMBAT_SCAN_DETAIL || b->phase==BTP_COMBAT_PICK ? b->scan_unit : b->target_unit;
        const BtpCombatUnit *u=&b->unit[unit<b->count ? unit : 0];
        if (u->infantry) snprintf(line,sizeof line,"Person - health %u",u->record[15]);
        else snprintf(line,sizeof line,"%.15s - heat %u",u->record,u->heat);
        text(c,60,40,line,14);
        if (b->phase==BTP_COMBAT_SCAN_DETAIL) {
            unsigned armor=0,maximum=0;for (unsigned i=0;i<11;++i) { armor+=u->record[17+i];maximum+=u->record[86+i]; }
            snprintf(line,sizeof line,"Armor %u/%u  Weapons %u",armor,maximum,btp_combat_weapon_count(u));text(c,60,62,line,15);
            text(c,60,86,"SPACE: return to scan",7);return;
        }
        const char *labels[3]={"Use this target","Next enemy","Cancel"};unsigned selected=b->target_selected,count=3;
        if (b->phase==BTP_COMBAT_OVERRIDE || b->phase==BTP_COMBAT_REPLACE) { text(c,60,56,"Replace the previous order?",15);labels[0]="Yes";labels[1]="No";count=2; }
        if (b->phase==BTP_COMBAT_SCAN_CHOICE) { labels[0]="Friendly units";labels[1]="Enemy units";labels[2]="Cancel";selected=b->selected; }
        if (b->phase==BTP_COMBAT_SCAN) { labels[0]="Next unit";labels[1]=btp_combat_scan_detail(b) ? "Inspect details" : "Done";count=btp_combat_scan_detail(b) ? 3u : 2u;labels[2]="Done";selected=b->selected; }
        if (b->phase==BTP_COMBAT_PICK) { text(c,60,70,"Arrows choose. SPACE accepts.",15);return; }
        for (unsigned i=0;i<count;++i) { if (i==selected) box(c,60,76+(int)i*12,198,9,3);text(c,64,77+(int)i*12,labels[i],15); }return;
    }
    if (b->phase==BTP_COMBAT_MOVE) { text(c,4,154,"Arrows set destination. SPACE confirms.",15);text(c,4,168,"ESC returns to combat orders.",7);return; }
    if (b->phase==BTP_COMBAT_NOTICE) {
        const char *notice=b->notice==2 ? "This unit cannot use that movement mode." : b->notice==3 ? "This unit cannot kick." : b->notice==4 ? "Too many movement waypoints." : b->notice==18 ? "That weapon is damaged." : b->notice==19 ? "That weapon has no ammunition." : b->notice==20 ? "Overheated: weapons are shut down." : b->notice==21 ? "Sensors are damaged." : b->notice==22 ? "Sensors are destroyed." : "That order is unavailable here.";
        text(c,4,154,notice,15);text(c,4,168,"SPACE: continue",14);return;
    }
    snprintf(line,sizeof line,"Round %u - resolving orders. SPACE pauses.",b->round);text(c,4,154,line,15);
    if (s->effects.shown.active) { snprintf(line,sizeof line,"%s  damage %u",s->effects.shown.hit ? "Hit" : "Miss",b->shot.damage);text(c,4,168,line,14); }
}
void btp_independent_render(const BtpResources *r,const BtpState *s,uint32_t f[BTP_PIXELS])
{
    if (btp_art_picture(r,s,f)) return;
    Canvas c={&r->project->independent,f};frame(&c,r,s);
    if (s->mode==BTP_EVENT || s->mode==BTP_ENDING) event(&c,r,s);
    else if (s->mode==BTP_ACTIONS) actions(&c,r,s);
    else if (s->combat.phase) combat(&c,r,s);
    else if (s->mode==BTP_GAME_OVER) { text(&c,90,80,"Your expedition has ended.",15);text(&c,90,100,"F9 restores your last save.",7); }
    else map(&c,r,s);
}
