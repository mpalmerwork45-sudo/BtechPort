#include "core/combat.h"
#include "core/audio.h"
#include "core/party.h"
#include "data/save.h"
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static uint64_t hash(const uint8_t *b,unsigned n)
{
    uint64_t h=UINT64_C(14695981039346656037);
    for (unsigned i=0;i<n;++i) h=(h^b[i])*UINT64_C(1099511628211);
    return h;
}
int main(int argc,char **argv)
{
    if (argc!=2) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError e;
    if (!r || !btp_resources_load(argv[1],r,&e) || !btp_combat_data_load("work/combat-data.bin",&r->combat,&e)) return 2;
    if (!btp_world_data_load("work/world-data.bin",&r->world,&e)) return 2;
    memset(r->map.tiles,64,4096);
    FILE *f=fopen("tests/fixtures/mixed-encounters-primary.txt","r");if (!f) { free(r);return 2; }
    FILE *trace=getenv("BTP_MIXED_TRACE") ? fopen("work/m4-audit/mixed-native.txt","w") : NULL;
    BtpState s={0};unsigned case_id=0,failures=0,turns=0,units=0,checks=0;char line[256];
    while (fgets(line,sizeof line,f)) {
        if (line[0]=='B') {
            unsigned seed,weak,friends,count;
            if (sscanf(line+1,"%u %u %u %u %u",&case_id,&seed,&weak,&friends,&count)!=5) return 2;
            btp_start(&s);btp_party_init(&s);s.mode=BTP_ENCOUNTER;s.campaign.encounter=1;
            s.campaign.battle_x=s.campaign.battle_y=1536;
            s.combat=(BtpCombatState){.phase=BTP_COMBAT_MENU,.selected=9,.messages=2,.movement=255,.kick_target=255,
                .enemy_movement=255,.friends=(uint8_t)friends,.count=(uint8_t)count,.target_unit=(uint8_t)friends};
            for (unsigned i=0;i<8;++i) {
                const uint8_t dex[]={9,10,7,12,10,0,0,0};
                uint8_t p[17]={(uint8_t)(i<5 ? i : 255u),8,dex[i],7,2,2,2,2,(uint8_t)(i<2),0,0,
                    (uint8_t)(i==3 ? 13u : 9u),(uint8_t)(i==0 || i==4 ? 0u : i==1 ? 1u : 8u),1,25,80,0};
                memcpy(s.party.people[i],p,17);
            }
            s.combat.automatic=UINT32_MAX;
            memset(s.combat.orders,255,11);memset(s.combat.enemy_orders,255,sizeof s.combat.enemy_orders);
            memset(s.combat.enemy_modes,255,sizeof s.combat.enemy_modes);
            for (unsigned i=0;i<count;++i) { s.combat.plans[i].movement=s.combat.plans[i].kick=255;memset(s.combat.plans[i].orders,255,11); }
            s.npc.rng[0]=(uint8_t)seed;s.npc.rng[1]=(uint8_t)(seed>>8);s.npc.rng[2]=(uint8_t)(seed>>16);
            units=0;(void)weak;
        } else if (line[0]=='I') {
            unsigned id,kind,x,y,direction,weapon;
            if (sscanf(line+1,"%u %u %u %u %u %u",&id,&kind,&x,&y,&direction,&weapon)!=6 || units>=24) return 2;
            BtpCombatUnit *u=&s.combat.unit[units];u->x=(uint8_t)x;u->y=(uint8_t)y;u->direction=(uint8_t)direction;
            s.combat.ids[units]=(uint8_t)id;s.combat.plan_direction[units]=s.combat.fallback[units]=(uint8_t)direction;
            if (kind<4) {
                memcpy(u->record,kind==3 ? r->combat.commando : r->combat.loans[kind],125);
                u->record[121]=(uint8_t)(id<4 ? id : 0u);u->record[122]=(uint8_t)(id==0 ? 4u : 255u);
                if ((!case_id && id<2) || (case_id && id>=12)) memset(u->record+17,1,19);
                if (id<4) memcpy(btp_party_mech(&s,id),u->record,125);
            } else {
                u->infantry=1;
                if (id<12) memcpy(u->record,s.party.people[id-4],17);
                else { u->record[1]=8;u->record[11]=(uint8_t)weapon;u->record[12]=8;u->record[15]=80; }
            }
            ++units;
        } else if (line[0]=='T') {
            unsigned turn,rng,count;
            if (sscanf(line+1,"%u %u %u %u",&case_id,&turn,&rng,&count)!=4) return 2;
            s.combat.phase=BTP_COMBAT_MENU;s.combat.selected=9;
            btp_combat_tick(&s,r,BTP_ACCEPT);
            for (unsigned t=0;t<8192 && s.combat.phase==BTP_COMBAT_ROUND;++t) {
                btp_combat_tick(&s,r,BTP_IDLE);btp_audio_samples(&s.audio,r,BTP_AUDIO_TICK_SAMPLES,NULL);
            }
            if (trace) for (unsigned i=0;i<s.combat.count;++i) {
                fprintf(trace,"%u %u %u ",case_id,turn,btp_combat_id(&s.combat,i));
                for (unsigned b=0;b<(s.combat.unit[i].infantry ? 17u : 125u);++b) fprintf(trace,"%02x",s.combat.unit[i].record[b]);
                fputc('\n',trace);
            }
            ++turns;++checks;
            unsigned actual=s.npc.rng[0]+256u*s.npc.rng[1]+65536u*s.npc.rng[2];
            if (actual!=rng || s.combat.count!=count) { fprintf(stderr,"Mixed case %u turn %u rng %u/%u count %u/%u\n",case_id,turn,actual,rng,s.combat.count,count);++failures; }
        } else if (line[0]=='U') {
            unsigned id,x,y,face,heat;uint64_t expected;
            if (sscanf(line+1,"%u %u %u %u %u %" SCNx64,&id,&x,&y,&face,&heat,&expected)!=6) return 2;
            unsigned at=btp_combat_target(&s.combat,id);++checks;if (at>=s.combat.count) { ++failures;continue; }
            const BtpCombatUnit *u=&s.combat.unit[at];uint64_t actual=hash(u->record,u->infantry ? 17u : 125u);
            if (actual!=expected || (u->record[0]!=255 && (u->x!=x || u->y!=y || u->direction!=face || u->heat!=heat))) {
                fprintf(stderr,"Mixed case %u round %u ID %u got %u,%u face%u heat%u %016" PRIx64 " expected %u,%u face%u heat%u %016" PRIx64 "\n",case_id,s.combat.round,id,u->x,u->y,u->direction,u->heat,actual,x,y,face,heat,expected);++failures;
            }
        }
    }
    if (trace) fclose(trace);
    fclose(f);free(r);printf("Mixed encounters: %u turns, %u numeric comparisons, %u differences\n",turns,checks,failures);return failures!=0;
}
