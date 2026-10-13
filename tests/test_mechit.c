#include "core/service.h"
#include "core/party.h"
#include "data/save.h"
#include "frontend/pixels.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
static unsigned checks;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x);exit(1); } } while (0)
static uint64_t hash(const uint8_t *b,size_t n)
{
    uint64_t h=UINT64_C(14695981039346656037);for (size_t i=0;i<n;++i) h=(h^b[i])*UINT64_C(1099511628211);return h;
}
static uint64_t region(const uint32_t *f,unsigned x,unsigned y,unsigned width,unsigned height)
{
    uint64_t h=UINT64_C(14695981039346656037);
    for (unsigned row=y;row<y+height;++row) for (unsigned col=x;col<x+width;++col)
        for (int shift=16;shift>=0;shift-=8) h=(h^(uint8_t)(f[row*320+col]>>shift))*UINT64_C(1099511628211);
    return h;
}
static void damaged_record(uint8_t *m,unsigned shape)
{
    if (!shape) {
        m[17]=(uint8_t)(m[86]>3 ? m[86]-3 : 0);m[28]=(uint8_t)(m[97]>2 ? m[97]-2 : 0);
        for (unsigned i=51;i<86;++i) if (m[i]>=16 && m[i]<=32) { m[i]|=128;break; }
        for (unsigned i=51;i<86;++i) if (m[i]==34) { m[i]|=128;break; }
        m[36]=(uint8_t)(m[105] ? m[105]-1 : 0);
        for (unsigned i=39;i<49;++i) if (m[i]!=255) m[i]=0;
    } else {
        memcpy(m+17,m+86,21);memset(m+51,0,35);
        if (shape==1) { m[51]=m[52]=145;m[65]=146;m[58]=162; }
        else if (shape==2) m[51]=m[52]=160;
        else if (shape<7) {
            m[51]=24;m[52]=31;m[65]=17;m[79]=24;
            const uint8_t ammo[10]={0,0,255,0,255,255,255,255,255,255};
            const uint8_t capacity[10]={5,3,255,5,255,255,255,255,255,255};
            memcpy(m+39,ammo,10);memcpy(m+107,capacity,10);
            if (shape==4) m[65]|=128;
            if (shape==5) m[51]|=128;
            if (shape==6) m[79]|=128;
        } else {
            memset(m+117,0,3);if (shape<10) m[117+shape-7]=1;
        }
    }
}
static void setup(BtpState *s,const BtpResources *r,const char *kind)
{
    uint8_t raw[BTP_ORIGINAL_BYTES];FILE *f=fopen("Original DOS/GAME3","rb");CHECK(f);
    CHECK(fread(raw,1,sizeof raw,f)==sizeof raw && !fclose(f));
    raw[0xf45]=20;raw[0xf46]=10;raw[0xf47]=69;raw[0xf48]=128;
    raw[0xcf9+24]=(uint8_t)!strcmp(kind,"recruit");raw[0xcf9+36]=127;raw[0xcf9+39]=0;
    for (unsigned i=0;i<8;++i) raw[1+17*i+12]=8;
    for (unsigned i=0;i<4;++i) {
        unsigned at=0x111+125*i,type=1+0xd452-0xc614+i;
        if (raw[type]!=255) { raw[at]=raw[type];raw[type]=255; }
        if (raw[at]!=255) {
            if (!strcmp(kind,"gyro")) {
                memcpy(raw+at+17,raw+at+86,21);
                for (unsigned j=51;j<86;++j) raw[at+j]&=127;
                memset(raw+at+117,0,3);if (i==2) raw[at+118]=1;
            } else damaged_record(raw+at,0);
        }
    }
    if (!strcmp(kind,"apprentice")) { raw[17]&=254;raw[0x111+125+124]=0; }
    BtpError e;CHECK(btp_original_decode(raw,sizeof raw,s,r,&e));
}
static void step(BtpState *s,const BtpResources *r,BtpAction a)
{
    uint8_t before[BTP_STATE_BYTES],after[BTP_STATE_BYTES];BtpState copy;
    btp_state_encode(s,before);
    if (!btp_state_decode(before,sizeof before,btp_active_map(r,s),btp_state_bld(r,s),&copy))
        fprintf(stderr,"Mechit save phase %u action %u kind %u selected %u outcome %u\n",s->service.phase,s->service.action,s->service.kind,s->service.selected,s->service.outcome);
    CHECK(btp_state_decode(before,sizeof before,btp_active_map(r,s),btp_state_bld(r,s),&copy));
    btp_game_tick(s,r,a);btp_game_tick(&copy,r,a);btp_state_encode(s,before);btp_state_encode(&copy,after);CHECK(!memcmp(before,after,sizeof before));
}
int main(int argc,char **argv)
{
    if (argc!=2) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError e;CHECK(r && btp_resources_load(argv[1],r,&e));
    CHECK(btp_dialogue_load("work/talk-data.bin",&r->dialogue,&e));CHECK(btp_combat_data_load("work/combat-data.bin",&r->combat,&e));
    CHECK(btp_world_data_load("work/world-data.bin",&r->world,&e));
    FILE *f=fopen("tests/fixtures/mechit-primary.txt","r");CHECK(f);char line[4096];unsigned cases=0;
    while (fgets(line,sizeof line,f)) {
        char type;unsigned loan,shape,funds,policy,cash,questions,menus;uint64_t expected;
        CHECK(sscanf(line,"%c %u %u %u %u %u %u %u %" SCNx64,&type,&loan,&shape,&funds,&policy,&cash,&questions,&menus,&expected)==9);
        BtpState s;setup(&s,r,"repair");uint8_t original[BTP_ORIGINAL_BYTES];FILE *g=fopen("Original DOS/GAME3","rb");CHECK(g);
        CHECK(fread(original,1,sizeof original,g)==sizeof original && !fclose(g));
        memcpy(s.campaign.mech,original+0x111+125*loan,125);if (s.campaign.mech[0]==255) s.campaign.mech[0]=original[1+0xd452-0xc614+loan];
        damaged_record(s.campaign.mech,shape);s.party.mech_types[0]=s.campaign.mech[0];s.credits=funds;
        step(&s,r,BTP_UP);step(&s,r,BTP_ACCEPT);CHECK(s.script.status==BTP_SCRIPT_MENU);
        for (unsigned i=0;i<(type=='P' ? 2u : 3u);++i) step(&s,r,BTP_DOWN);
        step(&s,r,BTP_ACCEPT);CHECK(s.service.phase==1);
        step(&s,r,BTP_ACCEPT);
        unsigned seen_questions=0,seen_menus=0;
        for (unsigned i=0;s.service.phase && i<256;++i) {
            BtpServiceState *v=&s.service;
            if (type=='P' && v->phase==3) {
                ++seen_questions;
                int no=policy==1 || (policy==2 && v->kind==0) || (policy==4 && v->kind==2);
                if (no) step(&s,r,BTP_RIGHT);
            } else if (type=='P' && v->phase==6) {
                ++seen_menus;
                if (policy==1 || policy==3) for (unsigned n=btp_service_weapon_count(v);n;--n) step(&s,r,BTP_DOWN);
            } else if (type=='A' && v->phase==5) {
                if (policy==3) step(&s,r,BTP_DIGIT_3);
                if (policy==999) for (unsigned n=0;n<3;++n) step(&s,r,BTP_DIGIT_9);
            }
            step(&s,r,BTP_ACCEPT);
        }
        CHECK(!s.service.phase);
        if (s.credits!=cash || hash(s.campaign.mech,125)!=expected || seen_questions!=questions || seen_menus!=menus)
            fprintf(stderr,"Mechit case %s actual %u %u %u %016" PRIx64 "\n",line,s.credits,seen_questions,seen_menus,hash(s.campaign.mech,125));
        CHECK(s.credits==cash && hash(s.campaign.mech,125)==expected && seen_questions==questions && seen_menus==menus);++cases;
    }
    fclose(f);CHECK(cases==591);
    f=fopen("tests/fixtures/mechit-ui-primary.txt","r");CHECK(f);uint32_t *pixels=malloc(BTP_PIXELS*sizeof *pixels);CHECK(pixels);unsigned screens=0;
    while (fgets(line,sizeof line,f)) {
        unsigned index;char kind[16],actions[2048];uint64_t right,footer;
        CHECK(sscanf(line,"U %u %15s %" SCNx64 " %" SCNx64 " %2047s",&index,kind,&right,&footer,actions)==5);
        BtpState s;setup(&s,r,kind);char *key=strtok(actions,",");
        while (key) { BtpAction a;CHECK(btp_action_parse(key,&a));step(&s,r,a);key=strtok(NULL,","); }
        btp_render(r,&s,0,pixels);
        char preview[96];CHECK(snprintf(preview,sizeof preview,"work/mechit-ui-%u.ppm",index)>0);
        CHECK(btp_write_ppm(preview,pixels));
        if (region(pixels,104,0,216,200)!=right || region(pixels,0,100,104,100)!=footer) {
            fprintf(stderr,"Mechit UI %u actual %016" PRIx64 " / %016" PRIx64 "\n",index,region(pixels,104,0,216,200),region(pixels,0,100,104,100));
            CHECK(btp_write_ppm("work/mechit-ui-failed.ppm",pixels));
        }
        CHECK(region(pixels,104,0,216,200)==right && region(pixels,0,100,104,100)==footer);++screens;
    }
    fclose(f);CHECK(screens==23);
    /* Native acceptance starts at the same real building menu. */
    BtpState s;setup(&s,r,"repair");step(&s,r,BTP_UP);step(&s,r,BTP_ACCEPT);CHECK(btp_save_write("work/mechit-ui-start.btp",&s,r,&e));
    step(&s,r,BTP_DOWN);step(&s,r,BTP_DOWN);step(&s,r,BTP_ACCEPT);step(&s,r,BTP_ACCEPT);
    uint8_t legacy[BTP_STATE_BYTES];btp_state_encode(&s,legacy);memcpy(legacy,"BTPW",4);legacy[4]=32;
    /* This fixture predates world-sector debris; keep its unrelated old-format
       mark ring empty while exercising the service-state migration. */
    memset(legacy+2048,0,257);
    memset(legacy+19308+sizeof s.yard,0,21);BtpState restored;
    CHECK(btp_state_decode(legacy,sizeof legacy,btp_active_map(r,&s),btp_state_bld(r,&s),&restored));
    CHECK(restored.service.phase==1 && restored.service.action==18 && restored.credits==s.credits &&
        !memcmp(restored.campaign.mech,s.campaign.mech,125));step(&restored,r,BTP_ACCEPT);CHECK(restored.service.phase==3);
    for (unsigned i=0;i<2;++i) {
        setup(&s,r,i ? "recruit" : "apprentice");step(&s,r,BTP_UP);step(&s,r,BTP_ACCEPT);
        CHECK(btp_save_write(i ? "work/mechit-recruit-start.btp" : "work/mechit-apprentice-start.btp",&s,r,&e));
    }
    /* Original 1791874354558657062 retains crew through ordinary building
       entry/exit. Exercise Jason in a nonzero bay with a passenger as well. */
    setup(&s,r,"gyro");s.campaign.mounted=1;s.y_half+=2;s.campaign.world_y+=2;
    const uint8_t mounts[4]={2,0,1,2};
    for (unsigned i=0;i<4;++i) s.party.people[i][12]=mounts[i];
    for (unsigned i=0;i<3;++i) { uint8_t *m=btp_party_mech(&s,i);m[121]=(uint8_t)((i+1u)%3u);m[122]=(uint8_t)(i==2 ? 3 : 255); }
    step(&s,r,BTP_UP);CHECK(s.mode==BTP_ENTRY);step(&s,r,BTP_ACCEPT);CHECK(s.mode==BTP_BUILDING && s.campaign.mounted);
    for (unsigned i=0;i<5;++i) step(&s,r,BTP_DOWN);
    step(&s,r,BTP_ACCEPT);CHECK(s.mode==BTP_EXPLORE && s.campaign.mounted);
    for (unsigned i=0;i<4;++i) CHECK(s.party.people[i][12]==mounts[i]);
    for (unsigned i=0;i<3;++i) { const uint8_t *m=btp_party_mech(&s,i);CHECK(m[121]==(i+1u)%3u && m[122]==(i==2 ? 3 : 255)); }
    free(pixels);free(r);printf("PASS: %u checks; 591 complete original services, 23 screen pairs and every-input saved continuation\n",checks);return 0;
}
