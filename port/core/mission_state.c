#include "core/mission_state.h"
#include "core/battle_mission.h"
#include <string.h>

const char *btp_objective_name(unsigned state)
{
    static const char *const names[]={"inactive","active","complete","failed"};
    return state<4 ? names[state] : "invalid";
}
unsigned btp_objective_state(const BtpState *s,const BtpAdventure *a,unsigned i)
{
    const BtpObjective *o=&a->objectives[i];
    return o->explicit_state ? s->event.objectives[i] :
        s->event.flags[o->complete] ? BTP_OBJECTIVE_COMPLETE :
        s->event.flags[o->active] ? BTP_OBJECTIVE_ACTIVE : BTP_OBJECTIVE_INACTIVE;
}
int btp_mission_region(const BtpState *s,const BtpAdventure *a,unsigned i)
{
    const BtpMissionRegion *r=&a->regions[i];
    unsigned map=s->event.map,x=s->x_half,y=s->y_half;
    /* Combat uses a temporary tactical position. Mission geography remains
       the exploration position to which the battle will return. */
    if (s->event.phase==BTP_EVENT_FIGHTING || s->battle_mission.active) {
        map=s->event.return_map;x=s->campaign.return_x;y=s->campaign.return_y;
    }
    const BtpScene *current=&a->maps[map],*base=&a->maps[r->map];
    if (map!=r->map && (!base->world || base->world!=current->world)) return 0;
    unsigned wx=current->origin_x*2+x,wy=current->origin_y*2+y;
    unsigned rx=(base->origin_x+r->x)*2,ry=(base->origin_y+r->y)*2;
    return wx>=rx && wy>=ry && wx<rx+r->width*2 && wy<ry+r->height*2;
}
static uint32_t membership(const BtpState *s,const BtpAdventure *a)
{
    uint32_t mask=0;
    for (unsigned i=0;i<a->region_count;++i) if (btp_mission_region(s,a,i)) mask|=UINT32_C(1)<<i;
    return mask;
}
int btp_mission_check(const BtpState *s,const BtpAdventure *a,const BtpEventNode *e)
{
    for (unsigned i=0;i<e->count;++i) {
        const BtpMissionCondition *c=&e->conditions[i];unsigned v=0;
        switch (c->kind) {
        case BTP_CONDITION_FLAG:v=s->event.flags[c->argument];break;
        case BTP_CONDITION_VARIABLE:v=s->event.variables[c->argument];break;
        case BTP_CONDITION_OBJECTIVE:v=btp_objective_state(s,a,c->argument);break;
        case BTP_CONDITION_REGION:v=(unsigned)btp_mission_region(s,a,c->argument);break;
        case BTP_CONDITION_COMBAT_ROUND:v=s->battle_mission.round;break;
        default:v=btp_battle_group_value(s,a,c->argument,c->kind);break;
        }
        int match=c->compare==0 ? v==c->value : c->compare==1 ? v!=c->value :
            c->compare==2 ? v<c->value : c->compare==3 ? v<=c->value :
            c->compare==4 ? v>c->value : v>=c->value;
        if (e->value ? match : !match) return e->value!=0; /* any / all */
    }
    return e->value==0;
}
int btp_mission_variable(BtpState *s,const BtpAdventure *a,const BtpEventNode *e)
{
    uint32_t *v=&s->event.variables[e->argument],maximum=a->variables[e->argument].maximum;
    if (e->x==1) {
        if (e->value>maximum-*v) return 0;
        *v+=e->value;
    } else if (e->x==2) {
        if (e->value>*v) return 0;
        *v-=e->value;
    } else *v=e->value;
    return 1;
}
int btp_mission_objective(BtpState *s,const BtpAdventure *a,const BtpEventNode *e)
{
    (void)a;uint8_t *state=&s->event.objectives[e->argument];
    /* Repeating the same state is idempotent. Terminal objectives cannot
       silently restart; authors use a new objective for a new contract. */
    if (*state==e->value) return 1;
    if (*state==BTP_OBJECTIVE_COMPLETE || *state==BTP_OBJECTIVE_FAILED ||
        e->value==BTP_OBJECTIVE_INACTIVE) return 0;
    *state=(uint8_t)e->value;return 1;
}
void btp_mission_initialize(BtpState *s,const BtpAdventure *a)
{
    s->event.mission_state=(uint8_t)a->mission_state;
    s->event.capacity=(uint8_t)(a->version>=3);
    for (unsigned i=0;i<a->variable_count;++i) s->event.variables[i]=a->variables[i].initial;
    for (unsigned i=0;i<a->objective_count;++i) s->event.objectives[i]=(uint8_t)a->objectives[i].initial;
}
void btp_mission_preview(BtpState *s,const BtpAdventure *a)
{
    s->event.regions=membership(s,a);
    s->event.enter_pending=s->event.leave_pending=0;
}
unsigned btp_mission_trigger(BtpState *s,const BtpAdventure *a)
{
    BtpEventState *v=&s->event;if (!v->mission_state) return BTP_EVENT_NODES;
    uint32_t now=membership(s,a);
    v->enter_pending=(v->enter_pending|(now&~v->regions))&now;
    v->leave_pending=(v->leave_pending|(v->regions&~now))&~now;
    v->regions=now;
    /* Leaves precede enters; each group follows region declaration order.
       A transfer reconciles its final destination at the chain's end, so a
       stale queued entry never fires after the party has left that region. */
    for (unsigned side=0;side<2;++side) for (unsigned i=0;i<a->region_count;++i) {
        uint32_t bit=UINT32_C(1)<<i,*pending=side ? &v->enter_pending : &v->leave_pending;
        uint32_t *fired=side ? &v->entered : &v->left;
        const BtpMissionRegion *r=&a->regions[i];unsigned node=side ? r->enter : r->leave;
        if (!(*pending&bit)) continue;
        *pending&=~bit;
        if (node==BTP_EVENT_NODES || (!r->repeat && (*fired&bit))) continue;
        *fired|=bit;return node;
    }
    return BTP_EVENT_NODES;
}
int btp_mission_valid(const BtpState *s,const BtpAdventure *a)
{
    const BtpEventState *v=&s->event;
    if (v->mission_state!=a->mission_state || v->capacity!=(a->version>=3)) return 0;
    for (unsigned i=0;i<BTP_VARIABLES;++i)
        if (v->variables[i]>(i<a->variable_count ? a->variables[i].maximum : 0u)) return 0;
    for (unsigned i=0;i<BTP_OBJECTIVES;++i) {
        if (i>=a->objective_count || !a->objectives[i].explicit_state) { if (v->objectives[i]) return 0; }
        else if (v->objectives[i]>BTP_OBJECTIVE_FAILED) return 0;
    }
    uint32_t mask=a->region_count==32 ? UINT32_MAX : (UINT32_C(1)<<a->region_count)-1;
    if ((v->regions|v->enter_pending|v->leave_pending|v->entered|v->left)&~mask) return 0;
    if ((v->enter_pending&~v->regions) || (v->leave_pending&v->regions)) return 0;
    for (unsigned i=0;i<a->region_count;++i) {
        uint32_t bit=UINT32_C(1)<<i;
        if (a->regions[i].enter==BTP_EVENT_NODES && (v->entered&bit)) return 0;
        if (a->regions[i].leave==BTP_EVENT_NODES && (v->left&bit)) return 0;
    }
    return 1;
}
static void put32(uint8_t *b,uint32_t v)
{ for (unsigned i=0;i<4;++i) b[i]=(uint8_t)(v>>(i*8)); }
static uint32_t get32(const uint8_t *b)
{ return b[0]|(uint32_t)b[1]<<8|(uint32_t)b[2]<<16|(uint32_t)b[3]<<24; }
void btp_mission_encode(const BtpState *s,uint8_t b[BTP_MISSION_BYTES])
{
    const BtpEventState *v=&s->event;memset(b,0,BTP_MISSION_BYTES);b[0]=1;
    for (unsigned i=0;i<32;++i) put32(b+4+i*4,v->variables[i]);
    memcpy(b+132,v->objectives,32);
    put32(b+164,v->regions);put32(b+168,v->enter_pending);put32(b+172,v->leave_pending);
    put32(b+176,v->entered);put32(b+180,v->left);
}
int btp_mission_decode(BtpState *s,const uint8_t b[BTP_MISSION_BYTES])
{
    BtpEventState *v=&s->event;
    if (b[0]!=1 || b[1] || b[2] || b[3]) return 0;
    for (unsigned i=184;i<BTP_MISSION_BYTES;++i) if (b[i]) return 0;
    v->mission_state=1;
    for (unsigned i=0;i<32;++i) {
        v->variables[i]=get32(b+4+i*4);
        if (v->variables[i]>BTP_COUNTER_MAX) return 0;
        v->objectives[i]=b[132+i];if (v->objectives[i]>BTP_OBJECTIVE_FAILED) return 0;
    }
    v->regions=get32(b+164);v->enter_pending=get32(b+168);v->leave_pending=get32(b+172);
    v->entered=get32(b+176);v->left=get32(b+180);return 1;
}

