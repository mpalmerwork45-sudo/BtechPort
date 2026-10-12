#include "core/audio.h"
#include "data/save.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
static unsigned checks;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x);return 1; } } while (0)
static void byte(uint64_t *h,unsigned n) { *h=(*h^(n&255u))*UINT64_C(1099511628211); }
int main(int argc,char **argv)
{
    if (argc!=2) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError e;CHECK(r);CHECK(btp_resources_load(argv[1],r,&e));
    CHECK(btp_combat_data_load("work/combat-data.bin",&r->combat,&e));
    FILE *f=fopen("tests/fixtures/audio-primary.txt","r");CHECK(f);char row[200];unsigned notes=0;
    while (fgets(row,sizeof row,f)) if (row[0]=='N') { unsigned n,pitch;CHECK(sscanf(row+1,"%u %u",&n,&pitch)==2);CHECK(btp_audio_pitch(n)==pitch);++notes; }
    else if (row[0]=='T') {
        unsigned count,position,divisor,clock;uint64_t expected,h=UINT64_C(14695981039346656037);
        CHECK(sscanf(row+1,"%u %" SCNx64 " %u %u %u",&count,&expected,&position,&divisor,&clock)==5);
        BtpAudioState v={.active=1,.countdown=1};
        for (unsigned i=0;i<count;++i) {
            CHECK(v.active);btp_audio_irq(&v,r);byte(&h,v.position);byte(&h,v.position>>8);
            byte(&h,v.divisor);byte(&h,v.divisor>>8);byte(&h,v.active);byte(&h,v.countdown);
        }
        CHECK(h==expected && !v.active && v.position==position && v.divisor==divisor && v.countdown==clock);
    } else if (row[0]=='P') {
        char hex[53];CHECK(sscanf(row+1,"%52s",hex)==1);
        for (unsigned i=0;i<26;++i) { unsigned kind;CHECK(sscanf(hex+2*i,"%2x",&kind)==1);CHECK(r->combat.building_portraits[i]==kind); }
    }
    fclose(f);CHECK(notes==128);
    BtpState s;btp_start(&s);btp_audio_start(&s);int16_t one[BTP_AUDIO_TICK_SAMPLES],two[BTP_AUDIO_TICK_SAMPLES];
    unsigned nonzero=0;
    for (unsigned i=0;i<300;++i) {
        BtpAudioState expected=s.audio;btp_audio_samples(&expected,r,BTP_AUDIO_TICK_SAMPLES,one);btp_game_tick(&s,r,BTP_IDLE);
        CHECK(!memcmp(&expected,&s.audio,sizeof expected));
        for (unsigned n=0;n<BTP_AUDIO_TICK_SAMPLES;++n) nonzero+=one[n]!=0;
        uint8_t a[BTP_STATE_BYTES],b[BTP_STATE_BYTES];BtpState copy;
        btp_state_encode(&s,a);CHECK(btp_state_decode(a,sizeof a,&r->map,&r->training,&copy));btp_state_encode(&copy,b);CHECK(!memcmp(a,b,sizeof a));
        BtpAudioState resumed=copy.audio;btp_audio_samples(&expected,r,BTP_AUDIO_TICK_SAMPLES,one);btp_audio_samples(&resumed,r,BTP_AUDIO_TICK_SAMPLES,two);
        CHECK(!memcmp(one,two,sizeof one));
    }
    CHECK(nonzero>1000);btp_game_tick(&s,r,BTP_ACCEPT);CHECK(s.mode==BTP_EXPLORE && !s.audio.active);
    free(r);printf("PASS: %u checks, original complete title IRQ trace and saved PCM continuation\n",checks);return 0;
}
