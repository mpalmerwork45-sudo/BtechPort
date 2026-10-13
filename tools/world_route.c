/* Input-only replay helper: BFS through the native world's collision samples.
   It reads a real save, produces ordinary keys, and never changes game state. */
#include "core/world.h"
#include "data/save.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static void step(BtpState *s,const BtpResources *r,BtpAction a)
{
    puts(btp_action_name(a));btp_game_tick(s,r,a);
}
static int encounter(BtpState *s,const BtpResources *r)
{
    for (unsigned n=0;n<40 && s->mode==BTP_ENCOUNTER;++n) {
        if (s->combat.phase==BTP_COMBAT_MENU) {
            if (s->combat.selected!=8) step(s,r,BTP_DOWN);else step(s,r,BTP_ACCEPT);
        } else if (s->combat.phase==BTP_COMBAT_OFFER ||
            (s->combat.phase>=BTP_COMBAT_CONTROL && s->combat.phase<=BTP_COMBAT_GRAPHICS)) step(s,r,BTP_ACCEPT);
        else return 0;
    }
    return s->mode!=BTP_ENCOUNTER;
}
int main(int argc,char **argv)
{
    if (argc!=4) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError e;BtpState s;
    if (!r || !btp_resources_load("Original DOS",r,&e) ||
        !btp_combat_data_load("work/combat-data.bin",&r->combat,&e) ||
        !btp_world_data_load("work/world-data.bin",&r->world,&e) ||
        !btp_save_load(argv[1],&s,r,&e)) { fprintf(stderr,"%s\n",e.text);free(r);return 1; }
    if (!strcmp(argv[2],"idle")) {
        unsigned n=(unsigned)atoi(argv[3]);if (n>65535) { free(r);return 2; }
        for (unsigned i=0;i<n;++i) { step(&s,r,BTP_IDLE);if (!encounter(&s,r)) { free(r);return 1; } }
        free(r);return 0;
    }
    int tx=atoi(argv[2]),ty=atoi(argv[3]),sx=s.x_half,sy=s.y_half;
    if (s.map_id) {
        const BtpMap *m=btp_active_map(r,&s);
        sx+=(m->entrance_x[0]>>8)*128;sy+=(m->entrance_y[0]>>12)*128;
    }
    if (tx<0 || ty<0 || tx>=2048 || ty>=2048) { free(r);return 2; }
    enum { SIZE=2048*2048 };
    int *parents=malloc(SIZE*sizeof *parents),*queue=malloc(SIZE*sizeof *queue);
    if (!parents || !queue) { free(parents);free(queue);free(r);return 1; }
    for (unsigned i=0;i<SIZE;++i) parents[i]=-1;
    int start=sy*2048+sx,target=ty*2048+tx;parents[start]=start;queue[0]=start;
    unsigned begin=0,end=1;
    static const int dx[8]={0,1,0,-1,1,1,-1,-1},dy[8]={-1,0,1,0,-1,1,1,-1};
    while (begin<end && parents[target]<0) {
        int p=queue[begin++],x=p%2048,y=p/2048;
        for (unsigned dir=0;dir<8;++dir) {
            int nx=x+dx[dir],ny=y+dy[dir];
            if (nx<0 || ny<2 || nx>=2046 || ny>=2048) continue;
            int q=ny*2048+nx;if (parents[q]>=0) continue;
            unsigned blocked=(!btp_world_location(r,&s,nx/2,ny/2) && btp_world_deep_crossing(&r->world,(unsigned)x,(unsigned)y,dx[dir],dy[dir])) || (s.campaign.mounted ? btp_world_tile(r,&s,nx/2,(ny-2)/2)>=s.gate ||
                btp_world_tile(r,&s,nx/2+1,(ny-2)/2)>=s.gate : btp_world_tile(r,&s,(nx+1)/2,ny/2)>=s.gate);
            if (q==target) blocked=0; /* Pending building entry precedes parking. */
            unsigned id=(unsigned)btp_world_location(r,&s,nx/2,ny/2);
            if (id && q!=target) {
                const BtpMap *m=id==1 ? &r->map : id==11 ? &r->destroyed : &r->local[id-1];
                for (unsigned i=0;i<16;++i) if (m->entrance_x[i] && m->entrance_y[i] &&
                    nx==(m->entrance_x[i]>>8)*128+(m->entrance_x[i]&127) &&
                    ny==(m->entrance_y[i]>>12)*128+(m->entrance_y[i]&127)+(s.campaign.mounted ? 2 : 0)) blocked=0;
            }
            if (!blocked) { parents[q]=p;queue[end++]=q; }
        }
    }
    int ok=parents[target]>=0;unsigned count=0;
    if (ok) {
        for (int q=target;q!=start;q=parents[q]) queue[count++]=q;
        for (unsigned i=count;i>0;--i) {
            int q=queue[i-1],p=parents[q],delta=q-p;
            step(&s,r,delta==-2048 ? BTP_UP : delta==1 ? BTP_RIGHT : delta==2048 ? BTP_DOWN :
                delta==-1 ? BTP_LEFT : delta==-2047 ? BTP_UP_RIGHT : delta==2049 ? BTP_DOWN_RIGHT :
                delta==2047 ? BTP_DOWN_LEFT : BTP_UP_LEFT);
            /* Declining a non-target doorway commits its pending outdoor
               step. Excluding every doorway can strand the route at a shop. */
            if (s.mode==BTP_ENTRY && q!=target) step(&s,r,BTP_CANCEL);
            if (!encounter(&s,r)) { fprintf(stderr,"Encounter continuation requires battle orders\n");ok=0;break; }
        }
    } else fprintf(stderr,"No native walking route to %d,%d\n",tx,ty);
    free(parents);free(queue);free(r);return !ok;
}
