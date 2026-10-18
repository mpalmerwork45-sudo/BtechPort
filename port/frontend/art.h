#ifndef BTP_FRONTEND_ART_H
#define BTP_FRONTEND_ART_H
#include "data/resources.h"
#include "core/game.h"
int btp_art_draw(const BtpResources *resources,unsigned image,unsigned frame,int x,int y,
    int left,int top,int right,int bottom,uint32_t pixels[BTP_PIXELS]);
int btp_art_sprite(const BtpResources *resources,unsigned slot,unsigned frame,int x,int y,
    int left,int top,int right,int bottom,uint32_t pixels[BTP_PIXELS]);
int btp_art_unit(const BtpResources *resources,const uint8_t record[125],unsigned frame,unsigned direction,
    int x,int y,int left,int top,int right,int bottom,uint32_t pixels[BTP_PIXELS]);
int btp_art_actor(const BtpResources *resources,const BtpState *state,unsigned actor,
    int x,int y,int left,int top,int right,int bottom,uint32_t pixels[BTP_PIXELS]);
int btp_art_person(const BtpResources *resources,unsigned person,unsigned frame,unsigned direction,
    int x,int y,int left,int top,int right,int bottom,uint32_t pixels[BTP_PIXELS]);
uint32_t btp_art_pixel(const BtpResources *resources,unsigned image,unsigned frame,unsigned x,unsigned y,uint32_t below);
int btp_art_picture(const BtpResources *resources,const BtpState *state,uint32_t pixels[BTP_PIXELS]);
int btp_art_world_map(const BtpResources *resources,const BtpState *state,uint32_t pixels[BTP_PIXELS]);
#endif
