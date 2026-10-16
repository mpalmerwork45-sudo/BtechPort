#include "core/campaign.h"
#include "core/party.h"
#include "core/combat.h"
#include "data/save.h"
#include "frontend/pixels.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
static unsigned checks;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x);return 1; } } while (0)
static unsigned rng(const BtpState *s) { return s->npc.rng[0]+((unsigned)s->npc.rng[1]<<8)+((unsigned)s->npc.rng[2]<<16); }
static uint64_t hash(const uint8_t *p,size_t n) { uint64_t h=UINT64_C(14695981039346656037);for (size_t i=0;i<n;++i) h=(h^p[i])*UINT64_C(1099511628211);return h; }
static uint64_t panel(const uint32_t *f) {
    uint64_t h=UINT64_C(14695981039346656037);
    for (unsigned y=112;y<200;++y) for (unsigned x=104;x<320;++x) for (int shift=16;shift>=0;shift-=8)
        h=(h^(uint8_t)(f[y*320+x]>>shift))*UINT64_C(1099511628211);
    return h;
}
static int restore(BtpState *s,const BtpResources *r) {
    uint8_t a[BTP_STATE_BYTES],b[BTP_STATE_BYTES];BtpState t;
    btp_state_encode(s,a);if (!btp_state_decode(a,sizeof a,btp_active_map(r,s),btp_state_bld(r,s),&t)) return 0;
    btp_state_encode(&t,b);if (memcmp(a,b,sizeof a)) return 0;*s=t;return 1;
}
static void setup(BtpState *s,const BtpResources *r,unsigned slot) {
    btp_start(s);s->story_flags[4]=1;s->npc=(BtpNpcState){.rng={31,66,171}};s->map_id=0;s->mode=BTP_ENCOUNTER;
    s->campaign.world_x=320;s->campaign.world_y=333;s->campaign.battle_x=256;s->campaign.battle_y=256;s->campaign.owned=1;s->campaign.encounter=1;
    s->x_half=64;s->y_half=79;btp_party_init(s);s->party.mech_types[slot]='L';memcpy(btp_party_mech(s,slot),r->combat.loans[0],125);
    for (unsigned i=0;i<8;++i) { const uint8_t p[17]={(uint8_t)i,8,9,7,0,0,0,1,1,1,0,9,(uint8_t)slot,3,30,80,0};memcpy(s->party.people[i],p,17); }
    s->combat=(BtpCombatState){.phase=BTP_COMBAT_ROUND,.friends=1,.count=2,.target_unit=1,.last_target=1,.movement=255,.kick_target=255,.enemy_movement=255};
    BtpCombatState *c=&s->combat;memset(c->orders,255,11);memset(c->enemy_orders,255,sizeof c->enemy_orders);memset(c->enemy_modes,255,sizeof c->enemy_modes);
    c->ids[0]=(uint8_t)slot;c->ids[1]=12;
    for (unsigned i=0;i<2;++i) { memcpy(c->unit[i].record,r->combat.loans[0],125);c->unit[i].x=(uint8_t)(64+10*i);c->unit[i].y=77;c->plans[i].movement=255;c->plans[i].kick=255;memset(c->plans[i].orders,255,11); }
}
int main(int argc,char **argv) {
    if (argc!=2) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError e;CHECK(r);CHECK(btp_resources_load(argv[1],r,&e));CHECK(btp_combat_data_load("work/combat-data.bin",&r->combat,&e));
    FILE *f=fopen("tests/fixtures/aftermath-primary.txt","r");CHECK(f);char line[300];unsigned cases=0;
    while (fgets(line,sizeof line,f)) {
        BtpState s;btp_start(&s);
        if (line[0]=='R') { unsigned n,seed,amount,expected;CHECK(sscanf(line+1,"%u %u %u %u",&n,&seed,&amount,&expected)==4);for (unsigned i=0;i<3;++i) s.npc.rng[i]=(uint8_t)(seed>>(8*i));CHECK(btp_aftermath_cash(s.npc.rng,n)==amount);CHECK(rng(&s)==expected); }
        else if (line[0]=='S') { unsigned skill,v,yes;CHECK(sscanf(line+1,"%u %u %u",&skill,&v,&yes)==3);uint8_t m[125];memcpy(m,r->combat.loans[0],125);m[117]=v&1 ? 3 : 0;m[118]=v&2 ? 2 : 0;m[31]=v&4 ? 0 : 3;CHECK(btp_salvage_eligible(m,skill)==(int)yes); }
        else if (line[0]=='C') { unsigned loan,pilot,mount;uint64_t expected;CHECK(sscanf(line+1,"%u %u %" SCNx64 " %u",&loan,&pilot,&expected,&mount)==4);btp_party_init(&s);uint8_t m[125];memcpy(m,r->combat.loans[loan],125);unsigned kind=m[0];m[0]=255;m[117]=3;m[118]=2;m[31]=m[32]=0;btp_salvage_copy(&s,0,pilot,m,kind);CHECK(hash(s.campaign.mech,125)==expected);CHECK(s.party.people[pilot][12]==mount); }
        else if (line[0]=='E') { unsigned slot,pilot,second,v[10];CHECK(sscanf(line+1,"%u %u %u %u %u %u %u %u %u %u %u %u %u",&slot,&pilot,&second,&v[0],&v[1],&v[2],&v[3],&v[4],&v[5],&v[6],&v[7],&v[8],&v[9])==13);setup(&s,r,slot);s.combat.unit[0].record[121]=(uint8_t)pilot;s.combat.unit[0].record[122]=(uint8_t)second;unsigned seed=rng(&s);btp_campaign_destroy(&s,0);CHECK(s.combat.unit[0].record[0]==v[0]);CHECK(s.aftermath.wrecks[slot] && v[1]);btp_campaign_eject(&s);CHECK(rng(&s)==seed);
            for (unsigned crew=0;crew<2;++crew) { unsigned member=crew ? second : pilot;if (member==255) continue;unsigned at=btp_combat_target(&s.combat,4+member);CHECK(at<s.combat.friends);CHECK(s.combat.unit[at].record[12]==v[2+4*crew]);CHECK(s.combat.unit[at].record[0]!=255 && v[3+4*crew]);CHECK(s.combat.unit[at].x==v[4+4*crew] && s.combat.unit[at].y==v[5+4*crew]); }
            CHECK(restore(&s,r)); }
        else continue;
        ++cases;
    }fclose(f);CHECK(cases==114);
    BtpState s;setup(&s,r,0);s.combat.unit[0].record[121]=0;s.combat.unit[0].record[122]=1;btp_campaign_destroy(&s,0);btp_campaign_eject(&s);CHECK(s.combat.friends==3 && s.combat.count==4 && !s.effects.pending);CHECK(restore(&s,r));
    btp_campaign_destroy(&s,3);s.combat.phase=0;s.combat.won=1;btp_campaign_result(&s,r);CHECK(s.aftermath.phase==5);CHECK(restore(&s,r));
    btp_game_tick(&s,r,BTP_ACCEPT);CHECK(s.aftermath.phase==1);CHECK(restore(&s,r));CHECK(btp_save_write("work/aftermath-salvage.btp",&s,r,&e));
    for (unsigned guard=0;guard<30 && s.mode==BTP_ENCOUNTER;++guard) { btp_game_tick(&s,r,BTP_ACCEPT);CHECK(restore(&s,r)); }
    CHECK(s.mode==BTP_EXPLORE && s.campaign.mounted && s.party.people[0][12]<4);CHECK(s.campaign.mech[117]==1 && s.campaign.mech[118]==1);
    setup(&s,r,0);s.combat.unit[0].record[121]=0;s.combat.unit[0].record[122]=255;btp_campaign_destroy(&s,0);btp_campaign_eject(&s);unsigned j=btp_combat_target(&s.combat,4);btp_campaign_destroy(&s,j);CHECK(s.effects.pending==2);s.effects.pending=0;s.combat.phase=0;s.combat.lost=1;btp_campaign_result(&s,r);CHECK(s.mode==BTP_GAME_OVER && s.party.people[0][0]==255);CHECK(restore(&s,r));
    /* Hold every result boundary. Repairs happen after their announcement,
       cash after its own page, and recovery after looting, exactly once. */
    setup(&s,r,0);s.party.people[1][9]=2;s.party.people[2][10]=4;s.party.advanced_kit=1;
    s.party.people[3][15]=1;s.story_flags[41]=63;
    btp_campaign_destroy(&s,1);s.combat.phase=0;s.combat.won=1;unsigned cash=s.credits;
    btp_campaign_result(&s,r);CHECK(s.aftermath.phase==5 && restore(&s,r));
    btp_game_tick(&s,r,BTP_ACCEPT);CHECK(s.aftermath.phase==8 && s.credits==cash && restore(&s,r));
    btp_game_tick(&s,r,BTP_ACCEPT);CHECK(s.aftermath.phase==9 && s.aftermath.cash && s.credits==cash && restore(&s,r));
    unsigned reward=s.aftermath.cash;btp_game_tick(&s,r,BTP_IDLE);CHECK(s.credits==cash && restore(&s,r));
    btp_game_tick(&s,r,BTP_ACCEPT);CHECK(s.credits==cash+reward && s.aftermath.phase==10 && restore(&s,r));
    unsigned hp=s.party.people[3][15];CHECK(hp>1 && s.service.amount==8);
    btp_game_tick(&s,r,BTP_IDLE);CHECK(s.credits==cash+reward && s.party.people[3][15]==hp && restore(&s,r));
    btp_game_tick(&s,r,BTP_ACCEPT);CHECK(s.aftermath.phase==7 && restore(&s,r));
    btp_game_tick(&s,r,BTP_ACCEPT);CHECK(s.mode==BTP_EXPLORE && s.credits==cash+reward && restore(&s,r));
    /* Recovered weapons replace a gun and offer the displaced gun again;
       the explicit Drop it row terminates that exchange, including reload. */
    setup(&s,r,0);s.combat.phase=0;s.combat.won=1;s.combat.ids[1]=16;s.combat.unit[1].infantry=1;
    memset(s.combat.unit[1].record,0,125);memcpy(s.combat.unit[1].record,s.party.people[0],17);
    s.combat.unit[1].record[0]=255;s.combat.unit[1].record[11]=7;
    s.aftermath=(BtpAftermathState){.phase=4,.applied=1,.unit=16};s.aftermath.wrecks[16]=128;
    btp_aftermath_input(&s,r,BTP_ACCEPT);CHECK(s.party.people[0][11]==7 && s.combat.unit[1].record[11]==9 && s.aftermath.phase==4 && restore(&s,r));
    btp_aftermath_input(&s,r,BTP_CANCEL);CHECK(!s.aftermath.phase && s.aftermath.unit==24 && restore(&s,r));
    CHECK(btp_dialogue_load("work/talk-data.bin",&r->dialogue,&e));
    /* Full original salvage loops: retries happen inside one accepted offer,
       and every held result (including the final no-wreck page) survives save. */
    f=fopen("tests/fixtures/salvage-primary.txt","r");CHECK(f);unsigned loops=0,pages=0,attempt=0;
    while (fgets(line,sizeof line,f)) {
        if (line[0]=='C') {
            unsigned id,skill,damage,answers,seed;
            CHECK(sscanf(line+1,"%u %u %u %u %u",&id,&skill,&damage,&answers,&seed)==5);
            setup(&s,r,0);s.combat.phase=0;s.combat.won=1;s.combat.friends=3;s.combat.count=6;
            for (unsigned i=0;i<3;++i) s.npc.rng[i]=(uint8_t)(seed>>(8*i));
            for (unsigned p=0;p<8;++p) {
                const uint8_t person[17]={(uint8_t)(p<3 ? p : 255),8,9,7,0,0,0,1,1,(uint8_t)(p==1 ? skill : 0),0,9,8,3,30,80,0};
                memcpy(s.party.people[p],person,17);
            }
            for (unsigned bay=0;bay<4;++bay) { memset(btp_party_mech(&s,bay),0,125);btp_party_mech(&s,bay)[0]=255;s.party.mech_types[bay]=255; }
            s.aftermath=(BtpAftermathState){.phase=1,.applied=2};
            const uint8_t ids[3]={12,13,15};
            for (unsigned i=0;i<3;++i) {
                s.combat.ids[i]=(uint8_t)(4+i);s.combat.unit[i]=(BtpCombatUnit){.infantry=1,.x=64,.y=64};
                memcpy(s.combat.unit[i].record,s.party.people[i],17);
                s.combat.ids[3+i]=ids[i];s.combat.unit[3+i]=(BtpCombatUnit){.x=74,.y=64};
                uint8_t *m=s.combat.unit[3+i].record;memcpy(m,r->combat.loans[i],125);
                s.aftermath.wrecks[ids[i]]=m[0];m[0]=255;
                if (damage&(1u<<i)) { m[117]=3;m[118]=2;m[31]=m[32]=0; }
            }
            ++loops;
        } else if (line[0]=='Q') {
            unsigned pilot,answer;CHECK(sscanf(line+1,"%u %u",&pilot,&answer)==2);
            CHECK(s.aftermath.phase==1 && s.aftermath.pilot==pilot && restore(&s,r));
            btp_aftermath_input(&s,r,answer ? BTP_ACCEPT : BTP_CANCEL);attempt=0;
        } else if (line[0]=='A') {
            unsigned pilot,id,eligible;CHECK(sscanf(line+1,"%u %u %u",&pilot,&id,&eligible)==3);
            CHECK(s.aftermath.phase==2 && s.aftermath.pilot==pilot && attempt<s.aftermath.attempts);
            CHECK(s.aftermath.inspected[attempt]==id);
            CHECK(eligible==(unsigned)(attempt+1==s.aftermath.attempts && !s.aftermath.notice));++attempt;
        } else if (line[0]=='W') {
            uint64_t expected,pixels;uint8_t message[1024];CHECK(sscanf(line+1,"%" SCNx64 " %" SCNx64,&expected,&pixels)==2);
            CHECK(s.aftermath.phase==2 && restore(&s,r));size_t n=btp_salvage_text(r,&s,message);
            /* Bank strings carry an ignored BLD delimiter absent from the
               original far-string calls observed by the numeric harness. */
            size_t raw_n=0;for (size_t i=0;i<n;++i) if (message[i]!=1) message[raw_n++]=message[i];n=raw_n;
            if (hash(message,n)!=expected) fprintf(stderr,"Salvage loop %u text: %.*s\n",loops,(int)n,(char *)message);
            CHECK(hash(message,n)==expected);
            uint32_t frame[BTP_PIXELS];btp_render(r,&s,0,frame);uint64_t actual=UINT64_C(14695981039346656037);
            for (unsigned y=120;y<192;++y) for (unsigned x=112;x<312;++x) for (int shift=16;shift>=0;shift-=8)
                actual=(actual^(uint8_t)(frame[y*320+x]>>shift))*UINT64_C(1099511628211);
            if (actual!=pixels) { fprintf(stderr,"Salvage loop %u pixels %016" PRIx64 "/%016" PRIx64 "\n",loops,actual,pixels);btp_write_ppm("work/m4-audit/salvage-failed.ppm",frame); }
            CHECK(actual==pixels);++pages;btp_aftermath_input(&s,r,BTP_ACCEPT);
        } else if (line[0]=='Z') {
            unsigned expected_rng,mask;uint64_t people,mechs;uint8_t records[500];
            CHECK(sscanf(line+1,"%u %" SCNx64 " %" SCNx64 " %u",&expected_rng,&people,&mechs,&mask)==4);
            for (unsigned i=0;i<4;++i) memcpy(records+125*i,btp_party_mech(&s,i),125);
            unsigned left=0;for (unsigned i=0;i<16;++i) if (s.aftermath.wrecks[i]) left|=1u<<i;
            CHECK(!s.aftermath.phase && rng(&s)==expected_rng && left==mask);
            CHECK(hash(s.party.people[0],8*17)==people && hash(records,sizeof records)==mechs);
        } else CHECK(0);
    }
    fclose(f);CHECK(loops==384 && pages==552);
    uint8_t raw[BTP_ORIGINAL_BYTES];f=fopen("Original DOS/GAME3","rb");CHECK(f && fread(raw,1,sizeof raw,f)==sizeof raw && !fclose(f));
    f=fopen("tests/fixtures/aftermath-ui-primary.txt","r");CHECK(f);unsigned screens=0;uint32_t frame[BTP_PIXELS];
    while (fgets(line,sizeof line,f)) {
        unsigned phase;uint64_t expected;CHECK(sscanf(line,"P %u %" SCNx64,&phase,&expected)==2);
        CHECK(btp_original_decode(raw,sizeof raw,&s,r,&e));s.mode=BTP_ENCOUNTER;s.campaign.encounter=1;
        s.combat=(BtpCombatState){.count=2,.friends=1};s.combat.ids[0]=0;s.combat.ids[1]=16;s.combat.unit[1].infantry=1;s.combat.unit[1].record[11]=9;
        s.aftermath=(BtpAftermathState){.phase=(uint8_t)phase,.applied=2,.pilot=1,.unit=16,.notice=1,.selected=3,.cash=(uint16_t)(phase==9 ? 216 : 71)};
        s.aftermath.wrecks[12]='L';s.party.people[1][9]=2;
        if (phase==1) { s.aftermath.pilot=3;s.aftermath.selected=0;s.party.people[3][12]=8;s.party.people[3][8]=1;s.party.people[1][9]=4; }
        const uint8_t weapons[4]={9,7,7,4};for (unsigned i=0;i<4;++i) s.party.people[i][11]=weapons[i];
        btp_render(r,&s,0,frame);
        if (panel(frame)!=expected) { fprintf(stderr,"Aftermath panel phase %u: %016" PRIx64 " != %016" PRIx64 "\n",phase,panel(frame),expected);btp_write_ppm("work/aftermath-panel.ppm",frame); }
        CHECK(panel(frame)==expected);++screens;
    }
    fclose(f);CHECK(screens==6);
    f=fopen("tests/fixtures/salvage-live-primary.txt","r");CHECK(f);unsigned live=0;
    while (fgets(line,sizeof line,f)) {
        unsigned notice;uint64_t expected;CHECK(sscanf(line,"L %u %" SCNx64,&notice,&expected)==2);
        setup(&s,r,0);s.combat.phase=0;s.combat.won=1;
        for (unsigned i=0;i<8;++i) { s.party.people[i][9]=0;if (i!=0 && i!=3) s.party.people[i][0]=255; }
        s.party.people[3][0]=4;s.party.people[3][9]=(uint8_t)(notice ? 3 : 4);s.party.people[3][12]=8;
        memcpy(s.combat.unit[1].record,r->combat.loans[1],125);s.combat.unit[1].record[0]=255;
        s.aftermath=(BtpAftermathState){.phase=2,.applied=2,.pilot=3,.unit=12,.cash='W',.notice=(uint8_t)notice,
            .attempts=1,.inspected={12},.models={'W'}};
        CHECK(restore(&s,r));btp_render(r,&s,0,frame);
        if (panel(frame)!=expected) fprintf(stderr,"Live salvage %u pixels %016" PRIx64 "/%016" PRIx64 "\n",notice,panel(frame),expected);
        CHECK(btp_write_ppm("work/m4-audit/salvage-live-native.ppm",frame));CHECK(panel(frame)==expected);++live;
        char path[80];snprintf(path,sizeof path,"work/m4-audit/salvage-live-%u.btp",notice);CHECK(btp_save_write(path,&s,r,&e));
    }
    CHECK(!fclose(f) && live==3);
    free(r);printf("PASS: %u checks; %u primary aftermath cases, %u original panels, %u full salvage loops/%u held pages and saved crew survival/loss\n",checks,cases,screens,loops,pages);return 0;
}