/* These offsets describe the v52 wire format, independently of C padding
   or future array sizes. The original first 256 done bits / 32 variables /
   32 objectives remain in their released locations. */
_Static_assert(BTP_EVENT_NODES==1024 && BTP_VARIABLES==128 && BTP_OBJECTIVES==128,
    "A capacity change requires an explicit save-format audit");
void btp_capacity_encode(const BtpState *s,uint8_t b[BTP_CAPACITY_BYTES])
{
    memset(b,0,BTP_CAPACITY_BYTES);b[0]=1;b[1]=s->battle_mission.enabled;
    memcpy(b+4,s->event.done+32,96);
    for (unsigned i=32;i<128;++i) put32(b+100+(i-32)*4,s->event.variables[i]);
    memcpy(b+484,s->event.objectives+32,96);
}
int btp_capacity_decode(BtpState *s,const uint8_t b[BTP_CAPACITY_BYTES])
{
    if (b[0]!=1 || b[1]>1 || b[2] || b[3]) return 0;
    for (unsigned i=580;i<BTP_CAPACITY_BYTES;++i) if (b[i]) return 0;
    s->event.capacity=1;memcpy(s->event.done+32,b+4,96);
    for (unsigned i=32;i<128;++i) {
        s->event.variables[i]=get32(b+100+(i-32)*4);
        s->event.objectives[i]=b[484+i-32];
        if (s->event.variables[i]>BTP_COUNTER_MAX || s->event.objectives[i]>BTP_OBJECTIVE_FAILED) return 0;
    }
    return 1;
}
