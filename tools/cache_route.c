/* Emit only ordinary inputs to a reachable cache interaction in a real save. */
#include "core/cache.h"
#include "data/save.h"
#include "data/content.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static int goal(const BtpState *s,const BtpResources *r,const char *kind,unsigned index,int x,int y,unsigned tile)
{
    unsigned tx=((unsigned)x+1u)&126u,ty=(unsigned)y&126u;
    if (!strcmp(kind,"terminal")) return index<33 && (tile==182 || tile==183) && (unsigned)y==r->combat.cache_ty[index] &&
        (unsigned)(x+1)>=r->combat.cache_tx[index] && (unsigned)(x+1)<r->combat.cache_tx[index]+3u;
    if (!strcmp(kind,"door")) return index<12 && tile>=126 && tile<=128 && ty==r->combat.cache_dy[index] &&
        (((unsigned)x+1u-2u*(tile-126u))&126u)==r->combat.cache_dx[index];
    if (!strcmp(kind,"room")) return tile==40 && tx==72 && ty==56;
    if (!strcmp(kind,"power")) return (tile==58 || tile==61) && tx==78 && ty>=12 && ty<=16;
    if (!strcmp(kind,"found")) return tile==40 && tx==124 && ty==4;
    if (!strcmp(kind,"generator")) return tile==77 && ((tx==4 && ty==4) || (tx==2 && ty==14));
    if (!strcmp(kind,"secret")) return tile==245 && x>=1 && x<=4 && y==84;
    if (!strcmp(kind,"phoenix")) return tile>=246 && tile<250;
    if (!strcmp(kind,"submit")) return tile==140 || tile==141;
    if (!strcmp(kind,"exit")) return tile==148;
    if (!strcmp(kind,"symbol") && s->story_flags[66] && index<768) {
        unsigned px=index/64u%4u*8u+index%8u,py=index/64u/4u*8u+index%64u/8u;
        return (unsigned)(x+1)/2u==px && (unsigned)y/2u==py;
    }
    return !strcmp(kind,"walk") && (unsigned)(y*128+x)==index;
}
int main(int argc,char **argv)
{
    const char *project=NULL;
    if (argc==6 && !strcmp(argv[4],"--project")) { project=argv[5];argc-=2; }
    if (argc!=4) return 2;
    BtpContent content={0};BtpState s;BtpError e;
    BtpOriginalContentPaths paths={"Original DOS","work/talk-data.bin","work/combat-data.bin","work/world-data.bin"};
    if (!(project ? btp_content_load_project(&content,project,NULL,&e) : btp_content_load_original(&content,&paths,&e))) {
        fprintf(stderr,"%s\n",e.text);return 1;
    }
    const BtpResources *r=content.resources;
    if (!btp_save_load(argv[1],&s,r,&e)) { fprintf(stderr,"%s\n",e.text);btp_content_close(&content);return 1; }
    if (s.mode!=BTP_CACHE || s.cache.phase) { btp_content_close(&content);return 2; }
    unsigned index=(unsigned)strtoul(argv[3],NULL,10);int parents[128*128],queue[128*128],start=s.y_half*128+s.x_half,target=-1;
    for (unsigned i=0;i<128*128;++i) parents[i]=-1;
    parents[start]=start;queue[0]=start;unsigned begin=0,end=1;
    static const int dx[]={0,1,0,-1},dy[]={-1,0,1,0};
    int width=s.story_flags[66] ? 64 : 128,height=s.story_flags[66] ? 48 : 128;
    while (begin<end && target<0) {
        int p=queue[begin++],x=p%128,y=p/128;
        for (unsigned d=0;d<4;++d) {
            int nx=x+dx[d],ny=y+dy[d];if (nx<0 || ny<0 || nx>=width-1 || ny>=height) continue;
            int q=ny*128+nx;if (parents[q]>=0) continue;
            int cx=nx,cy=ny,member=btp_cache_contact(&s,r,&cx,&cy);
            unsigned tile=cx<0 || cy<0 ? 255u : btp_cache_tile(r,&s,(cx+1)/2,cy/2);
            if (goal(&s,r,argv[2],index,cx,cy,tile)) { parents[q]=p;target=q;break; }
            if (member<0) { parents[q]=p;queue[end++]=q; }
        }
    }
    if (target<0) { fprintf(stderr,"No reachable %s %u from %u,%u\n",argv[2],index,s.x_half,s.y_half);btp_content_close(&content);return 1; }
    unsigned count=0;
    for (int q=target;q!=start;q=parents[q]) queue[count++]=q;
    for (unsigned i=count;i>0;--i) {
        int q=queue[i-1],p=parents[q],delta=q-p;
        BtpAction a=delta==-128 ? BTP_UP : delta==1 ? BTP_RIGHT : delta==128 ? BTP_DOWN : BTP_LEFT;
        puts(btp_action_name(a));btp_game_tick(&s,r,a);
    }
    btp_content_close(&content);return 0;
}
