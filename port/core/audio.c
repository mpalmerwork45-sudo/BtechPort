#include "core/audio.h"
#include <string.h>
unsigned btp_audio_pitch(unsigned note)
{
    /* Original 184B:0121/0139/00CF: PIT integer division then 16-bit SHL. */
    static const uint16_t frequency[12]={4186,4435,4699,4978,5274,5588,5920,6272,6645,7040,7459,7902};
    if (note&128u) return 14;
    unsigned shift=(8u-note/12u)&255u,divisor=1193182u/frequency[note%12u];
    return shift>=16 ? 0 : (divisor<<shift)&65535u;
}
void btp_audio_start(BtpState *s)
{
    s->mode=BTP_TITLE;s->audio=(BtpAudioState){.active=1,.countdown=1};
}
void btp_audio_irq(BtpAudioState *v,const BtpResources *r)
{
    if (!v->active || --v->countdown) return;
    v->countdown=4;
    if (v->position>r->music_length) { v->active=0;return; }
    unsigned note=r->music[v->position],n=1;
    if (!note) { note=r->music[v->position+1u];n=2;if (!note) { v->active=0;return; } }
    v->position=(uint16_t)(v->position+n);v->divisor=(uint16_t)btp_audio_pitch(note);v->phase=0;
}
void btp_audio_samples(BtpAudioState *v,const BtpResources *r,unsigned count,int16_t *out)
{
    if (v->sound_count) {
        for (unsigned i=0;i<count;++i) {
            if (!v->sound_count) { if (out) memset(out+i,0,(count-i)*sizeof *out);break; }
            v->sound_fraction+=1193182u;unsigned clocks=v->sound_fraction/BTP_AUDIO_RATE;v->sound_fraction%=BTP_AUDIO_RATE;
            int sum=0;
            for (unsigned n=0;n<clocks && v->sound_count;++n) {
                unsigned program=v->sounds[0]-1u;
                if (program>=BTP_SOUND_COUNT || v->event>=r->combat.sound_count[program]) {
                    --v->sound_count;memmove(v->sounds,v->sounds+1,v->sound_count);v->sounds[v->sound_count]=0;
                    v->event=0;v->remaining=0;v->sound_phase=0;
                    if (!v->sound_count) { v->sound_fraction=0;break; }program=v->sounds[0]-1u;
                }
                const BtpSpeakerEvent *e=&r->combat.sound[program][v->event];
                if (!v->remaining) { v->remaining=e->clocks;v->sound_phase=0; }
                unsigned divisor=e->divisor ? e->divisor : 65536u;
                if (e->type==1) { sum+=v->sound_phase<(divisor+1u)/2u ? 1 : -1;v->sound_phase=(uint16_t)((v->sound_phase+1u)%divisor); }
                if (e->type==2) sum+=e->level ? 1 : -1;
                if (!--v->remaining) ++v->event;
            }
            if (out) out[i]=(int16_t)(sum*6000/(int)clocks);
        }
        return;
    }
    if (!v->active) { if (out) memset(out,0,count*sizeof *out);return; }
    for (unsigned i=0;i<count;++i) {
        v->fraction+=1193182u;unsigned clocks=v->fraction/BTP_AUDIO_RATE;v->fraction%=BTP_AUDIO_RATE;
        int sum=0;unsigned divisor=v->divisor ? v->divisor : 65536u;
        for (unsigned n=0;n<clocks;++n) {
            if (++v->irq_phase==4095) { v->irq_phase=0;btp_audio_irq(v,r);divisor=v->divisor ? v->divisor : 65536u; }
            if (v->active && v->divisor) sum+=v->phase<(divisor+1u)/2u ? 1 : -1;
            v->phase=(uint16_t)(((unsigned)v->phase+1u)%divisor);
        }
        /* Integrate PIT square output over a host sample, limiting aliasing.
           Host volume/filtering is approximate; note divisors/timing are exact. */
        if (out) out[i]=(int16_t)(sum*6000/(int)clocks);
    }
}
int btp_audio_valid(const BtpState *s)
{
    const BtpAudioState *v=&s->audio;
    if (v->sound_count>48 || v->event>BTP_SOUND_EVENTS || v->sound_fraction>=BTP_AUDIO_RATE || v->remaining>UINT32_C(131072000)) return 0;
    for (unsigned i=0;i<48;++i) if (i<v->sound_count ? !v->sounds[i] || v->sounds[i]>18 : v->sounds[i]!=0) return 0;
    if (!v->sound_count && (v->event || v->remaining || v->sound_phase || v->sound_fraction)) return 0;
    return v->active<=1 && v->countdown<=4 && (!v->active || (v->countdown && s->mode==BTP_TITLE)) &&
        v->position<=4352 && v->irq_phase<4095 && v->fraction<BTP_AUDIO_RATE && (!v->divisor || v->phase<v->divisor);
}
void btp_audio_effect(BtpState *s,unsigned effect)
{
    if (s->menu.sound && effect && effect<=18 && s->audio.sound_count<48)
        s->audio.sounds[s->audio.sound_count++]=(uint8_t)effect;
}
