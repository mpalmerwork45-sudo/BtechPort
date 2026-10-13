#include "frontend/pixels.h"
#include "core/menu.h"
#include "core/party.h"
#include "data/save.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
static unsigned checks;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x);return 1; } } while (0)
static uint64_t left_hash(const uint32_t *f)
{
    uint64_t h=UINT64_C(14695981039346656037);
    for (unsigned y=0;y<200;++y) for (unsigned x=0;x<128;++x) for (unsigned c=0;c<3;++c)
        h=(h^((f[y*320+x]>>(16u-8u*c))&255u))*UINT64_C(1099511628211);
    return h;
}
int main(int argc,char **argv)
{
    if (argc!=2) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError e;CHECK(r && btp_resources_load(argv[1],r,&e));
    CHECK(btp_dialogue_load("work/talk-data.bin",&r->dialogue,&e));
    CHECK(btp_combat_data_load("work/combat-data.bin",&r->combat,&e));
    CHECK(btp_world_data_load("work/world-data.bin",&r->world,&e));
    uint32_t *frame=malloc(BTP_PIXELS*sizeof *frame),*second=malloc(BTP_PIXELS*sizeof *second);CHECK(frame && second);
    FILE *fixture=fopen("tests/fixtures/mech-view-primary.txt","r");CHECK(fixture);
    char line[2048];CHECK(fgets(line,sizeof line,fixture));unsigned cases=0;
    unsigned slot,variant,heat,count;uint64_t expected;
    while (fscanf(fixture," V %u %u %u %" SCNx64 " %u",&slot,&variant,&heat,&expected,&count)==5) {
        char path[4096];snprintf(path,sizeof path,"%s/GAME%u",argv[1],slot);
        uint8_t *bytes;size_t length;CHECK(btp_read_file(path,&bytes,&length,&e) && length==BTP_ORIGINAL_BYTES);
        uint8_t m[125];memcpy(m,bytes+0x111,sizeof m);if (m[0]==255) m[0]=bytes[0xe3f];
        if (variant) {
            m[117]=(uint8_t)(variant==1 ? 1 : 3);m[118]=m[119]=(uint8_t)(variant==1 ? 1 : 2);
            m[36]=(uint8_t)(variant==1 ? 0x8c : 0);m[37]=0;
            for (unsigned i=51;i<86;++i) if (m[i]==34) m[i]|=128;
            if (variant==1) m[51]|=128;
            else { memset(m+17,0,11);memset(m+28,1,8);m[38]=0; }
        }
        const char *pilot=m[121]<8 ? btp_character_name(bytes[1+17*m[121]]) : NULL;
        const char *rider=m[122]<8 ? btp_character_name(bytes[1+17*m[122]]) : NULL;
        btp_mech_screen(r,m,pilot,rider,heat,0,frame);
        uint64_t actual=left_hash(frame);
        if (actual!=expected) fprintf(stderr,"GAME%u variant %u: left %016" PRIx64 "/%016" PRIx64 "\n",slot,variant,actual,expected);
        CHECK(actual==expected);
        for (unsigned i=0;i<count;++i) {
            unsigned x0,y0,x1,y1,color;CHECK(fscanf(fixture,"%u %u %u %u %u",&x0,&y0,&x1,&y1,&color)==5);
            CHECK(x0<=x1 && y0<=y1 && x1<320 && y1<200 && color<16);
            if (x0<128) continue; /* Text overwrites the earlier left-panel clear. */
            for (unsigned y=y0;y<=y1;++y) for (unsigned x=x0;x<=x1;++x) CHECK(frame[y*320+x]==btp_palette[color]);
        }
        free(bytes);++cases;
    }
    CHECK(feof(fixture) && cases==18);fclose(fixture);
    BtpState s,copy;CHECK(btp_save_load("Original DOS/GAME3",&s,r,&e));
    btp_menu_open(&s);s.campaign.ui=BTP_MENU_INSPECT;s.campaign.member=0;
    btp_game_tick(&s,r,BTP_RIGHT);CHECK(s.campaign.ui==BTP_MENU_MECH && s.campaign.member==s.party.people[0][12]);
    uint8_t saved[BTP_STATE_BYTES];btp_state_encode(&s,saved);
    CHECK(btp_state_decode(saved,sizeof saved,btp_active_map(r,&s),btp_state_bld(r,&s),&copy));
    btp_render(r,&s,0,frame);btp_render(r,&copy,0,second);CHECK(!memcmp(frame,second,BTP_PIXELS*sizeof *frame));
    btp_game_tick(&copy,r,BTP_ACCEPT);CHECK(copy.mode==BTP_EXPLORE);
    CHECK(btp_write_ppm("work/mech-view.ppm",frame));
    free(frame);free(second);free(r);printf("PASS: %u checks, 18 executed original mech screens and saved inspection continuation\n",checks);return 0;
}
