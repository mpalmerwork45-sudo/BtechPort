#ifndef BTP_AUTHORED_ROUTE_H
#define BTP_AUTHORED_ROUTE_H

#include "core/events.h"
#include "core/party.h"
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

/* The quest robot chooses ordinary inputs with the shared C collision and
   ground-contact rules. It never teleports, changes flags or edits the step
   setting. Separate movement tests establish those rules independently. */
static int authored_walk_to(BtpState *s,const BtpResources *r,const char *entrance_id,
                            void (*input)(BtpState *,const BtpResources *,BtpAction))
{
    enum { SIDE=128,CELLS=SIDE*SIDE };
    static const BtpAction directions[8]={BTP_UP,BTP_RIGHT,BTP_DOWN,BTP_LEFT,
        BTP_UP_RIGHT,BTP_DOWN_RIGHT,BTP_DOWN_LEFT,BTP_UP_LEFT};
    const BtpScene *scene=btp_scene(r,s);
    if (!scene || !entrance_id || !input || s->mode!=BTP_EXPLORE ||
        !s->menu.steps || s->menu.steps>4 || s->x_half>=SIDE || s->y_half>=SIDE) return 0;
    unsigned target=0;
    while (target<scene->entrance_count && strcmp(scene->entrances[target].id,entrance_id)) ++target;
    if (target==scene->entrance_count) return 0;

    int16_t *parent=malloc(CELLS*sizeof *parent),*queue=malloc(CELLS*sizeof *queue);
    uint8_t *edge=malloc(CELLS*sizeof *edge),*path=malloc((CELLS+1u)*sizeof *path);
    if (!parent || !queue || !edge || !path) {
        free(parent);free(queue);free(edge);free(path);return 0;
    }
    for (unsigned i=0;i<CELLS;++i) parent[i]=-1;
    unsigned root=(unsigned)s->y_half*SIDE+s->x_half,head=0,tail=0,last=0,length=0;
    BtpAction final_action=BTP_IDLE;
    int found=0;
    parent[root]=(int16_t)root;queue[tail++]=(int16_t)root;
    while (head<tail && !found) {
        unsigned at=(unsigned)queue[head++];
        for (unsigned direction=0;direction<8 && !found;++direction) {
            BtpAction action=directions[direction];
            int x=(int)(at%SIDE),y=(int)(at/SIDE),other_entry=0;
            /* A two/four-step key can stop at an intermediate doorway or
               wall. Model each half-step without changing the real state. */
            for (unsigned step=0;step<s->menu.steps;++step) {
                int nx=x+btp_action_dx(action),ny=y+btp_action_dy(action);
                int door=btp_party_entrance(s,r,&scene->rules,nx,ny);
                if (door>=0) {
                    if ((unsigned)door==target) { found=1;last=at;final_action=action; }
                    else other_entry=1;
                    break;
                }
                if (nx<0 || ny<0 || nx>=SIDE || ny>=SIDE ||
                    !btp_party_can_stand(s,r,(int)(2*scene->origin_x)+nx,
                                            (int)(2*scene->origin_y)+ny)) break;
                x=nx;y=ny;
            }
            if (found || other_entry) continue;
            unsigned next=(unsigned)y*SIDE+(unsigned)x;
            if (parent[next]>=0) continue;
            parent[next]=(int16_t)at;edge[next]=(uint8_t)action;queue[tail++]=(int16_t)next;
        }
    }
    if (found) {
        path[length++]=(uint8_t)final_action;
        while (last!=root) {
            path[length++]=edge[last];last=(unsigned)parent[last];
        }
        unsigned map=s->map_id;
        while (length) {
            input(s,r,(BtpAction)path[--length]);
            if (length && (s->mode!=BTP_EXPLORE || s->map_id!=map)) { found=0;break; }
        }
        found=found && s->map_id==map && s->event.phase==BTP_EVENT_ENTRY &&
            s->event.origin_entry==target;
    }
    free(parent);free(queue);free(edge);free(path);return found;
}

#endif
