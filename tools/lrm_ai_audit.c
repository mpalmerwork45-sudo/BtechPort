/* Updated policy comparison on declared open-ground prerequisites. This is
   an authored tactics/balance audit, not an observation of original DOS. */
#include "core/combat.h"
#include "core/combat_ai.h"
#include "data/content.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static unsigned hull(const BtpCombatUnit *u)
{
    unsigned total=0;for (unsigned i=17;i<38;++i) total+=u->record[i];return total;
}
static unsigned ammo(const BtpCombatUnit *u)
{
    unsigned total=0;for (unsigned i=39;i<49;++i) if (u->record[i]!=255) total+=u->record[i];return total;
}
static void profile(BtpState *s,const BtpResources *r,unsigned enhanced)
{
    s->combat_profile=(uint8_t)enhanced;s->combat_fingerprint=enhanced ? r->combat_profile.fingerprint : 0;
}
static void scenario(const BtpResources *r,unsigned model,unsigned case_id,unsigned seed,unsigned policy)
{
    BtpState s;btp_start(&s);s.mode=BTP_MISSION;s.mission.phase=BTP_MISSION_DRIVE;
    s.mission.assignment=(uint8_t)(case_id==6 ? 2 : 4);s.story_flags[0]=s.mission.assignment;
    s.npc.rng[0]=(uint8_t)(31+seed*17);s.npc.rng[1]=(uint8_t)(77+seed*29);s.npc.rng[2]=(uint8_t)(13+seed*7);
    btp_combat_begin(&s,r);s.menu.sound=0;s.menu.speed=0;s.menu.outtakes=0;
    BtpCombatState *c=&s.combat;c->phase=BTP_COMBAT_MENU;c->graphics=0;c->automatic=1;c->auto_run=0;
    BtpCombatUnit *a=&c->unit[0],*t=&c->unit[1];
    memcpy(a->record,model<r->roster.count ? r->roster.mechs[model].record : r->combat.loans[0],125);
    if (model==r->roster.count) {
        /* Synthetic pure-LRM carrier, explicitly absent from the game pack. */
        memset(a->record+51,0,35);a->record[51]=a->record[52]=28;a->record[39]=a->record[40]=16;
    }
    memcpy(t->record,r->combat.jenner,125);a->x=40;a->y=64;t->x=(uint8_t)(case_id==0 ? 56 : case_id==3 ? 64 : 88);t->y=64;
    a->heat=(uint8_t)(case_id==3 ? 20 : 0);a->pool=0;
    if (case_id==2 || case_id==4) for (unsigned w=39;w<49;++w) if (a->record[w]!=255) a->record[w]=(uint8_t)(case_id==4);
    if (case_id==5) for (unsigned k=51;k<86;++k) if (a->record[k]>=26 && a->record[k]<=29) a->record[k]|=128;
    unsigned before_a=hull(a),before_t=hull(t),before_ammo=ammo(a),rounds=0,peak=a->heat,idle=0,oscillations=0;
    unsigned x[3]={a->x,a->x,a->x},y[3]={a->y,a->y,a->y};
    for (unsigned round=0;round<8 && c->phase==BTP_COMBAT_MENU;++round) {
        /* Middle comparison isolates order planning. It shares Enhanced
           numeric rules AND the live firing filter with the new planner. */
        profile(&s,r,policy==2);c->selected=9;btp_combat_tick(&s,r,BTP_ACCEPT);profile(&s,r,policy!=0);
        unsigned ticks=0;while (c->phase==BTP_COMBAT_ROUND && ticks++<4096) btp_game_tick(&s,r,BTP_IDLE);
        if (ticks>=4096) { fputs("Unbounded audit round\n",stderr);exit(1); }
        ++rounds;if (a->heat>peak) peak=a->heat;
        idle+=a->x==x[2] && a->y==y[2] && !c->fired;
        oscillations+=round>0 && a->x==x[1] && a->y==y[1] && (a->x!=x[2] || a->y!=y[2]);
        x[0]=x[1];x[1]=x[2];x[2]=a->x;y[0]=y[1];y[1]=y[2];y[2]=a->y;
    }
    printf("%s,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u\n",model<r->roster.count ? r->roster.mechs[model].id : "synthetic-pure-lrm",
        case_id,seed,policy,rounds,before_t-hull(t),before_a-hull(a),before_ammo-ammo(a),peak,idle,oscillations,
        btp_combat_distance(a->x,a->y,t->x,t->y),c->won,c->lost);
}
static int compare(const void *a,const void *b)
{
    double x=*(const double *)a,y=*(const double *)b;return (x>y)-(x<y);
}
static void benchmark(const BtpResources *r)
{
    BtpState base;btp_start(&base);profile(&base,r,1);base.combat.count=24;base.combat.friends=12;
    /* Deliberate upper-bound stress: all 24 actors carry the fullest mech
       loadouts, although normal parties also include cheaper infantry AI. */
    static const unsigned stress_models[]={21,14,20,2};
    for (unsigned i=0;i<24;++i) {
        BtpCombatUnit *u=&base.combat.unit[i];memcpy(u->record,r->roster.mechs[stress_models[i%4]].record,125);
        u->x=(uint8_t)(24+(i%6)*12);u->y=(uint8_t)(36+(i/6)*12);base.combat.ids[i]=(uint8_t)i;
        memset(base.combat.path[i],2,sizeof base.combat.path[i]);
    }
    double timings[31];unsigned candidates=0;
    for (unsigned repeat=0;repeat<31;++repeat) {
        BtpState s=base;clock_t begin=clock();
        for (unsigned actor=0;actor<24;++actor) {
            BtpAiPlan p;if (!btp_combat_ai_plan(&s,r,&r->map,actor,&p)) exit(1);
            memcpy(s.combat.path[actor],p.path,sizeof p.path);if (p.candidates>candidates) candidates=p.candidates;
        }
        timings[repeat]=(double)(clock()-begin)*1000.0/CLOCKS_PER_SEC;
    }
    qsort(timings,31,sizeof timings[0],compare);
    fprintf(stderr,"24-mech planning stress, 31 runs, CPU ms: median=%.3f p95=%.3f max=%.3f; candidates/actor<=%u\n",
        timings[15],timings[29],timings[30],candidates);
}
int main(int argc,char **argv)
{
    if (argc!=2) return 2;
    BtpContent content={0};BtpError error;
    BtpOriginalContentPaths paths={argv[1],"work/talk-data.bin","work/combat-data.bin","work/world-data.bin"};
    if (!btp_content_load_original(&content,&paths,&error) ||
        !btp_content_select(&content,BTP_CONTENT_UPDATED,"content/updated/roster.json",&error)) { fprintf(stderr,"%s\n",error.text);return 2; }
    BtpResources *r=content.resources;memset(r->map.tiles,64,sizeof r->map.tiles);
    puts("model,scenario,seed,policy,rounds,damage_dealt,damage_taken,ammo_used,peak_heat,idle_rounds,oscillations,final_distance,won,lost");
    static const unsigned models[]={2,4,10,14,15,16,21};
    for (unsigned model=0;model<8;++model) for (unsigned scenario_id=0;scenario_id<7;++scenario_id)
        for (unsigned seed=0;seed<8;++seed) for (unsigned policy=0;policy<3;++policy)
            scenario(r,model<7 ? models[model] : r->roster.count,scenario_id,seed,policy);
    benchmark(r);btp_content_close(&content);return 0;
}
