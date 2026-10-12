#ifndef BTP_AUDIO_H
#define BTP_AUDIO_H
#include "core/game.h"
enum { BTP_AUDIO_RATE=48000,BTP_AUDIO_TICK_SAMPLES=1536 };
unsigned btp_audio_pitch(unsigned note);
void btp_audio_start(BtpState *state);
void btp_audio_irq(BtpAudioState *audio,const BtpResources *resources);
void btp_audio_samples(BtpAudioState *audio,const BtpResources *resources,unsigned count,int16_t *samples);
int btp_audio_valid(const BtpState *state);
void btp_audio_effect(BtpState *state,unsigned effect);
#endif
