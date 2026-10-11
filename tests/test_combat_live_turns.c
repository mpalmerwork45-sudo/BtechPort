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
        if (line[0]=='P') {
            char *p=line+1;unsigned group=number(&p),direction=number(&p),count=number(&p);++cases;
            if (group==18) {
                if (count!=3) return 2;
                for (unsigned i=0;i<3;++i) if (250u+r->combat.impact[i]!=number(&p)) ++failures;
                continue;
            }
            if (group>=18 || direction>7 || count>8) return 2;
            if (r->combat.poses[group][direction][0]!=count) ++failures;
            for (unsigned i=0;i<count;++i) if (r->combat.poses[group][direction][i+1]!=number(&p)) ++failures;
            continue;
        }
        if (line[0]=='G') {
            char *p=line+1;unsigned infantry=number(&p),direction=number(&p),count=number(&p);++cases;
            unsigned frame=0,previous=8;
            for (unsigned i=0;i<count;++i) {
                frame=btp_combat_walk_frame(frame,previous,direction,(int)infantry);previous=direction;
                if (frame!=number(&p)) ++failures;
            }
            continue;
        }
        if (line[0]=='F') {
            char *p=line+1;unsigned seed=number(&p),kind=number(&p),x=number(&p),y=number(&p),next=number(&p);
            unsigned after=number(&p),sprite=number(&p),mx=number(&p),my=number(&p),rng=number(&p),unchanged=number(&p);
            BtpState s;btp_start(&s);BtpCombatUnit target={.x=(uint8_t)x,.y=(uint8_t)y,.infantry=(uint8_t)kind};
            s.terrain_next=(uint8_t)next;s.npc.rng[0]=(uint8_t)seed;
            s.npc.rng[1]=(uint8_t)(seed>>8);s.npc.rng[2]=(uint8_t)(seed>>16);
            btp_combat_ignite(&s,&target);BtpTerrainMark *mark=&s.terrain_marks[next];++cases;
            if (s.terrain_next!=after || mark->sprite!=sprite || mark->x!=mx || mark->y!=my || !unchanged ||
                s.npc.rng[0]+256u*s.npc.rng[1]+65536u*s.npc.rng[2]!=rng) ++failures;
            uint8_t bytes[BTP_STATE_BYTES],again[BTP_STATE_BYTES];BtpState restored;
            btp_state_encode(&s,bytes);
            if (!btp_state_decode(bytes,sizeof bytes,&r->map,&r->citadel,&restored)) ++failures;
            else {
                btp_state_encode(&restored,again);if (memcmp(bytes,again,sizeof bytes)) ++failures;
                BtpState untouched=restored;bytes[2048]=64;
                if (btp_state_decode(bytes,sizeof bytes,&r->map,&r->citadel,&restored) ||
                    memcmp(&untouched,&restored,sizeof restored)) ++failures;
            }
            continue;
        }
        if (line[0]=='Q') {
            char *p=line+1;unsigned loan=number(&p),mode=number(&p),heat=number(&p),count=number(&p);
            BtpState s;btp_start(&s);s.mode=BTP_MISSION;s.mission.phase=BTP_MISSION_DRIVE;
            s.mission.assignment=2;s.story_flags[2]=(uint8_t)loan;btp_combat_begin(&s,r);
            BtpCombatState *c=&s.combat;c->phase=BTP_COMBAT_MENU;c->selected=9;c->graphics=0;
            c->unit[0].x=96;c->unit[0].y=93;c->unit[0].heat=(uint8_t)heat;
            c->unit[1].x=120;c->unit[1].y=120;
            for (unsigned i=0;i<count;++i) {
                unsigned x=number(&p),y=number(&p);if (!btp_combat_waypoint(c,x,y,mode)) return 2;
            }
            btp_combat_tick(&s,r,BTP_ACCEPT);uint64_t path=fingerprint((const uint8_t *)c->path[0],24);
            while (c->phase==BTP_COMBAT_ROUND) btp_combat_tick(&s,r,BTP_IDLE);
            p=strchr(p,'|');if (!p) return 2;++p;++cases;
            unsigned x=number(&p),y=number(&p),h=number(&p),movement=number(&p),remaining=number(&p);
            uint64_t expected=strtoull(p,&p,16);
            if (c->unit[0].x!=x || c->unit[0].y!=y || c->unit[0].heat!=h || c->movement!=movement ||
                (c->goal_active ? 1u+c->waypoint_count : 0u)!=remaining || path!=expected) {
                fprintf(stderr,"Queue case %u: got %u,%u heat%u mode%u remaining%u path%016" PRIx64
                    " expected %u,%u heat%u mode%u remaining%u path%016" PRIx64 "\n",cases,
                    c->unit[0].x,c->unit[0].y,c->unit[0].heat,c->movement,c->goal_active ? 1u+c->waypoint_count : 0u,
                    path,x,y,h,movement,remaining,expected);++failures;
            }
            for (unsigned i=0;i<remaining;++i) {
                x=number(&p);y=number(&p);
                if ((i ? c->waypoint_x[i-1] : c->goal_x)!=x || (i ? c->waypoint_y[i-1] : c->goal_y)!=y) ++failures;
            }
            continue;
        }
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
        for (unsigned tick=0;tick<512 && c->phase==BTP_COMBAT_ROUND;++tick) btp_combat_tick(&s,r,BTP_IDLE);
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
    fclose(f);free(r);printf("Combat: %u original comparison cases, %u failures\n",cases,failures);
    return failures ? 1 : 0;
}
