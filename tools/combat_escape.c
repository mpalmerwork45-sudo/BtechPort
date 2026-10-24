/* Produce ordinary orders through actual movement planning. The replay helper
   reads the known destroyed map to plan ahead; it never edits the played state. */
#include "core/combat.h"
#include "data/save.h"
#include "data/content.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static void input(BtpState *s,const BtpResources *r,BtpAction a)
{ puts(btp_action_name(a));btp_game_tick(s,r,a); }
static void command(BtpState *s,const BtpResources *r,unsigned n)
{
    while (s->combat.selected!=n) input(s,r,BTP_DOWN);
    input(s,r,BTP_ACCEPT);
    if (s->combat.phase==BTP_COMBAT_REPLACE) input(s,r,BTP_ACCEPT);
}
int main(int argc,char **argv)
{
    const char *project=argc==4 && !strcmp(argv[2],"--project") ? argv[3] : NULL;
    if (argc!=2 && !project) return 2;
    BtpContent content={0};BtpState s;BtpError e;
    BtpOriginalContentPaths paths={"Original DOS","work/talk-data.bin","work/combat-data.bin","work/world-data.bin"};
    if (!(project ? btp_content_load_project(&content,project,NULL,&e) : btp_content_load_original(&content,&paths,&e))) {
        fprintf(stderr,"%s\n",e.text);return 1;
    }
    const BtpResources *r=content.resources;
    if (!btp_save_load(argv[1],&s,r,&e)) { fprintf(stderr,"%s\n",e.text);btp_content_close(&content);return 1; }
    if (!s.campaign.invasion || s.combat.phase!=BTP_COMBAT_MENU) { btp_content_close(&content);return 2; }
    static const int dx[]={0,1,1,1,0,-1,-1,-1},dy[]={-1,-1,0,1,1,1,0,-1};
    int *parents=malloc(65536*sizeof *parents),*queue=malloc(65536*sizeof *queue);
    if (!parents || !queue) { free(parents);free(queue);btp_content_close(&content);return 1; }
    for (unsigned round=0;round<128 && s.combat.phase;++round) {
        if (s.combat.goal_active) { command(&s,r,0);input(&s,r,BTP_CANCEL); }
        BtpState projected=s;projected.late.invasion_event=3;
        BtpMap m;btp_combat_map(r,&projected,&m);BtpCombatUnit u=s.combat.unit[0];
        for (unsigned i=0;i<65536;++i) parents[i]=-1;
        int start=u.y*256+u.x,goal=-1;unsigned begin=0,end=1;queue[0]=start;parents[start]=start;
        while (begin<end && goal<0) {
            int p=queue[begin++],x=p%256,y=p/256;
            /* The western breach heads away from the invading Jenners.
               Shortest-to-any-edge would choose an eastward charge at them. */
            if (x<63) { goal=p;break; }
            u.x=(uint8_t)x;u.y=(uint8_t)y;
            for (unsigned d=0;d<8;++d) {
                int nx=x+dx[d],ny=y+dy[d];if (nx<0 || ny<0 || nx>253 || ny>255) continue;
                int q=ny*256+nx;if (parents[q]>=0) continue;
                int8_t path[12][2];btp_combat_plan(&m,s.gate,&u,NULL,nx,ny,1,0,path);
                if (path[0][0]!=dx[d] || path[0][1]!=dy[d]) continue;
                parents[q]=p;queue[end++]=q;
            }
        }
        if (goal<0) { fprintf(stderr,"No route through actual destroyed terrain\n");free(parents);free(queue);btp_content_close(&content);return 1; }
        unsigned n=0;for (int p=goal;p!=start;p=parents[p]) queue[n++]=p;
        /* Queue the corners of at most twelve steps. The core accounts for
           terrain cost and remaining points when consuming those orders. */
        unsigned limit=n<12 ? n : 12;
        for (unsigned k=1;k<=limit;++k) {
            int p=queue[n-k],previous=k==1 ? start : queue[n-k+1];
            int next=k==limit ? -1 : queue[n-k-1];
            if (next>=0 && next-p==p-previous) continue;
            command(&s,r,1);
            int x=p%256,y=p/256;
            while (s.combat.cursor_x<x) input(&s,r,BTP_RIGHT);
            while (s.combat.cursor_x>x) input(&s,r,BTP_LEFT);
            while (s.combat.cursor_y<y) input(&s,r,BTP_DOWN);
            while (s.combat.cursor_y>y) input(&s,r,BTP_UP);
            input(&s,r,BTP_ACCEPT);
        }
        command(&s,r,9);
        for (unsigned i=0;i<8192 && s.combat.phase && s.combat.phase!=BTP_COMBAT_MENU;++i)
            input(&s,r,s.combat.phase==BTP_COMBAT_STORY && !s.cutscene.active ? BTP_ACCEPT : BTP_IDLE);
        if (s.combat.lost) { fprintf(stderr,"The ordinary escape attempt lost its mech\n");free(parents);free(queue);btp_content_close(&content);return 1; }
    }
    int ok=s.combat.fled;free(parents);free(queue);btp_content_close(&content);return !ok;
}
