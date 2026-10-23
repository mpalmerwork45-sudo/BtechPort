/* Bounded authoring scenarios over the real player. Seeds enter before the
   first event; computer, hold and retreat policies send ordinary menu inputs.
   No command grants victory, teleports the party or edits mission flags. */
#include "frontend/cli.h"
#include "frontend/authored_route.h"
#include "frontend/world_route.h"
#include "core/events.h"
#include "core/mission_state.h"
#include "core/battle_mission.h"
#include "core/party.h"
#include "core/combat.h"
#include "core/roster_game.h"
#include "data/json.h"
#include "data/project.h"
#include "data/save.h"
#include "data/digest.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <direct.h>
#define change_directory _chdir
#else
#include <unistd.h>
#define change_directory chdir
#endif

static unsigned ticks,limit=120000,failed,step_number;
static FILE *actions,*trace,*combat_log;
static BtpError error;
static unsigned battle_open,battle_index,initial_armor,initial_structure,initial_ammo,initial_count;
static unsigned initial_infantry[BTP_COMBAT_UNITS];
static unsigned initial_alive[BTP_COMBAT_UNITS],metrics_from_checkpoint,metrics_start_round;
static unsigned resumed,starting_tick;
static uint8_t starting_rng[3];
static char checkpoint_file[96],checkpoint_hash[65],checkpoint_names[256][49];
static unsigned checkpoint_count;
static const char *battle_policy="unselected";
static const char *last_outcome="none";
static unsigned last_round;
static BtpRouteReport route;
static unsigned route_present;

static unsigned sum(const uint8_t *bytes,unsigned count)
{ unsigned result=0;for(unsigned i=0;i<count;++i)result+=bytes[i];return result; }
static unsigned ammunition(const uint8_t record[125])
{
    unsigned result=0;
    /* FF marks energy weapons/unused bins, not 255 rounds of ammunition. */
    for(unsigned i=39;i<49;++i)if(record[i]!=255)result+=record[i];
    return result;
}
static const char *outcome(const BtpCombatState *c)
{ return c->won ? "win" : c->fled ? "retreat" : c->lost ? "loss" : c->phase ? "pending" : "none"; }
static void points(const BtpCombatState *c,unsigned *armor,unsigned *structure,unsigned *ammo)
{
    *armor=*structure=*ammo=0;
    for(unsigned i=0;i<c->friends && i<initial_count;++i) {
        const BtpCombatUnit *u=&c->unit[i];
        if(u->record[0]==255 || u->infantry!=initial_infantry[i])continue;
        if(u->infantry) {*armor+=u->record[14];*structure+=u->record[15];}
        else {*armor+=sum(u->record+17,11);*structure+=sum(u->record+28,8);*ammo+=ammunition(u->record);}
    }
}
static void begin_metrics(const BtpState *s)
{
    battle_open=1;++battle_index;battle_policy="unselected";
    metrics_from_checkpoint=0;metrics_start_round=s->combat.round;
    initial_count=s->combat.friends;
    for(unsigned i=0;i<s->combat.friends;++i) {
        initial_infantry[i]=s->combat.unit[i].infantry;initial_alive[i]=s->combat.unit[i].record[0]!=255;
    }
    points(&s->combat,&initial_armor,&initial_structure,&initial_ammo);
}
static void end_metrics(void *context,const BtpState *s,const BtpResources *r,const BtpSceneBattle *encounter)
{
    (void)context;(void)r;
    unsigned armor,structure,ammo,actors_lost=0,mechs_lost=0;const BtpCombatState *c=&s->combat;
    points(c,&armor,&structure,&ammo);
    for(unsigned i=0;i<c->friends;++i) {
        /* Ejected pilots append new friendly slots during the battle. Count
           their later losses, but never re-count a wreck already in the save. */
        int newly_lost=(i>=initial_count || initial_alive[i]) && c->unit[i].record[0]==255;
        if(newly_lost)++actors_lost;
        if(newly_lost && !c->unit[i].infantry)++mechs_lost;
    }
    last_outcome=outcome(c);last_round=c->round;
    fprintf(combat_log,"{\"battle\":%u,\"encounter\":\"%s\",\"policy\":\"%s\",\"outcome\":\"%s\",\"rounds\":%u,\"friendly_actors_lost\":%u,\"friendly_mechs_lost\":%u,"
        "\"armor_reduction\":%u,\"structure_reduction\":%u,\"ammunition_reduction\":%u,\"metric_basis\":\"%s\",\"start_round\":%u}\n",battle_index,encounter->id,battle_policy,last_outcome,c->round,actors_lost,mechs_lost,
        initial_armor>armor ? initial_armor-armor : 0,initial_structure>structure ? initial_structure-structure : 0,initial_ammo>ammo ? initial_ammo-ammo : 0,
        metrics_from_checkpoint?"since_checkpoint":"whole_battle",metrics_start_round);
    battle_open=0;
}

