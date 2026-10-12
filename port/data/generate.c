#include "data/resources.h"
#include "core/npc.h"
#include <string.h>

/* Independent midpoint implementation of the primary 187F:0BFB program.
   The right/bottom subdivisions run first, matching its explicit LIFO stack.
   Eight-bit wrap followed by the >=128 clamp is part of the original rules. */
typedef struct { uint8_t grid[81], index; const uint8_t *noise; } Height;
static void midpoint(Height *h,unsigned a,unsigned b,unsigned radius)
{
    unsigned at=(a+b)/2;
    if (h->grid[at]!=255) return;
    unsigned average=((unsigned)h->grid[a]+h->grid[b])/2;
    unsigned value=(average+(h->noise[h->index++]&(4*radius-1))-2*radius)&255u;
    h->grid[at]=(uint8_t)(value<128 ? value : 0);
}
static void edge(Height *h,unsigned a,unsigned b,unsigned stride)
{
    if (b-a==stride) return;
    unsigned center=(a+b)/2,radius=(b-a)/2/stride;
    midpoint(h,a,b,radius);
    edge(h,center,b,stride);edge(h,a,center,stride);
}
static void interior(Height *h,unsigned a,unsigned b,unsigned c,unsigned d)
{
    if (b-a==1) return;
    unsigned center=(a+d)/2;
    if (h->grid[center]==255)
        h->grid[center]=(uint8_t)(((unsigned)h->grid[a]+h->grid[b]+h->grid[c]+h->grid[d])/4);
    midpoint(h,a,b,(b-a)/2);
    midpoint(h,a,c,(c-a)/18);
    midpoint(h,c,d,(d-c)/2);
    midpoint(h,b,d,(d-b)/18);
    unsigned top=(a+b)/2,left=(a+c)/2,bottom=(c+d)/2,right=(b+d)/2;
    interior(h,center,right,bottom,d);
    interior(h,left,center,c,bottom);
    interior(h,top,b,center,right);
    interior(h,a,top,left,center);
}
int btp_world_generate(BtpWorldData *w,uint32_t seed)
{
    if (!w || !w->native || !seed || seed>=UINT32_C(16777216)) return 0;
    uint8_t rng[3]={(uint8_t)seed,(uint8_t)(seed>>8),(uint8_t)(seed>>16)};
    for (unsigned i=0;i<256;++i) w->noise[i]=(uint8_t)btp_rng_next(rng);
    for (int ry=-1;ry<=16;++ry) for (int rx=-1;rx<=16;++rx) {
        int at=17+16*ry+rx;
        Height h={.noise=w->noise};memset(h.grid,255,sizeof h.grid);
        h.grid[0]=w->coarse[at];h.grid[8]=w->coarse[at+1];
        h.grid[72]=w->coarse[at+16];h.grid[80]=w->coarse[at+17];
        h.index=(uint8_t)(h.grid[0]+h.grid[8]);edge(&h,0,8,1);
        h.index=(uint8_t)(h.grid[72]+h.grid[80]);edge(&h,72,80,1);
        h.index=(uint8_t)(h.grid[0]+h.grid[72]);edge(&h,0,72,9);
        h.index=(uint8_t)(h.grid[8]+h.grid[80]);edge(&h,8,80,9);
        interior(&h,0,8,72,80);
        for (unsigned y=0;y<8;++y) for (unsigned x=0;x<8;++x)
            w->heights[(unsigned)(8*(ry+1)+(int)y)*144+(unsigned)(8*(rx+1)+(int)x)]=h.grid[9*y+x]&240u;
    }
    w->seed=seed;w->loaded=1;
    for (int y=0;y<BTP_WORLD_SIDE;++y) for (int x=0;x<BTP_WORLD_SIDE;++x)
        w->tiles[y*BTP_WORLD_SIDE+x]=(uint8_t)btp_generated_tile(w,BTP_WORLD_ORIGIN+x,BTP_WORLD_ORIGIN+y);
    return 1;
}
unsigned btp_generated_tile(const BtpWorldData *w,int x,int y)
{
    if (!w || !w->native || !w->loaded || x<0 || y<0 || x>=1024 || y>=1024) return 255;
    unsigned bx=(unsigned)x/8,by=(unsigned)y/8,at=(by+8)*144+bx+8;
    unsigned level=w->heights[at],mask=0;
    if (level>=128) return 255; /* Stored local maps are supplied by world.c. */
    if (w->heights[at-144]==level) mask|=1;
    if (w->heights[at+1]==level) mask|=2;
    if (w->heights[at+144]==level) mask|=4;
    if (w->heights[at-1]==level) mask|=8;
    if (level==16) return w->special[((unsigned)y&7)*8+((unsigned)x&7)];
    unsigned flip=(bx+by)&3u,base=level ? level-16 : 0;
    if (base>48) base=48;
    unsigned dx=(unsigned)x&7,dy=(unsigned)y&7;
    if (flip&2u) { mask=w->flips[mask];dx=7-dx; }
    if (flip&1u) { mask=w->flips[32+mask];dy=7-dy; }
    unsigned tile=w->textures[64*mask+8*dy+dx];
    if (tile<64) {
        if (flip&1u) tile=w->flips[32+tile];
        if (flip&2u) tile=w->flips[tile];
        tile=(tile&15u)+base;
    }
    return tile;
}
