#include "core/combat_rules.h"
#include <string.h>

/* Independent interpretation of DS:5008 and physical 17C52/180CB..184BC.
   Nominal 8 MHz 8088 timings use Intel's table 2-21, word-bus transfers and
   effective addresses. IMUL uses the midpoint of its published range.
   Prefetch contention, interrupts and the physical speaker remain approximate.
   The original 05AB:0BA5/0C8F benchmark gives calibration 2 in this nominal
   model; the EXE's initial value 5 is not an 8 MHz calibration result. */
static const unsigned calibration=2;
static uint32_t pit_clocks(uint64_t cpu_clocks)
{
    return (uint32_t)((cpu_clocks*UINT64_C(1193182)+UINT64_C(4000000))/UINT64_C(8000000));
}
uint32_t btp_speaker_busy_clocks(unsigned duration,unsigned repeats)
{
    int iterations=(int16_t)(uint16_t)(duration*calibration);
    if (iterations<0) iterations=0;
    /* 180CB's fifty delay loops, or 18346's single sweep delay. */
    uint64_t cycles=repeats==50 ? UINT64_C(77)+50u*(314u+261u*(uint64_t)iterations) :
        UINT64_C(255)+261u*(uint64_t)iterations;
    return pit_clocks(cycles);
}
static int emit(BtpCombatData *d,unsigned program,unsigned type,unsigned divisor,unsigned level,uint32_t clocks)
{
    unsigned n=d->sound_count[program];if (n==BTP_SOUND_EVENTS) return 0;
    d->sound[program][n]=(BtpSpeakerEvent){clocks ? clocks : 1u,(uint16_t)divisor,(uint8_t)type,(uint8_t)level};
    ++d->sound_count[program];return 1;
}
static uint16_t rotate(uint16_t seed)
{
    unsigned x=(seed+0x9248u)&65535u;return (uint16_t)((x>>3)|(x<<13));
}
static int noise(BtpCombatData *d,unsigned p,unsigned mask,unsigned base,unsigned length,unsigned seed,unsigned *level)
{
    /* 187F:0067 disables the speaker. 007D receives the same explicit
       seed on each call; it does not feed its result back into STATE:398A. */
    uint16_t value=rotate((uint16_t)seed);*level=0;
    if (!emit(d,p,0,0,0,pit_clocks(641u+84u*(calibration-1u)))) return 0;
    for (unsigned i=0;i<length;++i) {
        *level^=1u;
        unsigned loops=(value&mask)|base;
        if (!loops) loops=65536;
        /* The original calls 187F:00A9 calibration times per toggle.
           LOOP takes 17 clocks when taken and 5 on its final iteration;
           caller/port/prologue work matters for short noise periods. */
        if (!emit(d,p,2,0,*level,pit_clocks(641u+calibration*(566u+17u*(uint64_t)loops)))) return 0;
    }
    return 1;
}
int btp_sound_programs(BtpCombatData *d)
{
    if (d->sound_calibration<2 || d->sound_calibration>1000) return 0;
    memset(d->sound_count,0,sizeof d->sound_count);unsigned at=0;
    for (unsigned p=0;p<BTP_SOUND_COUNT;++p) {
        unsigned level=0;
        for (unsigned budget=0;budget<314;++budget) {
            if (at+3>314) return 0;
            const uint16_t *w=d->sound_words+at;
            unsigned opcode=w[0],size=opcode<=1000 ? 3u : opcode==1001 ? 6u : opcode<=1004 ? 7u : 0u;
            if (!opcode || !size || at+size>314) return 0;
            at+=size;
            if (!w[1] && !w[2]) break;
            unsigned repeats=opcode<=1000 ? opcode : w[1];
            if (!repeats || repeats>1000) return 0;
            for (unsigned n=0;n<repeats;++n) {
                if (opcode<=1000) {
                    if (!emit(d,p,w[1] ? 1u : 0u,w[1],0,btp_speaker_busy_clocks(w[2],50))) return 0;
                } else if (opcode==1001) {
                    if (!noise(d,p,w[2],w[3],w[4],w[5],&level)) return 0;
                } else if (opcode==1002) {
                    if (!w[6] || w[5]>1000) return 0;
                    for (unsigned cycle=0;cycle<w[5];++cycle)
                        for (unsigned j=0;j*w[6]<2u*w[3];++j)
                            if (!emit(d,p,1,(w[2]-w[3]+j*w[6])&65535u,0,btp_speaker_busy_clocks(w[4],1))) return 0;
                } else {
                    if (!w[6] || w[5]>1000) return 0;
                    for (unsigned j=0;j<65536;++j) {
                        int value=(int16_t)(uint16_t)(opcode==1003 ? w[2]-j*w[6] : w[2]+j*w[6]);
                        if (opcode==1003 ? value<=(int16_t)w[3] : value>=(int16_t)w[3]) break;
                        if (!noise(d,p,(uint16_t)value,(uint16_t)(value-w[4]),w[5],1000,&level)) return 0;
                    }
                }
            }
            if (!emit(d,p,0,0,0,1)) return 0;
            level=0;
        }
        if (!d->sound_count[p]) return 0;
    }
    return at==313 && d->sound_words[at]==0;
}
