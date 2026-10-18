/* Bounded authoring scenarios over the real player. No command grants a
   victory, teleports the party or edits mission flags. Controlled starting
   setups and richer battle policies belong to a later scenario milestone. */
#include "frontend/cli.h"
#include "frontend/authored_route.h"
#include "core/events.h"
#include "core/party.h"
#include "core/combat.h"
#include "data/json.h"
#include "data/save.h"
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
static FILE *actions,*trace;
static BtpError error;

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
{ if (!failed) snprintf(error.text,sizeof error.text,"%s",message);failed=1;return 0; }
static void input(BtpState *s,const BtpResources *r,BtpAction action)
{
    if (failed) return;
    if (ticks>=limit) { fail("Scenario exceeded its logical tick budget");return; }
    fprintf(actions,"%s\n",btp_action_name(action));++ticks;btp_game_tick(s,r,action);
    if (s->mode==BTP_SCRIPT_FAULT || s->event.phase==BTP_EVENT_FAULT) fail("Runtime event or script fault");
}
static void event_trace(void *context,const BtpState *s,const BtpResources *r,const BtpEventNode *e)
{
    FILE *f=context;const BtpAdventure *a=btp_adventure(r);
    fprintf(f,"{\"tick\":%u,\"event\":\"%s\",\"credits\":%u,\"flags\":{",s->tick,e->id,s->credits);
    for(unsigned i=0;i<a->flag_count;++i)fprintf(f,"%s\"%s\":%u",i?",":"",a->flags[i],s->event.flags[i]);
    fputs("}}\n",f);
}
static const char *phase_name(unsigned phase)
{
    static const char *names[]={"exploration","entry","text","choice","shop","battle","fault","complete"};
    return phase<8 ? names[phase] : "unknown";
}
static void state(const BtpState *s,const BtpResources *r)
{
    const BtpAdventure *a=btp_adventure(r);const BtpScene *scene=btp_scene(r,s);
    fputs("{\"map\":",stdout);string_json(stdout,scene ? scene->id : "");
    printf(",\"at\":[%u,%u],\"credits\":%u,\"phase\":\"%s\",\"event\":",s->x_half,s->y_half,s->credits,phase_name(s->event.phase));
    string_json(stdout,s->event.node<a->node_count ? a->nodes[s->event.node].id : "");
    printf(",\"party_count\":%u,\"flags\":{",btp_party_count(&s->party));
    for(unsigned i=0;i<a->flag_count;++i)printf("%s\"%s\":%u",i?",":"",a->flags[i],s->event.flags[i]);
    printf("},\"battle\":{\"won\":%u,\"fled\":%u,\"round\":%u},\"objectives\":{",s->combat.won,s->combat.fled,s->combat.round);
    for(unsigned i=0;i<a->objective_count;++i) {
        const BtpObjective *o=&a->objectives[i];
        printf("%s\"%s\":\"%s\"",i?",":"",o->id,s->event.flags[o->complete] ? "complete" : s->event.flags[o->active] ? "active" : "inactive");
    }
    fputs("}}",stdout);
}
static int text_field(BtpJson *j,unsigned node,const char *key,char *value,size_t size)
{ return btp_json_string(j,btp_json_field(j,node,key),value,size); }
static int optional_number(BtpJson *j,unsigned node,const char *key,unsigned low,unsigned high,unsigned *value)
{ unsigned n=btp_json_optional(j,node,key);return !n || btp_json_uint(j,n,low,high,value); }
static int checkpoint(BtpState *s,const BtpResources *r)
{
    BtpState *loaded=malloc(sizeof *loaded);uint8_t *before=malloc(BTP_STATE_BYTES),*after=malloc(BTP_STATE_BYTES);
    int ok=loaded && before && after && btp_save_write("checkpoint.btp",s,r,&error) && btp_save_load("checkpoint.btp",loaded,r,&error);
    if(ok) { btp_state_encode(s,before);btp_state_encode(loaded,after);ok=!memcmp(before,after,BTP_STATE_BYTES); }
    if(ok)*s=*loaded;
    free(loaded);free(before);free(after);return ok || fail("Save/reload failed or changed logical state");
}
static int capture(const BtpState *s,const BtpResources *r,const char *path)
{
    uint32_t *pixels=malloc(BTP_PIXELS*sizeof *pixels);if(!pixels)return fail("Frame allocation failed");
    btp_render(r,s,0,pixels);int ok=btp_write_ppm(path,pixels);free(pixels);return ok || fail("Cannot write frame");
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
        if(!text_field(j,node,"entrance",value,sizeof value))return 0;
        if(!authored_walk_to(s,r,value,input))return fail("Entrance is absent, unreachable, or walking was interrupted");
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
        if(!text_field(j,node,"control",value,sizeof value) || strcmp(value,"computer"))return fail("This scenario runner supports computer control only");
        if(s->event.phase!=BTP_EVENT_FIGHTING || s->combat.phase!=BTP_COMBAT_CONTROL)return fail("Battle requires the initial computer-control prompt");
        input(s,r,BTP_UP);input(s,r,BTP_ACCEPT);input(s,r,BTP_ACCEPT);input(s,r,BTP_ACCEPT);
        while(s->event.phase==BTP_EVENT_FIGHTING && !failed)input(s,r,s->combat.phase==BTP_COMBAT_NOTICE ? BTP_ACCEPT : BTP_IDLE);
    } else if(!strcmp(op,"checkpoint")) {
        if(!checkpoint(s,r))return 0;
    } else if(!strcmp(op,"capture")) {
        char path[64];snprintf(path,sizeof path,"step-%03u.ppm",step_number);
        if(!capture(s,r,path))return 0;
    } else if(!strcmp(op,"assert")) {
        unsigned n,expected;const BtpAdventure *a=btp_adventure(r);
        n=btp_json_optional(j,node,"credits");if(n && (!btp_json_uint(j,n,0,16777215,&expected) || expected!=s->credits))return fail("Credit assertion failed");
        n=btp_json_optional(j,node,"party_count");if(n && (!btp_json_uint(j,n,1,8,&expected) || expected!=btp_party_count(&s->party)))return fail("Party assertion failed");
        n=btp_json_optional(j,node,"phase");if(n && (!btp_json_string(j,n,value,sizeof value) || strcmp(value,phase_name(s->event.phase))))return fail("Event phase assertion failed");
        n=btp_json_optional(j,node,"map");if(n && (!btp_json_string(j,n,value,sizeof value) || !btp_scene(r,s) || strcmp(value,btp_scene(r,s)->id)))return fail("Map assertion failed");
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
            const BtpObjective *o=&a->objectives[i];const char *actual=s->event.flags[o->complete] ? "complete" : s->event.flags[o->active] ? "active" : "inactive";
            if(strcmp(actual,status))return fail("Objective state assertion failed");
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
    BtpJson j={0};char format[64];
    if(!btp_json_load(&j,scenario,error.text) || !text_field(&j,1,"format",format,sizeof format) || strcmp(format,"btp-author-scenario-v1") ||
        !optional_number(&j,1,"max_ticks",1,120000,&limit)) { fprintf(stderr,"%s\n",error.text);btp_json_close(&j);return 1; }
    unsigned steps=btp_json_field(&j,1,"steps");
    if(!btp_json_type(&j,steps,'[') || !btp_json_done(&j,1)) {fprintf(stderr,"%s\n",error.text);btp_json_close(&j);return 1;}
    BtpContent content={0};
    if(!btp_cli_load_content(&options,&content,&error)) {fprintf(stderr,"%s\n",error.text);btp_json_close(&j);return 1;}
    const BtpResources *r=content.resources;BtpState *s=calloc(1,sizeof *s);
    if(artifacts && change_directory(artifacts)) {fail("Cannot enter scenario artifact directory");goto done;}
    actions=fopen("replay.actions","wb");trace=fopen("events.jsonl","wb");
    if(!s || !actions || !trace || !btp_adventure(r)) {fail("Scenario needs an authored project and writable output directory");goto done;}
    btp_events_observe(event_trace,trace);btp_initial_state(&options,s,r);
    for(unsigned node=j.nodes[steps].first;node;node=j.nodes[node].next) {
        if(++step_number>256){fail("At most 256 scenario steps");break;}
        int ok=execute(&j,node,s,r);
        printf("{\"step\":%u,\"ok\":%s,\"ticks\":%u,\"state\":",step_number,ok?"true":"false",ticks);state(s,r);fputs("}\n",stdout);
        if(!ok){failed=1;break;}
    }
    capture(s,r,"final.ppm");
    if(!failed && !btp_save_write("final.btp",s,r,&error))failed=1;
    printf("{\"status\":\"%s\",\"ticks\":%u,\"steps\":%u,\"rng_policy\":\"runtime initial state\",\"message\":",failed?"failed":"passed",ticks,step_number);
    string_json(stdout,error.text);fputs(",\"state\":",stdout);state(s,r);fputs("}\n",stdout);
done:
    btp_events_observe(NULL,NULL);if(actions && fclose(actions))failed=1;if(trace && fclose(trace))failed=1;
    if(failed)fprintf(stderr,"%s\n",error.text);
    free(s);btp_content_close(&content);btp_json_close(&j);return failed?1:0;
}
