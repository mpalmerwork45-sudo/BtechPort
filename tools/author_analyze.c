/* Read-only authored navigation/deployment probes. The initial party and
   real C collision/door rules are authoritative for these bounded fixtures;
   graph reachability and later recruitment remain separate analyses. */
#include "frontend/cli.h"
#include "core/events.h"
#include "core/party.h"
#include "data/unit_data.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { SIDE=128, CELLS=SIDE*SIDE };
static unsigned diagnostics;

static void problem(const char *code,const char *severity,const char *message,
                    const char *id,const char *map,unsigned x,unsigned y)
{
    printf("%s{\"code\":\"%s\",\"severity\":\"%s\",\"message\":\"%s\",\"object_id\":\"%s\","
           "\"location\":{\"map\":\"%s\",\"at\":[%u,%u],\"coordinate_space\":\"movement\"}}",
           diagnostics++ ? ",":"",code,severity,message,id,map,x,y);
}

static void position(BtpState *s,const BtpScene *m,unsigned map,unsigned x,unsigned y)
{
    s->event.map=(uint16_t)map;s->event.enabled=1;s->event.planet=(uint8_t)m->world;
    s->x_half=(uint16_t)x;s->y_half=(uint16_t)y;
    s->campaign.world_x=(uint16_t)(2*m->origin_x+x);s->campaign.world_y=(uint16_t)(2*m->origin_y+y);
}

static int stand(BtpState *s,const BtpResources *r,const BtpScene *m,unsigned map,unsigned x,unsigned y)
{
    position(s,m,map,x,y);
    return btp_party_can_stand(s,r,s->campaign.world_x,s->campaign.world_y);
}

static unsigned navigation(BtpState *s,const BtpResources *r,unsigned index,
                           uint8_t *visited,uint16_t *queue)
{
    const BtpAdventure *a=btp_adventure(r);const BtpScene *m=&a->maps[index];
    unsigned width=m->rules.width*2u,height=m->rules.height*2u,head=0,tail=0,anchors=0;
    uint8_t doors[BTP_SCENE_ENTRANCES]={0};memset(visited,0,CELLS);
    /* Multi-source flooding from the real starting cursor and every authored
       transfer arrival. It describes potential geometry, not event feasibility. */
    for (unsigned n=0;n<=a->node_count;++n) {
        unsigned x,y;const char *id;
        if (!n) {
            if(index!=a->start_map)continue;
            x=a->start_x;y=a->start_y;id="start";
        } else {
            const BtpEventNode *e=&a->nodes[n-1];
            if(e->op!=BTP_EVENT_TRANSFER || e->argument!=index)continue;
            x=e->x;y=e->y;id=e->id;
        }
        ++anchors;
        if(!stand(s,r,m,index,x,y)) {
            problem("deployment.blocked","error","The initial whole-party formation cannot stand at this arrival.",id,m->id,x,y);
            continue;
        }
        unsigned at=y*SIDE+x;
        if(x<width && y<height && !visited[at]) {visited[at]=1;queue[tail++]=(uint16_t)at;}
    }
    position(s,m,index,0,0);
    while(head<tail) {
        unsigned at=queue[head++];int x=(int)(at%SIDE),y=(int)(at/SIDE);
        for(int dy=-1;dy<=1;++dy)for(int dx=-1;dx<=1;++dx) {
            int nx=x+dx,ny=y+dy;if((!dx && !dy) || nx<0 || ny<0 || nx>=(int)width || ny>=(int)height)continue;
            int door=btp_party_entrance(s,r,&m->rules,nx,ny);
            if(door>=0) {if((unsigned)door<BTP_SCENE_ENTRANCES)doors[door]=1;continue;}
            unsigned next=(unsigned)ny*SIDE+(unsigned)nx;
            if(!visited[next] && btp_party_can_stand(s,r,(int)(2*m->origin_x)+nx,(int)(2*m->origin_y)+ny)) {
                visited[next]=1;queue[tail++]=(uint16_t)next;
            }
        }
    }
    for(unsigned n=0;n<m->entrance_count;++n)if(!doors[n]) {
        const BtpSceneEntrance *door=&m->entrances[n];
        if(!anchors || m->world)problem("navigation.unknown","warning",
            "No local route established; this map needs a supported arrival or a route through its surrounding world.",door->id,m->id,door->x,door->y);
        else problem("entrance.unreachable","warning",
            "No route from any declared arrival with the initial whole-party formation; check narrow paths and terrain.",door->id,m->id,door->x,door->y);
    }
    return tail;
}

