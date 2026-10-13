#include "core/audio.h"
#include "core/animation.h"
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
    f=fopen("tests/fixtures/speaker-timing.txt","r");CHECK(f);CHECK(fgets(row,sizeof row,f));
    unsigned duration,repeats,clocks,instructions,timings=0;
    while (fscanf(f," D %u %u %u %u",&duration,&repeats,&clocks,&instructions)==4) {
        CHECK(instructions>0 && btp_speaker_busy_clocks(duration,repeats)==clocks);++timings;
    }
    CHECK(feof(f) && timings==20);fclose(f);
    /* A rest still advances the original PIT/IRQ state. Its divisor-14
       ultrasonic carrier must not become audible after host sampling. */
    BtpAudioState rest={.active=1,.countdown=4,.divisor=14};
    BtpAudioState silent=rest,split=rest;int16_t rest_pcm[256],split_pcm[256];
    btp_audio_samples(&rest,r,256,rest_pcm);btp_audio_samples(&silent,r,256,NULL);
    btp_audio_samples(&split,r,127,split_pcm);btp_audio_samples(&split,r,129,split_pcm+127);
    CHECK(rest.active && rest.divisor==14 && rest.countdown==3);
    CHECK(!memcmp(&rest,&silent,sizeof rest) && !memcmp(&rest,&split,sizeof rest));
    CHECK(!memcmp(rest_pcm,split_pcm,sizeof rest_pcm));
    for (unsigned i=0;i<256;++i) CHECK(rest_pcm[i]==0);
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
    CHECK(nonzero>1000);btp_game_tick(&s,r,BTP_ACCEPT);CHECK(s.mode==BTP_BEGIN && !s.audio.active);btp_game_tick(&s,r,BTP_ACCEPT);CHECK(s.mode==BTP_EXPLORE);
    f=fopen("tests/fixtures/speaker-primary.txt","r");CHECK(f);
    unsigned programs=0;
    while (fgets(row,sizeof row,f)) {
        unsigned p,tones,noise,actual_tones=0,actual_noise=0;uint64_t want,h=UINT64_C(14695981039346656037);
        CHECK(sscanf(row,"S %u %u %" SCNx64 " %u",&p,&tones,&want,&noise)==4 && p>=1 && p<=18);
        for (unsigned i=0;i<r->combat.sound_count[p-1];++i) {
            const BtpSpeakerEvent *event=&r->combat.sound[p-1][i];
            if (event->type==1) { byte(&h,event->divisor);byte(&h,event->divisor>>8);++actual_tones; }
            if (event->type==2 && event->level) ++actual_noise;
        }
        if (h!=want || tones!=actual_tones || noise!=actual_noise) fprintf(stderr,"speaker %u: tone %u/%u noise %u/%u hash %016" PRIx64 "/%016" PRIx64 "\n",p,actual_tones,tones,actual_noise,noise,h,want);
        CHECK(h==want && tones==actual_tones && noise==actual_noise);++programs;
        btp_start(&s);btp_audio_effect(&s,p);nonzero=0;unsigned ticks=0;
        do {
            btp_game_tick_audio(&s,r,BTP_IDLE,one);
            for (unsigned i=0;i<BTP_AUDIO_TICK_SAMPLES;++i) nonzero+=one[i]!=0;
            uint8_t saved[BTP_STATE_BYTES];BtpState resumed;btp_state_encode(&s,saved);
            CHECK(btp_state_decode(saved,sizeof saved,&r->map,&r->training,&resumed));
            BtpAudioState first=s.audio,second=resumed.audio;
            btp_audio_samples(&first,r,BTP_AUDIO_TICK_SAMPLES,one);btp_audio_samples(&second,r,BTP_AUDIO_TICK_SAMPLES,two);
            CHECK(!memcmp(one,two,sizeof one) && !memcmp(&first,&second,sizeof first));
            CHECK(++ticks<4096);
        } while (s.audio.sound_count);
        CHECK(nonzero>0);
    }
    fclose(f);CHECK(programs==18);
    /* Compare every isolated audible event with original tone-delay entries
       and noise-loop inputs, rather than checking only aggregate toggles. */
    f=fopen("tests/fixtures/speaker-events-primary.txt","r");CHECK(f);programs=0;
    while (fgets(row,sizeof row,f)) {
        unsigned p,count,total,actual=0,sum=0;uint64_t want,h=UINT64_C(14695981039346656037);
        CHECK(sscanf(row,"E %u %u %" SCNx64 " %u",&p,&count,&want,&total)==4 && p>=1 && p<=18);
        for (unsigned i=0;i<r->combat.sound_count[p-1];++i) {
            const BtpSpeakerEvent *event=&r->combat.sound[p-1][i];if (!event->type) continue;
            byte(&h,event->type);byte(&h,event->divisor);byte(&h,event->divisor>>8);byte(&h,event->level);
            for (unsigned c=0;c<4;++c) byte(&h,event->clocks>>(8*c));
            sum+=event->clocks;++actual;
        }
        if (h!=want || actual!=count || sum!=total) fprintf(stderr,"Speaker event mismatch: program %u, events %u/%u, clocks %u/%u\n",p,actual,count,sum,total);
        CHECK(h==want && actual==count && sum==total);++programs;
    }
    CHECK(!ferror(f) && !fclose(f) && programs==18);
    s.menu.sound=0;btp_audio_effect(&s,2);CHECK(!s.audio.sound_count);
    f=fopen("tests/fixtures/outtake-primary.txt","r");CHECK(f);unsigned decisions=0;
    while (fgets(row,sizeof row,f)) {
        unsigned frequency,kind,flags,seed,show,next;
        CHECK(sscanf(row,"O %u %u %u %u %u %u",&frequency,&kind,&flags,&seed,&show,&next)==6);
        btp_start(&s);s.menu.outtakes=(uint8_t)frequency;
        for (unsigned i=0;i<3;++i) s.npc.rng[i]=(uint8_t)(seed>>(8*i));
        CHECK(btp_outtake_roll(&s,kind,flags)==(int)show);
        CHECK(((unsigned)s.npc.rng[0]|(unsigned)s.npc.rng[1]<<8|(unsigned)s.npc.rng[2]<<16)==next);++decisions;
    }
    fclose(f);CHECK(decisions==990);
    free(r);printf("PASS: %u checks, original complete title IRQ trace and saved PCM continuation\n",checks);return 0;
}
