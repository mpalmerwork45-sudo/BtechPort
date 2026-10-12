#include "core/audio.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static void word(uint8_t *b,unsigned n) { b[0]=(uint8_t)n;b[1]=(uint8_t)(n>>8); }
static void longword(uint8_t *b,unsigned n) { for (unsigned i=0;i<4;++i) b[i]=(uint8_t)(n>>(8*i)); }
int main(int argc,char **argv)
{
    if (argc!=3) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError e;
    if (!r || !btp_resources_load(argv[1],r,&e)) { free(r);return 1; }
    FILE *f=fopen(argv[2],"wb");if (!f) { free(r);return 1; }
    uint8_t header[44]={0};memcpy(header,"RIFF",4);memcpy(header+8,"WAVEfmt ",8);longword(header+16,16);
    word(header+20,1);word(header+22,1);longword(header+24,BTP_AUDIO_RATE);longword(header+28,2*BTP_AUDIO_RATE);word(header+32,2);word(header+34,16);memcpy(header+36,"data",4);
    int ok=fwrite(header,1,44,f)==44;BtpAudioState v={.active=1,.countdown=1};unsigned frames=0;
    while (ok && v.active && frames<4096) {
        int16_t samples[BTP_AUDIO_TICK_SAMPLES];uint8_t bytes[2*BTP_AUDIO_TICK_SAMPLES];btp_audio_samples(&v,r,BTP_AUDIO_TICK_SAMPLES,samples);
        for (unsigned i=0;i<BTP_AUDIO_TICK_SAMPLES;++i) word(bytes+2*i,(uint16_t)samples[i]);
        ok=fwrite(bytes,1,sizeof bytes,f)==sizeof bytes;++frames;
    }
    unsigned length=frames*BTP_AUDIO_TICK_SAMPLES*2u;longword(header+4,length+36);longword(header+40,length);
    if (fseek(f,0,SEEK_SET) || fwrite(header,1,44,f)!=44) ok=0;
    if (fclose(f)) ok=0;
    free(r);return !ok;
}
