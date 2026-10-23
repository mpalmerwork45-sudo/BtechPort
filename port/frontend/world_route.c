#include "frontend/world_route.h"
#include "core/party.h"
#include <stdlib.h>
#include <string.h>

/* Sparse A* nodes keep a full-size planet affordable. Only the position
   index covers the whole world (16 MiB at 1024 tiles square); the caller
   caps allocated/searchable nodes. Exhaustion is UNKNOWN, not unreachable. */
typedef struct { unsigned at,parent,cost,heap;BtpAction action; } Node;
typedef struct {
    Node *nodes;unsigned *heap,count,width,tx,ty,reach,steps;
} Search;
static unsigned distance(const Search *q,unsigned node)
{
    unsigned at=q->nodes[node].at;
    unsigned dx=(unsigned)abs((int)(at%q->width)-(int)q->tx);
    unsigned dy=(unsigned)abs((int)(at/q->width)-(int)q->ty);
    unsigned d=dx>dy?dx:dy;
    return d>q->reach ? (d-q->reach+q->steps-1)/q->steps : 0;
}
static int before(const Search *q,unsigned a,unsigned b)
{
    unsigned ah=distance(q,a),bh=distance(q,b),af=q->nodes[a].cost+ah,bf=q->nodes[b].cost+bh;
    return af!=bf ? af<bf : ah!=bh ? ah<bh : q->nodes[a].at<q->nodes[b].at;
}
static void swap(Search *q,unsigned a,unsigned b)
{
    unsigned n=q->heap[a];q->heap[a]=q->heap[b];q->heap[b]=n;
    q->nodes[q->heap[a]].heap=a;q->nodes[n].heap=b;
}
static void up(Search *q,unsigned p)
{ while(p && before(q,q->heap[p],q->heap[(p-1)/2])) {unsigned next=(p-1)/2;swap(q,p,next);p=next;} }
static unsigned pop(Search *q)
{
    unsigned first=q->heap[0];--q->count;
    if(q->count) {
        q->heap[0]=q->heap[q->count];q->nodes[q->heap[0]].heap=0;
        unsigned p=0;
        while(2*p+1<q->count) {
            unsigned c=2*p+1;if(c+1<q->count && before(q,q->heap[c+1],q->heap[c]))++c;
            if(!before(q,q->heap[c],q->heap[p]))break;
            swap(q,p,c);p=c;
        }
    }
    q->nodes[first].heap=UINT32_MAX;return first;
}
static int report(BtpRouteReport *out,const char *code,const char *message)
{ out->code=code;out->message=message;return !strcmp(code,"route.passed"); }
static void position(BtpState *probe,const BtpAdventure *a,unsigned map,unsigned x,unsigned y)
{
    const BtpScene *m=&a->maps[map];
    probe->event.map=(uint16_t)map;probe->event.planet=(uint8_t)m->world;
    probe->x_half=(uint16_t)(x-2*m->origin_x);probe->y_half=(uint16_t)(y-2*m->origin_y);
    probe->campaign.world_x=(uint16_t)x;probe->campaign.world_y=(uint16_t)y;
}
int btp_authored_formation(const BtpState *s,const BtpResources *r)
{
    if(!btp_scene(r,s) || !btp_party_can_stand(s,r,s->campaign.world_x,s->campaign.world_y))return 0;
    unsigned foot=0,mech=0;
    for(unsigned i=0;i<8;++i)if(s->party.people[i][0]!=255 && s->party.people[i][12]>=8) {
        int x=(int)s->campaign.world_x+r->combat.formation_x[foot];
        int y=(int)s->campaign.world_y+r->combat.formation_y[foot++];
        if(s->party.x[i]!=x || s->party.y[i]!=y)return 0;
    }
    for(unsigned i=0;i<4;++i)if((i?s->party.mechs[i-1]:s->campaign.mech)[0]!=255) {
        int x=(int)s->campaign.world_x+r->combat.mech_formation_x[mech];
        int y=(int)s->campaign.world_y+r->combat.mech_formation_y[mech++];
        if(s->party.mech_x[i]!=x || s->party.mech_y[i]!=y)return 0;
    }
    return 1;
}
int btp_authored_walk(BtpState *s,const BtpResources *r,const BtpRouteTarget *t,
                     void (*input)(BtpState *,const BtpResources *,BtpAction),BtpRouteReport *out)
{
    memset(out,0,sizeof *out);out->map=UINT32_MAX;
    const BtpAdventure *a=btp_adventure(r);const BtpScene *current=btp_scene(r,s),*target=NULL;
    if(!current || !input || s->mode!=BTP_EXPLORE || !s->menu.steps || s->menu.steps>4)
        return report(out,"route.invalid","Walking requires exploration and a supported step setting.");
    unsigned count=a->local_count?a->local_count:a->map_count,world=current->world;
    unsigned tx=t->x,ty=t->y,ox=0,oy=0,width,height,reach=0;
    if(t->entrance || t->map) {
        for(unsigned i=0;i<count;++i) {
            const BtpScene *m=&a->maps[i];
            if(t->map && !strcmp(t->map,m->id)) {target=m;out->map=i;break;}
            if(t->entrance)for(unsigned k=0;k<m->entrance_count;++k)if(!strcmp(t->entrance,m->entrances[k].id)) {
                target=m;tx=m->entrances[k].x;ty=m->entrances[k].y;out->map=i;break;
            }
            if(target)break;
        }
        if(!target)return report(out,"route.target_missing","The requested map or entrance is absent.");
        out->world=target->world;out->x=tx;out->y=ty;
        if(world!=target->world || (!world && target!=current))
            return report(out,"route.transfer_required","Use an ordinary transfer event before walking on another planet or detached map.");
        if(tx>=2*target->rules.width || ty>=2*target->rules.height)
            return report(out,"route.invalid","Destination is outside its local map.");
        tx+=2*target->origin_x;ty+=2*target->origin_y;
    } else {
        unsigned wi=0;while(wi<a->world_count && (!t->world || strcmp(t->world,a->worlds[wi].id)))++wi;
        if(wi==a->world_count)return report(out,"route.target_missing","The requested world is absent.");
        out->world=wi+1;out->x=tx;out->y=ty;
        if(world!=wi+1)return report(out,"route.transfer_required","Use an ordinary transfer event before walking on another planet.");
    }
    if(world) {width=2*a->worlds[world-1].width;height=2*a->worlds[world-1].height;}
    else {ox=2*current->origin_x;oy=2*current->origin_y;width=2*current->rules.width;height=2*current->rules.height;}
    if(tx<ox || ty<oy || tx-ox>=width || ty-oy>=height)
        return report(out,"route.invalid","Destination is outside the world or map.");
    if(t->entrance) {
        /* Any member may touch a door. This conservative radius keeps the
           heuristic admissible for mixed infantry/mech/vehicle formations. */
        for(unsigned i=0;i<8;++i) {
            unsigned x=(unsigned)abs(r->combat.formation_x[i]),y=(unsigned)abs(r->combat.formation_y[i]);
            if(x>reach)reach=x;
            if(y>reach)reach=y;
        }
        for(unsigned i=0;i<4;++i) {
            unsigned x=(unsigned)abs(r->combat.mech_formation_x[i])+1,y=(unsigned)abs(r->combat.mech_formation_y[i]);
            if(x>reach)reach=x;
            if(y>reach)reach=y;
        }
    }
    unsigned cells=width*height,budget=t->budget?t->budget:BTP_ROUTE_DEFAULT;
    if(budget>BTP_ROUTE_MAX)return report(out,"route.invalid","Route search budget exceeds 1048576 positions.");
    if(budget>cells)budget=cells;
    int32_t *index=malloc((size_t)cells*sizeof *index);
    Node *nodes=calloc(budget,sizeof *nodes);unsigned *heap=malloc((size_t)budget*sizeof *heap);
    BtpState *probe=malloc(sizeof *probe);
    if(!index || !nodes || !heap || !probe) {
        free(index);free(nodes);free(heap);free(probe);
        return report(out,"route.unavailable","Could not allocate bounded route search.");
    }
    *probe=*s;for(unsigned i=0;i<cells;++i)index[i]=-1;
    Search q={.nodes=nodes,.heap=heap,.width=width,.tx=tx-ox,.ty=ty-oy,.reach=reach,.steps=s->menu.steps,.count=1};
    unsigned start=(s->campaign.world_y-oy)*width+s->campaign.world_x-ox;
    nodes[0].at=start;index[start]=0;heap[0]=0;
    unsigned used=1,last=0;int found=!t->entrance && s->campaign.world_x==tx && s->campaign.world_y==ty,limited=0;
    BtpAction final_action=BTP_IDLE;
    static const BtpAction directions[]={BTP_UP,BTP_RIGHT,BTP_DOWN,BTP_LEFT,BTP_UP_RIGHT,BTP_DOWN_RIGHT,BTP_DOWN_LEFT,BTP_UP_LEFT};
    while(q.count && !found && !limited) {
        unsigned n=pop(&q);++out->examined;
        if(!t->entrance && nodes[n].at==(ty-oy)*width+tx-ox) {last=n;found=1;break;}
        for(unsigned d=0;d<8 && !found && !limited;++d) {
            int x=(int)(nodes[n].at%width+ox),y=(int)(nodes[n].at/width+oy),door=-1;
            for(unsigned step=0;step<s->menu.steps;++step) {
                int nx=x+btp_action_dx(directions[d]),ny=y+btp_action_dy(directions[d]);
                if(nx<(int)ox || ny<(int)oy || nx>=(int)(ox+width) || ny>=(int)(oy+height))break;
                int map=world?btp_adventure_world_at(a,world,nx/2,ny/2):(int)s->event.map;
                if(map<0)break;
                position(probe,a,(unsigned)map,(unsigned)nx,(unsigned)ny);
                unsigned owner=(unsigned)map;
                door=btp_party_entrance_scene(probe,r,&a->maps[map].rules,probe->x_half,probe->y_half,&owner);
                if(door>=0) {
                    if(t->entrance && !strcmp(t->entrance,a->maps[owner].entrances[door].id)) {found=1;last=n;final_action=directions[d];}
                    break;
                }
                if(!btp_party_can_stand(probe,r,nx,ny))break;
                x=nx;y=ny;
            }
            /* Other door prompts need an explicit scenario decision. */
            if(found || door>=0)continue;
            unsigned at=(unsigned)(y-(int)oy)*width+(unsigned)(x-(int)ox),cost=nodes[n].cost+1;
            int32_t known=index[at];unsigned next;
            if(known>=0) {
                next=(unsigned)known;if(nodes[next].cost<=cost)continue;
                nodes[next].cost=cost;nodes[next].parent=n;nodes[next].action=directions[d];
                if(nodes[next].heap!=UINT32_MAX) {up(&q,nodes[next].heap);continue;}
            } else {
                if(used==budget) {limited=1;break;}
                next=used++;index[at]=(int32_t)next;
                nodes[next]=(Node){.at=at,.parent=n,.cost=cost,.action=directions[d]};
            }
            nodes[next].heap=q.count;heap[q.count++]=next;up(&q,q.count-1);
        }
    }
    if(found) {
        /* Reuse the now-unused heap for the reversed route, recording the
           expected end of each key. A region/recruit/event can invalidate a
           plan; stop there rather than swallowing dialogue or teleporting. */
        unsigned length=0;for(unsigned n=last;n;n=nodes[n].parent)heap[length++]=n;
        while(length) {
            unsigned n=heap[--length];input(s,r,nodes[n].action);++out->inputs;
            if(s->event.planet!=world || s->campaign.world_x!=nodes[n].at%width+ox || s->campaign.world_y!=nodes[n].at/width+oy ||
               (s->mode!=BTP_EXPLORE && (length || t->entrance)) || !btp_authored_formation(s,r)) {found=0;break;}
        }
        if(found && t->entrance) {
            input(s,r,final_action);++out->inputs;
            found=s->event.phase==BTP_EVENT_ENTRY && s->event.origin_map<a->map_count &&
                s->event.origin_entry<a->maps[s->event.origin_map].entrance_count &&
                !strcmp(t->entrance,a->maps[s->event.origin_map].entrances[s->event.origin_entry].id);
        }
        if(found)report(out,"route.passed","Reached destination using ordinary movement inputs.");
        else report(out,"route.interrupted","Walking stopped at an event or differed from the planned whole-party movement; handle it explicitly.");
    } else report(out,limited?"route.budget":"route.unreachable",limited?
        "Search position budget exhausted; reachability is unknown. Split the route into waypoints or increase max_positions.":
        "No whole-party route at the current step setting without crossing another entrance prompt.");
    free(probe);free(heap);free(nodes);free(index);return found;
}
