/* Read-only scenario audit: real movement rules and automatic player planner.
   Declared open-ground/heat/ammunition prerequisites, not a campaign replay. */
#include "core/combat.h"
#include "data/roster.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc,char **argv)
{
    if (argc!=4) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError error;char diagnostic[256];
    if (!r || !btp_resources_load(argv[1],r,&error) || !btp_combat_data_load(argv[2],&r->combat,&error) ||
        !btp_roster_load(argv[3],&r->roster,diagnostic)) return 2;
    memset(r->map.tiles,64,sizeof r->map.tiles);
    puts("id,mass,walk,run,jump,lrm_mounts,preferred,heat,empty,separation_halfsteps,range_distance,mode,goal_x,goal_y,path_steps,gun_orders");
    for (unsigned model=0;model<r->roster.count;++model) {
        const BtpRosterMech *definition=&r->roster.mechs[model];
        BtpCombatUnit unit={0};memcpy(unit.record,definition->record,125);
        unsigned lrm=0,preferred=255;
        for (unsigned i=51;i<86;++i) {
            unsigned component=unit.record[i];lrm+=component>=26 && component<=29;
            if (component>=16 && component<=32) {
                unsigned candidate=(r->combat.weapons[component][14]&224u)>>3;
                if (candidate<preferred) preferred=candidate;
            }
        }
        if (preferred==255) preferred=0;
        static const unsigned distances[]={2,6,12,24,40,60,80};
        for (unsigned hot=0;hot<2;++hot) for (unsigned empty=0;empty<2;++empty) for (unsigned q=0;q<7;++q) {
            BtpState s;btp_start(&s);s.mode=BTP_MISSION;s.mission.phase=BTP_MISSION_DRIVE;
            s.mission.assignment=2;btp_combat_begin(&s,r);
            BtpCombatState *c=&s.combat;c->phase=BTP_COMBAT_MENU;c->selected=9;c->graphics=0;c->automatic=1;
            memcpy(c->unit[0].record,definition->record,125);c->unit[0].x=32;c->unit[0].y=64;c->unit[0].heat=(uint8_t)(hot*20);
            c->unit[1].x=(uint8_t)(32+distances[q]);c->unit[1].y=64;
            if (empty) for (unsigned i=39;i<49;++i) if (c->unit[0].record[i]!=255) c->unit[0].record[i]=0;
            btp_combat_tick(&s,r,BTP_ACCEPT);
            unsigned steps=0,orders=0;
            for (unsigned i=0;i<12;++i) steps+=(c->path[0][i][0]!=2 && c->path[0][i][1]!=2 && (c->path[0][i][0] || c->path[0][i][1]));
            for (unsigned i=0;i<11;++i) orders+=c->orders[i]!=255;
            printf("%s,%u,%d,%d,%d,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u\n",definition->id,unit.record[16],
                btp_combat_points(&unit,0),btp_combat_points(&unit,1),btp_combat_points(&unit,2),lrm,preferred,
                hot*20,empty,distances[q],btp_combat_distance(32,64,32+(int)distances[q],64),c->movement,c->goal_x,c->goal_y,steps,orders);
        }
    }
    free(r);return 0;
}
