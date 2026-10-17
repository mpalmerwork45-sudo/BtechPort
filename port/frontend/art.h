#ifndef BTP_FRONTEND_ART_H
#define BTP_FRONTEND_ART_H
#include "data/resources.h"
#include "core/game.h"
int btp_art_draw(const BtpResources *resources,unsigned image,unsigned frame,int x,int y,
    int left,int top,int right,int bottom,uint32_t pixels[BTP_PIXELS]);
int btp_art_sprite(const BtpResources *resources,unsigned slot,unsigned frame,int x,int y,
    int left,int top,int right,int bottom,uint32_t pixels[BTP_PIXELS]);
uint32_t btp_art_pixel(const BtpResources *resources,unsigned image,unsigned frame,unsigned x,unsigned y,uint32_t below);
int btp_art_picture(const BtpResources *resources,const BtpState *state,uint32_t pixels[BTP_PIXELS]);
int btp_art_world_map(const BtpResources *resources,const BtpState *state,uint32_t pixels[BTP_PIXELS]);
#endif
