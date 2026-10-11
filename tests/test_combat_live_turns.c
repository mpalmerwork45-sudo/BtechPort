#include "core/combat.h"
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint64_t fingerprint(const uint8_t *b, unsigned n)
{
    uint64_t h=UINT64_C(14695981039346656037);
    for (unsigned i=0;i<n;++i) h=(h^b[i])*UINT64_C(1099511628211);
    return h;
}
static unsigned number(char **p) { unsigned n=(unsigned)strtoul(*p,p,10);return n; }
int main(int argc,char **argv)
{
    if (argc!=4) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError error;
    if (!r || !btp_resources_load(argv[1],r,&error) || !btp_combat_data_load(argv[2],&r->combat,&error)) return 2;
    FILE *f=fopen(argv[3],"r");if (!f) return 2;
    char line[2048];unsigned cases=0,failures=0;
    while (fgets(line,sizeof line,f)) {
        if (line[0]=='#') continue;
        char *p=line+1;unsigned assignment=number(&p),loan=number(&p),seed=number(&p),count=number(&p);
        unsigned movement=number(&p),gx=number(&p),gy=number(&p),order=number(&p);
        if (count<2 || count>BTP_COMBAT_UNITS || loan>2) return 2;
        BtpState s;btp_start(&s);s.mode=BTP_MISSION;s.mission.phase=BTP_MISSION_DRIVE;
        s.mission.assignment=(uint8_t)assignment;s.story_flags[2]=(uint8_t)loan;
        btp_combat_begin(&s,r);BtpCombatState *c=&s.combat;c->count=(uint8_t)count;
        c->phase=BTP_COMBAT_MENU;c->selected=9;c->graphics=0;
        c->movement=(uint8_t)movement;c->goal_active=(uint8_t)(movement!=255);
        c->goal_x=(uint8_t)gx;c->goal_y=(uint8_t)gy;
        for (unsigned i=0;i<count;++i) {
            BtpCombatUnit *u=&c->unit[i];u->x=(uint8_t)number(&p);u->y=(uint8_t)number(&p);
            u->direction=(uint8_t)number(&p);u->heat=(uint8_t)number(&p);
            unsigned weapon=number(&p),body=number(&p);
            c->plan_direction[i]=c->fallback[i]=u->direction;
            if (i && assignment==3) {
                memset(u->record,0,sizeof u->record);u->infantry=1;u->record[1]=(uint8_t)body;
                u->record[11]=(uint8_t)weapon;u->record[12]=8;u->record[15]=(uint8_t)(10*body);
            }
        }
        unsigned weapons=order==0 ? 1 : order==1 ? 11 : 0;
        for (unsigned w=0;w<weapons;++w) c->orders[w]=(uint8_t)btp_combat_id(c,1);
        if (order==2) c->kick_target=(uint8_t)btp_combat_id(c,1);
        s.npc.rng[0]=(uint8_t)seed;s.npc.rng[1]=(uint8_t)(seed>>8);s.npc.rng[2]=(uint8_t)(seed>>16);
        btp_combat_tick(&s,r,BTP_ACCEPT);
        for (unsigned tick=0;tick<64 && c->phase==BTP_COMBAT_ROUND;++tick) btp_combat_tick(&s,r,BTP_IDLE);
        p=strchr(p,'|');if (!p) return 2;++p;++cases;
        for (unsigned i=0;i<count;++i) {
            unsigned x=number(&p),y=number(&p),direction=number(&p),heat=number(&p);
            uint64_t hash=strtoull(p,&p,16);BtpCombatUnit *u=&c->unit[i];
            uint64_t actual=fingerprint(u->record,u->infantry ? 17u : 125u);
            if (x!=u->x || y!=u->y || direction!=u->direction || heat!=u->heat || hash!=actual) {
                fprintf(stderr,"Case %u unit %u: got %u,%u dir%u heat%u %016" PRIx64
                    " expected %u,%u dir%u heat%u %016" PRIx64 "\n",cases,i,u->x,u->y,u->direction,u->heat,
                    actual,x,y,direction,heat,hash);++failures;
            }
        }
        unsigned expected=number(&p),actual=s.npc.rng[0]+256u*s.npc.rng[1]+65536u*s.npc.rng[2];
        if (actual!=expected) { fprintf(stderr,"Case %u RNG got%u expected%u\n",cases,actual,expected);++failures; }
        if (failures>=8) break;
    }
    fclose(f);free(r);printf("Live combat: %u complete original turns, %u failures\n",cases,failures);
    return failures ? 1 : 0;
}