static void string_json(FILE *f,const char *s)
{
    fputc('"',f);
    for (;*s;++s) {
        unsigned char c=(unsigned char)*s;
        if (c=='"' || c=='\\') { fputc('\\',f);fputc(c,f); }
        else if (c<32) fprintf(f,"\\u%04x",c);
        else fputc(c,f);
    }
    fputc('"',f);
}
static int fail(const char *message)
{
    /* Save/loader failures already occupy this buffer; copying it onto
       itself erased the useful diagnostic in a failed checkpoint report. */
    if (!failed && message!=error.text) snprintf(error.text,sizeof error.text,"%s",message);
    failed=1;return 0;
}
static void input(BtpState *s,const BtpResources *r,BtpAction action)
{
    if (failed) return;
    if (ticks>=limit) { fail("Scenario exceeded its logical tick budget");return; }
    fprintf(actions,"%s\n",btp_action_name(action));++ticks;btp_game_tick(s,r,action);
    if(s->event.phase==BTP_EVENT_FIGHTING && !battle_open)begin_metrics(s);
    if (s->mode==BTP_SCRIPT_FAULT || s->event.phase==BTP_EVENT_FAULT) fail("Runtime event or script fault");
}
static void group_state(FILE *f,const BtpState *s,const BtpAdventure *a)
{
    if (!a->combat_missions) return;
    fprintf(f,",\"combat_round\":%u,\"combat_hook\":%s,\"combat_groups\":{",s->battle_mission.round,s->battle_mission.in_hook ? "true":"false");
    for (unsigned i=0;i<a->group_count;++i) {
        fprintf(f,"%s\"%s\":{\"alive\":%u,\"destroyed\":%u,\"deployed\":%u,\"arrived\":%u}",i?",":"",a->groups[i].id,
            btp_battle_group_value(s,a,i,BTP_CONDITION_GROUP_ALIVE),btp_battle_group_value(s,a,i,BTP_CONDITION_GROUP_DESTROYED),
            btp_battle_group_value(s,a,i,BTP_CONDITION_GROUP_DEPLOYED),btp_battle_group_value(s,a,i,BTP_CONDITION_GROUP_ARRIVED));
    }
    fputc('}',f);
}
static void event_trace(void *context,const BtpState *s,const BtpResources *r,const BtpEventNode *e)
{
    FILE *f=context;const BtpAdventure *a=btp_adventure(r);
    fprintf(f,"{\"tick\":%u,\"event\":\"%s\",\"credits\":%u,\"rng\":[%u,%u,%u],\"flags\":{",s->tick,e->id,s->credits,s->npc.rng[0],s->npc.rng[1],s->npc.rng[2]);
    for(unsigned i=0;i<a->flag_count;++i)fprintf(f,"%s\"%s\":%u",i?",":"",a->flags[i],s->event.flags[i]);
    fputs("},\"variables\":{",f);
    for(unsigned i=0;i<a->variable_count;++i)fprintf(f,"%s\"%s\":%u",i?",":"",a->variables[i].id,s->event.variables[i]);
    fputs("},\"objectives\":{",f);
    for(unsigned i=0;i<a->objective_count;++i)fprintf(f,"%s\"%s\":\"%s\"",i?",":"",a->objectives[i].id,btp_objective_name(btp_objective_state(s,a,i)));
    fputc('}',f);group_state(f,s,a);fputs("}\n",f);
}
static const char *phase_name(unsigned phase)
{
    static const char *names[]={"exploration","entry","text","choice","shop","battle","fault","complete"};
    return phase<8 ? names[phase] : "unknown";
}
static void location(const BtpState *s,const BtpResources *r)
{
    const BtpAdventure *a=btp_adventure(r);const BtpScene *m=btp_scene(r,s);
    if(!m) {fputs("null",stdout);return;}
    if(m->world) {
        /* Reports use source city IDs, not compiler-generated sector IDs.
           Outside a city the editor needs the planet and world coordinates. */
        for(unsigned i=0;i<a->local_count;++i) {
            const BtpScene *city=&a->maps[i];unsigned x=s->campaign.world_x,y=s->campaign.world_y;
            if(city->world==m->world && x>=2*city->origin_x && y>=2*city->origin_y &&
               x<2*(city->origin_x+city->rules.width) && y<2*(city->origin_y+city->rules.height)) {m=city;break;}
        }
        if(m>=a->maps+a->local_count) {
            printf("{\"world\":\"%s\",\"at\":[%u,%u],\"coordinate_space\":\"world_movement\"}",
                a->worlds[m->world-1].id,s->campaign.world_x,s->campaign.world_y);return;
        }
    }
    printf("{\"map\":\"%s\",\"at\":[%u,%u],\"coordinate_space\":\"movement\"}",m->id,
        s->campaign.world_x-2*m->origin_x,s->campaign.world_y-2*m->origin_y);
}
static void navigation(const BtpResources *r)
{
    if(!route_present)return;
    const BtpAdventure *a=btp_adventure(r);
    printf(",\"navigation\":{\"code\":\"%s\",\"examined\":%u,\"inputs\":%u,\"destination\":",route.code,route.examined,route.inputs);
    if(route.map<a->map_count)printf("{\"map\":\"%s\",\"at\":[%u,%u],\"coordinate_space\":\"movement\"}",a->maps[route.map].id,route.x,route.y);
    else if(route.world && route.world<=a->world_count)printf("{\"world\":\"%s\",\"at\":[%u,%u],\"coordinate_space\":\"world_movement\"}",a->worlds[route.world-1].id,route.x,route.y);
    else fputs("null",stdout);
    fputc('}',stdout);
}
static void state(const BtpState *s,const BtpResources *r)
{
    const BtpAdventure *a=btp_adventure(r);const BtpScene *scene=btp_scene(r,s);
    printf("{\"tick\":%u,\"map\":",s->tick);string_json(stdout,scene ? scene->id : "");
    fputs(",\"location\":",stdout);location(s,r);
    printf(",\"world\":\"%s\",\"world_at\":[%u,%u],\"formation_compact\":%s,\"discovery\":{",
        scene && scene->world ? a->worlds[scene->world-1].id : "",s->campaign.world_x,s->campaign.world_y,
        btp_authored_formation(s,r)?"true":"false");
    for(unsigned i=0;i<a->world_count;++i) {
        const BtpAuthoredWorld *w=&a->worlds[i];unsigned seen=0,total=w->width*w->height/64;
        for(unsigned k=0;k<total;++k) {unsigned bit=w->explore_offset+k;seen+=(s->explored[bit/8]&(128u>>(bit&7u)))!=0;}
        printf("%s\"%s\":{\"seen_cells\":%u,\"total_cells\":%u}",i?",":"",w->id,seen,total);
    }
    fputc('}',stdout);
    printf(",\"at\":[%u,%u],\"credits\":%u,\"phase\":\"%s\",\"event\":",s->x_half,s->y_half,s->credits,phase_name(s->event.phase));
    string_json(stdout,s->event.node<a->node_count ? a->nodes[s->event.node].id : "");
    printf(",\"party_count\":%u,\"flags\":{",btp_party_count(&s->party));
    for(unsigned i=0;i<a->flag_count;++i)printf("%s\"%s\":%u",i?",":"",a->flags[i],s->event.flags[i]);
    const char *reported=s->event.phase==BTP_EVENT_FIGHTING || s->battle_mission.active ? outcome(&s->combat) : last_outcome;
    unsigned rounds=s->event.phase==BTP_EVENT_FIGHTING || s->battle_mission.active ? s->combat.round : last_round;
    printf("},\"battle\":{\"won\":%u,\"fled\":%u,\"lost\":%u,\"outcome\":\"%s\",\"round\":%u},\"objectives\":{",!strcmp(reported,"win"),!strcmp(reported,"retreat"),!strcmp(reported,"loss"),reported,rounds);
    for(unsigned i=0;i<a->objective_count;++i) {
        const BtpObjective *o=&a->objectives[i];
        printf("%s\"%s\":\"%s\"",i?",":"",o->id,btp_objective_name(btp_objective_state(s,a,i)));
    }
    fputs("},\"variables\":{",stdout);
    for(unsigned i=0;i<a->variable_count;++i)printf("%s\"%s\":%u",i?",":"",a->variables[i].id,s->event.variables[i]);
    fputs("},\"regions\":{",stdout);
    for(unsigned i=0;i<a->region_count;++i)printf("%s\"%s\":%d",i?",":"",a->regions[i].id,btp_mission_region(s,a,i));
    fputc('}',stdout);group_state(stdout,s,a);
    printf(",\"mode\":\"%s\",\"rng\":[%u,%u,%u],\"owned_mechs\":%u,\"party\":[",btp_mode_name(s->mode),s->npc.rng[0],s->npc.rng[1],s->npc.rng[2],btp_broker_count(s));
    unsigned comma=0;
    for(unsigned i=0;i<8;++i)if(s->event.people[i]<a->person_count) {
        printf("%s{\"id\":\"%s\",\"slot\":%u,\"alive\":%s,\"health\":%u,\"on_foot\":%s,\"world_at\":[%u,%u]}",comma++?",":"",a->people[s->event.people[i]].id,i,
            s->party.people[i][0]!=255 ? "true":"false",s->party.people[i][0]!=255 ? s->party.people[i][15] : 0,
            s->party.people[i][12]>=8?"true":"false",s->party.x[i],s->party.y[i]);
    }
    fputs("],\"units\":[",stdout);comma=0;
    for(unsigned i=0;i<4;++i) {
        const uint8_t *m=i ? s->party.mechs[i-1] : s->campaign.mech;
        if(!btp_broker_owned(s,i))continue;
        const BtpRosterMech *definition=btp_roster_definition(&r->roster,m);
        printf("%s{\"id\":\"%s\",\"bay\":%u,\"available\":%s,\"armor\":%u,\"structure\":%u,\"ammunition\":%u,\"world_at\":[%u,%u]}",comma++?",":"",definition?definition->id:"",i,m[0]!=255?"true":"false",sum(m+17,11),sum(m+28,8),ammunition(m),s->party.mech_x[i],s->party.mech_y[i]);
    }
    fputs("]}",stdout);
}
static int text_field(BtpJson *j,unsigned node,const char *key,char *value,size_t size)
{ return btp_json_string(j,btp_json_field(j,node,key),value,size); }
static int optional_number(BtpJson *j,unsigned node,const char *key,unsigned low,unsigned high,unsigned *value)
{ unsigned n=btp_json_optional(j,node,key);return !n || btp_json_uint(j,n,low,high,value); }
static int pair(BtpJson *j,unsigned node,unsigned high,unsigned *x,unsigned *y)
{
    if(!btp_json_type(j,node,'['))return 0;
    unsigned first=j->nodes[node].first,second=first?j->nodes[first].next:0;
    return first && second && !j->nodes[second].next && btp_json_uint(j,first,0,high,x) && btp_json_uint(j,second,0,high,y);
}
static void save_path(char path[96],const char *name,const BtpResources *r)
{
    int prefix=snprintf(path,96,"%s-",name);
    for (unsigned i=0;i<32;++i) snprintf(path+prefix+2*i,3,"%02x",r->project->digest[i]);
    strcpy(path+prefix+64,".btp");
}
static int file_hash(const char *path,char out[65])
{
    FILE *f=fopen(path,"rb");if(!f)return fail("Cannot read checkpoint save");
    BtpDigest digest;btp_digest_start(&digest);uint8_t buffer[4096],hash[32];size_t n,total=0;
    while((n=fread(buffer,1,sizeof buffer,f))) {
        total+=n;if(total>160+BTP_STATE_BYTES)break;
        btp_digest_add(&digest,buffer,n);
    }
    int ok=!ferror(f) && total<=160+BTP_STATE_BYTES && total>=184;
    if(fclose(f))ok=0;
    if(!ok)return fail("Checkpoint save is truncated, oversized or unreadable");
    btp_digest_finish(&digest,hash);
    for(unsigned i=0;i<32;++i)snprintf(out+2*i,3,"%02x",hash[i]);
    return 1;
}
static int checkpoint(BtpState *s,const BtpResources *r,const char *name)
{
    char path[96];
    if(name) {
        size_t len=strlen(name);if(!len || len>48)return fail("Checkpoint name needs 1..48 letters, digits, underscores or dashes");
        for(size_t i=0;i<len;++i)if(!((name[i]>='a' && name[i]<='z') || (name[i]>='A' && name[i]<='Z') ||
            (name[i]>='0' && name[i]<='9') || (i && (name[i]=='_' || name[i]=='-'))))return fail("Invalid checkpoint name");
        for(unsigned i=0;i<checkpoint_count;++i)if(!strcmp(name,checkpoint_names[i]))return fail("Checkpoint names must be unique within a scenario");
        if(checkpoint_count==256)return fail("Too many named checkpoints");
        snprintf(path,sizeof path,"checkpoint-%s.btp",name);
        FILE *existing=fopen(path,"rb");if(existing) {fclose(existing);return fail("Named checkpoint already exists; use a new artifact directory");}
        strcpy(checkpoint_names[checkpoint_count++],name);
    } else save_path(path,"checkpoint",r);
    BtpState *loaded=malloc(sizeof *loaded);uint8_t *before=malloc(BTP_STATE_BYTES),*after=malloc(BTP_STATE_BYTES);
    /* CTest reuses its artifact directory after authored content changes.
       Namespace fixtures by content instead of weakening the player's guard
       against overwriting another project revision's save. */
    int ok=loaded && before && after && btp_save_write(path,s,r,&error) && btp_save_load(path,loaded,r,&error);
    if(ok) { btp_state_encode(s,before);btp_state_encode(loaded,after);ok=!memcmp(before,after,BTP_STATE_BYTES); }
    if(ok) {*s=*loaded;ok=file_hash(path,checkpoint_hash);if(ok)strcpy(checkpoint_file,path);}
    free(loaded);free(before);free(after);return ok || fail(error.text[0] ? error.text : "Save/reload changed logical state");
}
static int capture(const BtpState *s,const BtpResources *r,const char *path)
{
    uint32_t *pixels=malloc(BTP_PIXELS*sizeof *pixels);if(!pixels)return fail("Frame allocation failed");
    btp_render(r,s,0,pixels);int ok=btp_write_ppm(path,pixels);free(pixels);return ok || fail("Cannot write frame");
}
static int command(BtpState *s,const BtpResources *r,unsigned selected)
{
    unsigned tries=0;
    while(s->combat.phase==BTP_COMBAT_MENU && s->combat.selected!=selected && tries++<12 && !failed)input(s,r,BTP_DOWN);
    if(s->combat.phase!=BTP_COMBAT_MENU || s->combat.selected!=selected)return fail("Requested combat command is unavailable");
    input(s,r,BTP_ACCEPT);return !failed;
}
static int number_assert(BtpJson *j,unsigned node,const char *key,unsigned actual)
{
    unsigned n=btp_json_optional(j,node,key),expected;
    return !n || (btp_json_uint(j,n,0,16777215,&expected) && expected==actual) || fail("Numeric state assertion failed");
}
static int execute(BtpJson *j,unsigned node,BtpState *s,const BtpResources *r)
{
    char op[24],value[128];if(!text_field(j,node,"op",op,sizeof op))return 0;
    if(!strcmp(op,"input")) {
        unsigned repeat=1;BtpAction action;
        if(!text_field(j,node,"action",value,sizeof value) || !btp_action_parse(value,&action) ||
            !optional_number(j,node,"repeat",1,120000,&repeat))return fail("Input needs a supported logical action and bounded repeat");
        for(unsigned i=0;i<repeat && !failed;++i)input(s,r,action);
    } else if(!strcmp(op,"pages")) {
        unsigned pages=0;while(s->event.phase==BTP_EVENT_TEXT && !failed && pages++<128)input(s,r,BTP_ACCEPT);
        if(pages>=128)return fail("Dialogue exceeded 128 pages");
    } else if(!strcmp(op,"walk")) {
        BtpRouteTarget target={0};char entrance[64],map[64],world[64];unsigned n,count=0;
        n=btp_json_optional(j,node,"entrance");if(n) {if(!btp_json_string(j,n,entrance,sizeof entrance))return 0;target.entrance=entrance;++count;}
        n=btp_json_optional(j,node,"map");if(n) {if(!btp_json_string(j,n,map,sizeof map))return 0;target.map=map;++count;}
        n=btp_json_optional(j,node,"world");if(n) {if(!btp_json_string(j,n,world,sizeof world))return 0;target.world=world;++count;}
        n=btp_json_optional(j,node,"at");
        if(count!=1 || (!!n==!!target.entrance) || (n && !pair(j,n,2047,&target.x,&target.y)) ||
           !optional_number(j,node,"max_positions",1,BTP_ROUTE_MAX,&target.budget))return fail("Walk needs an entrance OR a map/world and movement coordinates.");
        /* Preserve established local replay choices; worlds and coordinates
           use the bounded planner, including source-town entrance IDs. */
        if(target.entrance && !btp_scene(r,s)->world && !target.budget) {
            if(!authored_walk_to(s,r,target.entrance,input))return fail("Entrance is absent, unreachable, or walking was interrupted");
        } else {
            route_present=1;
            if(!btp_authored_walk(s,r,&target,input,&route))return fail(route.message);
        }
    } else if(!strcmp(op,"enter")) {
        if(s->event.phase!=BTP_EVENT_ENTRY)return fail("Enter requires an offered building entrance");
        input(s,r,BTP_ACCEPT);
    } else if(!strcmp(op,"choose")) {
        if(!text_field(j,node,"label",value,sizeof value))return 0;
        if(s->event.phase!=BTP_EVENT_SELECT)return fail("Choose requires a displayed choice event");
        const BtpEventNode *e=&btp_adventure(r)->nodes[s->event.node];unsigned choice=0;
        while(choice<e->count && strcmp(value,e->labels[choice]))++choice;
        if(choice==e->count)return fail("Choice label is not present in the current menu");
        unsigned count=0;while(s->event.selected!=choice && count++<8 && !failed)input(s,r,BTP_DOWN);
        if(s->event.selected!=choice)return fail("Could not select the requested choice");
        input(s,r,BTP_ACCEPT);
    } else if(!strcmp(op,"battle")) {
        unsigned until=0;
        if(!text_field(j,node,"control",value,sizeof value) || (strcmp(value,"computer") && strcmp(value,"hold") && strcmp(value,"retreat")))return fail("Use computer, hold or retreat combat control");
        if(!optional_number(j,node,"until_round",1,1024,&until))return 0;
        if(s->event.phase!=BTP_EVENT_FIGHTING && !s->battle_mission.active)return fail("Battle requires an active encounter");
        const char *policy=!strcmp(value,"computer") ? "computer" : !strcmp(value,"hold") ? "hold" : "retreat";
        if(s->combat.phase==BTP_COMBAT_CONTROL) battle_policy=policy;
        else if(!strcmp(battle_policy,"saved")) {
            /* Resume the saved orders, never rewrite auto flags to make a
               scenario pass. Mixed/manual-paused computer orders need
               explicit ordinary menu inputs before using this helper. */
            unsigned mask=(1u<<s->combat.friends)-1u;
            if(!strcmp(policy,"computer") ? s->combat.automatic!=mask || !s->combat.auto_run : s->combat.automatic!=0)
                return fail("Battle policy conflicts with saved control; use ordinary menu inputs or a matching policy");
            battle_policy=policy;
        }
        else if(strcmp(battle_policy,policy))return fail("Resume a held battle with its original tested policy");
        while((s->event.phase==BTP_EVENT_FIGHTING || s->battle_mission.active) && !failed) {
            if(until && s->combat.round>=until && !s->battle_mission.in_hook)break;
            if(s->battle_mission.in_hook) {
                if(s->event.phase!=BTP_EVENT_TEXT)return fail("Combat hook has a choice; use explicit choose input for this route");
                input(s,r,BTP_ACCEPT);continue;
            }
            /* Drain the saved start hook before selecting combat settings.
               A helper never changes mission variables or advances simulation
               directly: every acknowledgment is an ordinary logical key. */
            if(s->battle_mission.active) {
                unsigned pending=0;for(unsigned i=0;i<32;++i)pending+=s->battle_mission.pending[i];
                if(pending) { input(s,r,BTP_IDLE);continue; }
            }
            if(s->combat.phase==BTP_COMBAT_CONTROL) {
                if(!strcmp(policy,"computer"))input(s,r,BTP_UP);
                input(s,r,BTP_ACCEPT);continue;
            }
            if(s->combat.phase==BTP_COMBAT_MESSAGES || s->combat.phase==BTP_COMBAT_GRAPHICS) { input(s,r,BTP_ACCEPT);continue; }
            if(s->combat.phase==BTP_COMBAT_NOTICE || s->combat.phase==BTP_COMBAT_PICK)input(s,r,BTP_ACCEPT);
            else if(s->combat.phase==BTP_COMBAT_MENU && strcmp(policy,"computer")) {
                if(!command(s,r,!strcmp(policy,"retreat") ? 8u : 9u))return 0;
            } else input(s,r,BTP_IDLE);
        }
    } else if(!strcmp(op,"checkpoint")) {
        unsigned n=btp_json_optional(j,node,"name");char name[49];
        if(n && !btp_json_string(j,n,name,sizeof name))return 0;
        if(!checkpoint(s,r,n?name:NULL))return 0;
    } else if(!strcmp(op,"capture")) {
        char path[64];snprintf(path,sizeof path,"step-%03u.ppm",step_number);
        if(!capture(s,r,path))return 0;
    } else if(!strcmp(op,"assert")) {
        unsigned n,expected;const BtpAdventure *a=btp_adventure(r);
        n=btp_json_optional(j,node,"credits");if(n && (!btp_json_uint(j,n,0,16777215,&expected) || expected!=s->credits))return fail("Credit assertion failed");
        n=btp_json_optional(j,node,"party_count");if(n && (!btp_json_uint(j,n,0,8,&expected) || expected!=btp_party_count(&s->party)))return fail("Party assertion failed");
        if(!number_assert(j,node,"owned_mechs",btp_broker_count(s)))return 0;
        unsigned alive=0;for(unsigned i=0;i<8;++i)if(s->party.people[i][0]!=255)++alive;
        if(!number_assert(j,node,"alive_party",alive))return 0;
        const char *reported=s->event.phase==BTP_EVENT_FIGHTING || s->battle_mission.active ? outcome(&s->combat) : last_outcome;
        unsigned rounds=s->event.phase==BTP_EVENT_FIGHTING || s->battle_mission.active ? s->combat.round : last_round;
        n=btp_json_optional(j,node,"battle_outcome");if(n && (!btp_json_string(j,n,value,sizeof value) || strcmp(value,reported)))return fail("Battle outcome assertion failed");
        n=btp_json_optional(j,node,"round_min");if(n && (!btp_json_uint(j,n,0,65535,&expected) || rounds<expected))return fail("Minimum battle round assertion failed");
        n=btp_json_optional(j,node,"round_max");if(n && (!btp_json_uint(j,n,0,65535,&expected) || rounds>expected))return fail("Maximum battle round assertion failed");
        n=btp_json_optional(j,node,"person");if(n) {
            if(!btp_json_string(j,n,value,sizeof value))return 0;
            unsigned slot=0;
            while(slot<8 && (s->event.people[slot]>=a->person_count || strcmp(value,a->people[s->event.people[slot]].id)))++slot;
            if(slot==8)return fail("Requested party person is absent");
            unsigned health=s->party.people[slot][0]!=255 ? s->party.people[slot][15] : 0;
            n=btp_json_optional(j,node,"health_min");if(n && (!btp_json_uint(j,n,0,255,&expected) || health<expected))return fail("Character health assertion failed");
        }
        n=btp_json_optional(j,node,"mech");if(n) {
            if(!btp_json_string(j,n,value,sizeof value))return 0;
            const uint8_t *record=NULL;
            for(unsigned i=0;i<4;++i) {
                const uint8_t *m=btp_party_mech(s,i);const BtpRosterMech *d=btp_roster_definition(&r->roster,m);
                if(m[0]!=255 && d && !strcmp(value,d->id)) {if(record)return fail("Mech assertion is ambiguous; use a unique definition in this fixture");record=m;}
            }
            if(!record)return fail("Requested owned mech is absent");
            static const char *keys[]={"armor_min","armor_max","structure_min","structure_max","ammo_min","ammo_max"};
            unsigned values[]={sum(record+17,11),sum(record+28,8),ammunition(record)};
            for(unsigned i=0;i<6;++i) {
                n=btp_json_optional(j,node,keys[i]);if(n && (!btp_json_uint(j,n,0,65535,&expected) || (i%2 ? values[i/2]>expected : values[i/2]<expected)))return fail("Owned mech condition assertion failed");
            }
        }
        n=btp_json_optional(j,node,"phase");if(n && (!btp_json_string(j,n,value,sizeof value) || strcmp(value,phase_name(s->event.phase))))return fail("Event phase assertion failed");
        n=btp_json_optional(j,node,"map");if(n && (!btp_json_string(j,n,value,sizeof value) || !btp_scene(r,s) || strcmp(value,btp_scene(r,s)->id)))return fail("Map assertion failed");
        n=btp_json_optional(j,node,"world");if(n && (!btp_json_string(j,n,value,sizeof value) || !s->event.planet ||
            strcmp(value,a->worlds[s->event.planet-1].id)))return fail("World assertion failed");
        n=btp_json_optional(j,node,"world_at");if(n) {
            unsigned x,y;if(!pair(j,n,2047,&x,&y) || x!=s->campaign.world_x || y!=s->campaign.world_y)return fail("World position assertion failed");
        }
        n=btp_json_optional(j,node,"formation");if(n && (!btp_json_string(j,n,value,sizeof value) || strcmp(value,"compact") ||
            !btp_authored_formation(s,r)))return fail("Whole-party formation is detached or blocked");
        n=btp_json_optional(j,node,"discovered");if(n) {
            unsigned x,y,seen;
            if(!text_field(j,n,"world",value,sizeof value) || !pair(j,btp_json_field(j,n,"at"),1023,&x,&y) ||
               !btp_json_uint(j,btp_json_field(j,n,"seen"),0,1,&seen) || !btp_json_done(j,n))return fail("Discovery assertion needs world, tile coordinates and seen (0 or 1)");
            unsigned wi=0;while(wi<a->world_count && strcmp(value,a->worlds[wi].id))++wi;
            if(wi==a->world_count || x>=a->worlds[wi].width || y>=a->worlds[wi].height)return fail("Discovery location is outside the requested world");
            const BtpAuthoredWorld *w=&a->worlds[wi];unsigned bit=w->explore_offset+(y/8)*(w->width/8)+x/8;
            if((unsigned)!!(s->explored[bit/8]&(128u>>(bit&7u)))!=seen)return fail("World discovery assertion failed");
        }
        n=btp_json_optional(j,node,"event");if(n && (!btp_json_string(j,n,value,sizeof value) || s->event.node>=a->node_count || strcmp(value,a->nodes[s->event.node].id)))return fail("Event assertion failed");
        n=btp_json_optional(j,node,"flag");if(n) {
            if(!btp_json_string(j,n,value,sizeof value) || !btp_json_uint(j,btp_json_field(j,node,"value"),0,255,&expected))return 0;
            unsigned i=0;while(i<a->flag_count && strcmp(value,a->flags[i]))++i;
            if(i==a->flag_count || s->event.flags[i]!=expected)return fail("Flag assertion failed");
        }
        n=btp_json_optional(j,node,"objective");if(n) {
            char status[16];if(!btp_json_string(j,n,value,sizeof value) || !text_field(j,node,"status",status,sizeof status))return 0;
            unsigned i=0;while(i<a->objective_count && strcmp(value,a->objectives[i].id))++i;
            if(i==a->objective_count)return fail("Objective is absent");
            const char *actual=btp_objective_name(btp_objective_state(s,a,i));
            if(strcmp(actual,status))return fail("Objective state assertion failed");
        }
        n=btp_json_optional(j,node,"variable");if(n) {
            if(!btp_json_string(j,n,value,sizeof value) || !btp_json_uint(j,btp_json_field(j,node,"value"),0,BTP_COUNTER_MAX,&expected))return 0;
            unsigned i=0;while(i<a->variable_count && strcmp(value,a->variables[i].id))++i;
            if(i==a->variable_count || s->event.variables[i]!=expected)return fail("Mission variable assertion failed");
        }
        n=btp_json_optional(j,node,"region");if(n) {
            if(!btp_json_string(j,n,value,sizeof value) || !btp_json_uint(j,btp_json_field(j,node,"value"),0,1,&expected))return 0;
            unsigned i=0;while(i<a->region_count && strcmp(value,a->regions[i].id))++i;
            if(i==a->region_count || (unsigned)btp_mission_region(s,a,i)!=expected)return fail("Region membership assertion failed");
        }
        n=btp_json_optional(j,node,"group");if(n) {
            char measure[24];const char *const names[]={"alive","destroyed","deployed","arrived"};unsigned kind=0;
            if(!btp_json_string(j,n,value,sizeof value) || !text_field(j,node,"measure",measure,sizeof measure) ||
               !btp_json_uint(j,btp_json_field(j,node,"value"),0,12,&expected))return 0;
            while(kind<4 && strcmp(measure,names[kind]))++kind;
            unsigned i=0;while(i<a->group_count && strcmp(value,a->groups[i].id))++i;
            if(kind==4 || i==a->group_count || btp_battle_group_value(s,a,i,BTP_CONDITION_GROUP_ALIVE+kind)!=expected)return fail("Combat group assertion failed");
        }
    } else return fail("Unsupported scenario operation");
    return !failed && btp_json_done(j,node);
}