static void deployments(BtpState *s,const BtpResources *r)
{
    const BtpAdventure *a=btp_adventure(r);
    for(unsigned n=0;n<a->battle_count;++n) {
        const BtpSceneBattle *b=&a->battles[n];const BtpScene *m=&a->maps[b->map];
        if(!stand(s,r,m,b->map,b->x,b->y))problem("deployment.blocked","error",
            "Encounter party deployment is blocked for the initial whole-party formation.",b->id,m->id,b->x,b->y);
        unsigned fx[12],fy[12],friends=0,mechs=0,people=0;
        for(unsigned slot=0;slot<8;++slot)if(s->party.people[slot][0]!=255 && s->party.people[slot][12]>=8) {
            fx[friends]=(unsigned)((int)b->x+r->combat.formation_x[people]);
            fy[friends++]=(unsigned)((int)b->y+r->combat.formation_y[people++]);
        }
        for(unsigned slot=0;slot<4;++slot)if(btp_party_mech(s,slot)[0]!=255) {
            fx[friends]=(unsigned)((int)b->x+r->combat.mech_formation_x[mechs]);
            fy[friends++]=(unsigned)((int)b->y+r->combat.mech_formation_y[mechs++]);
        }
        for(unsigned i=0;i<b->count;++i) {
            const BtpSceneEnemy *e=&b->enemies[i];
            int drive=e->infantry ? 0 : 1+(int)btp_vehicle_kind(r->roster.mechs[e->definition].record);
            if(!btp_party_walkable(s,r,(int)(2*m->origin_x)+e->x,(int)(2*m->origin_y)+e->y,drive))
                problem("spawn.blocked","error","Enemy footprint cannot stand on its authored terrain.",b->id,m->id,e->x,e->y);
            for(unsigned k=0;k<friends;++k)if(abs((int)e->x-(int)fx[k])<3 && abs((int)e->y-(int)fy[k])<3) {
                problem("deployment.overlap","error","Enemy is too close to a friendly deployment, so the runtime refuses this battle.",b->id,m->id,e->x,e->y);break;
            }
            for(unsigned k=0;k<i;++k) {
                const BtpSceneEnemy *other=&b->enemies[k];
                int close=abs((int)e->x-other->x)<(e->infantry && other->infantry ? 1 : 3) && abs((int)e->y-other->y)<2;
                if(close) {problem("spawn.overlap","warning","Enemy deployment footprints overlap or touch; separate the starting actors.",b->id,m->id,e->x,e->y);break;}
            }
        }
    }
}

int main(int argc,char **argv)
{
    BtpOptions options;BtpContent content={0};BtpError error;
    if(btp_options(argc,argv,&options)<=0 || !options.project)return 2;
    if(!btp_cli_load_content(&options,&content,&error)) {fprintf(stderr,"%s\n",error.text);return 1;}
    const BtpResources *r=content.resources;const BtpAdventure *a=btp_adventure(r);
    BtpState *s=calloc(1,sizeof *s);uint8_t *visited=calloc(CELLS,1);uint16_t *queue=malloc(CELLS*sizeof *queue);
    if(!a || !s || !visited || !queue) {fputs("Authored project or analysis allocation unavailable\n",stderr);free(s);free(visited);free(queue);btp_content_close(&content);return 1;}
    btp_start(s);s->project=1;
    (void)btp_events_preview(s,r,a->maps[a->start_map].id,a->start_x,a->start_y);
    printf("{\"basis\":\"Initial party, compact formation, real C collision and door contacts; potential local routes from start/transfer arrivals.\",\"diagnostics\":[");
    unsigned scenes=a->local_count ? a->local_count : a->map_count,cells=0;
    for(unsigned i=0;i<scenes;++i)cells+=navigation(s,r,i,visited,queue);
    deployments(s,r);
    printf("],\"maps_checked\":%u,\"standable_positions_reached\":%u,\"encounters_checked\":%u}\n",scenes,cells,a->battle_count);
    free(s);free(visited);free(queue);btp_content_close(&content);return 0;
}
