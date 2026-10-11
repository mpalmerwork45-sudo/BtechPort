#include "core/combat.h"
#include "core/npc.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>

static uint64_t fingerprint(const uint8_t *bytes,size_t n)
{
    uint64_t h=UINT64_C(14695981039346656037);
    for (size_t i=0;i<n;++i) h=(h^bytes[i])*UINT64_C(1099511628211);
    return h;
}
int main(int argc,char **argv)
{
    if (argc!=4) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError error;
    if (!r || !btp_resources_load(argv[1],r,&error) || !btp_combat_data_load(argv[2],&r->combat,&error)) return 2;
    FILE *f=fopen(argv[3],"r");if (!f) return 2;
    BtpState s;btp_start(&s);s.mode=BTP_MISSION;s.mission.assignment=2;s.mission.phase=BTP_MISSION_DRIVE;
    btp_combat_begin(&s,r);s.combat.phase=BTP_COMBAT_MENU;s.combat.selected=9;s.combat.graphics=0;
    s.combat.unit[1].y=89;memcpy(s.npc.rng,(uint8_t[]){70,54,210},3);
    char line[256];unsigned turns=0,failures=0;
    while (fgets(line,sizeof line,f)) {
        if (line[0]=='#') continue;
        unsigned x,y;
        if (line[0]=='W' && sscanf(line+1,"%u %u",&x,&y)==2) {
            s.combat.goal_active=1;s.combat.movement=0;s.combat.goal_x=(uint8_t)x;s.combat.goal_y=(uint8_t)y;
        } else if (line[0]=='F' && sscanf(line+1,"%u",&x)==1 && x<11) s.combat.orders[x]=12;
        else if (line[0]=='T') {
            unsigned px,py,pd,ph,tx,ty,td,th,seed;uint64_t player,target;
            if (sscanf(line+1,"%u %u %u %u %" SCNx64 " %u %u %u %u %" SCNx64 " %u",
                &px,&py,&pd,&ph,&player,&tx,&ty,&td,&th,&target,&seed)!=11) return 2;
            btp_combat_tick_reference(&s,r,BTP_ACCEPT);
            for (unsigned t=0;s.combat.phase==BTP_COMBAT_ROUND && t<64;++t) btp_combat_tick_reference(&s,r,BTP_IDLE);
            unsigned rng=s.npc.rng[0]+256u*s.npc.rng[1]+65536u*s.npc.rng[2];
            BtpCombatUnit *p=&s.combat.unit[0],*e=&s.combat.unit[1];++turns;
            if (p->x!=px || p->y!=py || p->direction!=pd || p->heat!=ph || fingerprint(p->record,125)!=player ||
                e->x!=tx || e->y!=ty || e->direction!=td || e->heat!=th || fingerprint(e->record,125)!=target || rng!=seed) {
                fprintf(stderr,"Turn %u got %u,%u dir%u heat%u %016" PRIx64 " / %u,%u dir%u heat%u %016" PRIx64 " RNG %u event%u\nexpected %s",
                    turns,p->x,p->y,p->direction,p->heat,fingerprint(p->record,125),e->x,e->y,e->direction,e->heat,fingerprint(e->record,125),rng,s.combat.last_event,line);
                if (++failures>=3) break;
            }
        } else return 2;
    }
    fclose(f);free(r);printf("Combat flow: %u original turns, %u failures, won=%u\n",turns,failures,s.combat.won);
    return failures ? 1 : 0;
}