int main(int argc,char **argv)
{
    const char *scenario=NULL,*artifacts=NULL;char **filtered=calloc((size_t)argc+1,sizeof *filtered);int count=0;
    if(!filtered)return 1;
    for(int i=0;i<argc;++i) {
        if(!strcmp(argv[i],"--scenario") && i+1<argc)scenario=argv[++i];
        else if(!strcmp(argv[i],"--artifacts") && i+1<argc)artifacts=argv[++i];
        else filtered[count++]=argv[i];
    }
    BtpOptions options;int parsed=btp_options(count,filtered,&options);free(filtered);
    if(parsed<=0 || !scenario || !options.project || options.load || options.play_map || options.replay) {
        fputs("Use --project DIRECTORY --scenario FILE, with optional original asset paths. Output goes into the working directory.\n",stderr);return 2;
    }
    BtpJson j={0};char format[64],load_file[1025]={0},load_hash[65]={0};unsigned seed=0;uint8_t random[3];
    if(!btp_json_load(&j,scenario,error.text) || !text_field(&j,1,"format",format,sizeof format) || strcmp(format,"btp-author-scenario-v1") ||
        !optional_number(&j,1,"max_ticks",1,120000,&limit) || !optional_number(&j,1,"seed",1,16777215,&seed)) { fprintf(stderr,"%s\n",error.text);btp_json_close(&j);return 1; }
    unsigned setup=btp_json_optional(&j,1,"checkpoint");
    if(setup && (seed || !text_field(&j,setup,"file",load_file,sizeof load_file) ||
        !text_field(&j,setup,"sha256",load_hash,sizeof load_hash) || !btp_json_done(&j,setup))) {
        fprintf(stderr,"Checkpoint start needs file and SHA-256 and cannot set a seed. %s\n",error.text);btp_json_close(&j);return 1;
    }
    unsigned steps=btp_json_field(&j,1,"steps");
    if(!btp_json_type(&j,steps,'[') || !btp_json_done(&j,1)) {fprintf(stderr,"%s\n",error.text);btp_json_close(&j);return 1;}
    BtpContent content={0};
    if(!btp_cli_load_content(&options,&content,&error)) {fprintf(stderr,"%s\n",error.text);btp_json_close(&j);return 1;}
    const BtpResources *r=content.resources;BtpState *s=calloc(1,sizeof *s);
    if(!s || !btp_adventure(r)) {fail("Scenario needs an authored project and state allocation");goto done;}
    if(setup) {
        /* Resolve beside the scenario before entering its output directory.
           The Python runner copies/pins the input there for portable replay.
           Do not execute the new-game event before loading this state. */
        char path[4096],actual[65];const char *slash=strrchr(scenario,'/'),*back=strrchr(scenario,'\\');
        if(back && (!slash || back>slash))slash=back;
        int absolute=load_file[0]=='/' || load_file[0]=='\\' || (load_file[0] && load_file[1]==':');
        int n=snprintf(path,sizeof path,"%.*s%s",absolute || !slash ? 0 : (int)(slash-scenario+1),scenario,load_file);
        if(n<0 || (size_t)n>=sizeof path) {fail("Checkpoint path is too long");goto done;}
        if(!file_hash(path,actual))goto done;
        if(strcmp(actual,load_hash)) {fail("Checkpoint SHA-256 mismatch; select the exact saved input");goto done;}
        if(!btp_save_load(path,s,r,&error)) {fail(error.text);goto done;}
        resumed=1;
    }
    if(artifacts && change_directory(artifacts)) {fail("Cannot enter scenario artifact directory");goto done;}
    actions=fopen("replay.actions","wb");trace=fopen("events.jsonl","wb");combat_log=fopen("combat.jsonl","wb");
    if(!s || !actions || !trace || !combat_log || !btp_adventure(r)) {fail("Scenario needs an authored project and writable output directory");goto done;}
    random[0]=(uint8_t)seed;random[1]=(uint8_t)(seed>>8);random[2]=(uint8_t)(seed>>16);
    btp_events_observe(event_trace,trace);btp_events_observe_battles(end_metrics,NULL);
    if(!resumed)btp_initial_state_seeded(&options,s,r,seed ? random : NULL);
    starting_tick=s->tick;memcpy(starting_rng,s->npc.rng,3);
    if(s->event.phase==BTP_EVENT_FIGHTING || s->battle_mission.active) {
        begin_metrics(s);metrics_from_checkpoint=resumed;
        if(resumed)battle_policy="saved";
    }
    fputs("{\"initial\":true,\"state\":",stdout);state(s,r);fputs("}\n",stdout);
    for(unsigned node=j.nodes[steps].first;node;node=j.nodes[node].next) {
        if(++step_number>256){fail("At most 256 scenario steps");break;}
        route_present=0;checkpoint_file[0]=0;int ok=execute(&j,node,s,r);
        printf("{\"step\":%u,\"ok\":%s,\"ticks\":%u,\"state\":",step_number,ok?"true":"false",ticks);state(s,r);navigation(r);
        if(checkpoint_file[0])printf(",\"checkpoint\":{\"file\":\"%s\",\"sha256\":\"%s\"}",checkpoint_file,checkpoint_hash);
        fputs("}\n",stdout);
        if(!ok){failed=1;break;}
    }
    capture(s,r,"final.ppm");
    char save[96];save_path(save,"final",r);
    if(!failed && !btp_save_write(save,s,r,&error))failed=1;
    printf("{\"status\":\"%s\",\"ticks\":%u,\"steps\":%u,\"start_tick\":%u,\"start_rng\":[%u,%u,%u],\"seed\":",failed?"failed":"passed",ticks,step_number,starting_tick,starting_rng[0],starting_rng[1],starting_rng[2]);
    if(resumed)fputs("null",stdout);else printf("%u",seed ? seed : 11223583u);
    fputs(",\"rng_policy\":",stdout);string_json(stdout,resumed?"saved checkpoint state (not reseeded)":seed?"explicit 24-bit state before first event":"runtime initial state");
    fputs(",\"message\":",stdout);
    string_json(stdout,error.text);fputs(",\"save\":",stdout);string_json(stdout,save);fputs(",\"state\":",stdout);state(s,r);navigation(r);fputs("}\n",stdout);
done:
    btp_events_observe(NULL,NULL);btp_events_observe_battles(NULL,NULL);if(actions && fclose(actions))failed=1;if(trace && fclose(trace))failed=1;if(combat_log && fclose(combat_log))failed=1;
    if(failed)fprintf(stderr,"%s\n",error.text);
    free(s);btp_content_close(&content);btp_json_close(&j);return failed?1:0;
}
