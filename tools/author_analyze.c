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

enum { SIDE=128, CELLS=SIDE*SIDE, WORLD_BUDGET=262144 };
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

typedef struct {unsigned reached,anchors,limited;} WorldCheck;
static WorldCheck world_navigation(BtpState *s,const BtpResources *r,unsigned world)
{
    const BtpAdventure *a=btp_adventure(r);const BtpAuthoredWorld *w=&a->worlds[world-1];
    unsigned width=2*w->width,height=2*w->height,cells=width*height;
    unsigned budget=cells<WORLD_BUDGET?cells:WORLD_BUDGET,head=0,tail=0;
    uint8_t *visited=calloc(cells,1),*doors=calloc((size_t)a->map_count*BTP_SCENE_ENTRANCES,1);
    uint32_t *queue=malloc((size_t)budget*sizeof *queue);WorldCheck result={0};
    if(!visited || !doors || !queue) {result.limited=1;goto finished;}
    /* Potential arrivals are roots, not claims that the event graph can
       actually execute each transfer. Scenarios establish that separately. */
    for(unsigned n=0;n<=a->node_count;++n) {
        unsigned map,x,y;const char *id;
        if(!n) {map=a->start_map;x=a->start_x;y=a->start_y;id="start";}
        else {
            const BtpEventNode *e=&a->nodes[n-1];if(e->op!=BTP_EVENT_TRANSFER)continue;
            map=e->argument;x=e->x;y=e->y;id=e->id;
        }
        const BtpScene *m=&a->maps[map];if(m->world!=world)continue;
        ++result.anchors;
        if(!stand(s,r,m,map,x,y)) {
            problem("deployment.blocked","error","The initial whole-party formation cannot stand at this arrival.",id,m->id,x,y);continue;
        }
        unsigned at=(2*m->origin_y+y)*width+2*m->origin_x+x;
        if(!visited[at]) {visited[at]=1;queue[tail++]=at;}
    }
    /* The generated scene at (0,0) samples all world sectors and overlaid
       cities through btp_scene_tile, including each follower's footprint. */
    position(s,&a->maps[w->base],w->base,0,0);
    while(head<tail && !result.limited) {
        unsigned at=queue[head++];int x=(int)(at%width),y=(int)(at/width);
        for(int dy=-1;dy<=1 && !result.limited;++dy)for(int dx=-1;dx<=1;++dx) {
            int nx=x+dx,ny=y+dy;
            if((!dx && !dy) || nx<0 || ny<0 || nx>=(int)width || ny>=(int)height)continue;
            unsigned next=(unsigned)ny*width+(unsigned)nx;if(visited[next])continue;
            visited[next]=1;unsigned owner=w->base;
            int door=btp_party_entrance_scene(s,r,&a->maps[w->base].rules,nx,ny,&owner);
            if(door>=0) {doors[owner*BTP_SCENE_ENTRANCES+(unsigned)door]=1;continue;}
            if(!btp_party_can_stand(s,r,nx,ny))continue;
            if(tail==budget) {result.limited=1;break;}
            queue[tail++]=next;
        }
    }
finished:
    result.reached=tail;
    if(result.limited)printf("%s{\"code\":\"navigation.budget\",\"severity\":\"warning\",\"message\":\"World search incomplete: position or allocation budget reached. Use declared waypoint scenarios for the remaining routes.\",\"object_id\":\"%s\",\"location\":{\"world\":\"%s\",\"at\":[0,0],\"coordinate_space\":\"world_movement\"}}",
        diagnostics++?",":"",w->id,w->id);
    for(unsigned i=0;i<a->local_count;++i) {
        const BtpScene *m=&a->maps[i];if(m->world!=world)continue;
        for(unsigned j=0;j<m->entrance_count;++j) {
            const BtpSceneEntrance *e=&m->entrances[j];unsigned found=0;
            int sector=btp_adventure_world_at(a,world,(int)m->origin_x+e->x/2,(int)m->origin_y+e->y/2);
            const BtpScene *generated=&a->maps[sector];
            for(unsigned k=0;doors && k<generated->entrance_count;++k)
                if(!strcmp(e->id,generated->entrances[k].id))found=doors[(unsigned)sector*BTP_SCENE_ENTRANCES+k];
            if(!found)problem(result.limited || !result.anchors ? "navigation.unknown":"entrance.unreachable","warning",
                result.limited || !result.anchors ? "World route not established within the search budget or no declared arrival exists; verify with a scenario.":
                "No route from any declared arrival on this planet with the initial whole-party formation without another entrance prompt.",e->id,m->id,e->x,e->y);
        }
    }
    free(visited);free(doors);free(queue);return result;
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
    printf("{\"basis\":\"Initial party, compact formation, real C collision and door contacts; potential local/world routes from start/transfer arrivals. One-step geometry, not event feasibility.\",\"diagnostics\":[");
    unsigned scenes=a->local_count ? a->local_count : a->map_count,cells=0;
    for(unsigned i=0;i<scenes;++i)if(!a->maps[i].world)cells+=navigation(s,r,i,visited,queue);
    WorldCheck worlds[BTP_WORLDS]={0};
    for(unsigned i=0;i<a->world_count;++i) {worlds[i]=world_navigation(s,r,i+1);cells+=worlds[i].reached;}
    deployments(s,r);
    printf("],\"maps_checked\":%u,\"standable_positions_reached\":%u,\"encounters_checked\":%u,\"worlds\":[",scenes,cells,a->battle_count);
    for(unsigned i=0;i<a->world_count;++i)printf("%s{\"world\":\"%s\",\"arrivals\":%u,\"reached\":%u,\"complete\":%s,\"max_positions\":%u}",
        i?",":"",a->worlds[i].id,worlds[i].anchors,worlds[i].reached,!worlds[i].limited && worlds[i].anchors?"true":"false",WORLD_BUDGET);
    fputs("]}\n",stdout);
    free(s);free(visited);free(queue);btp_content_close(&content);return 0;
}
