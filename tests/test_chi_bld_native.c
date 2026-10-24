/* Private-fixture journeys. No source dialogue or decoded programs embedded. */
#include "data/content.h"
#include "data/project.h"
#include "data/chi.h"
#include "data/save.h"
#include "core/npc.h"
#include "core/original_actions.h"
#include "core/combat.h"
#include "core/chi_bridge.h"
#include "frontend/pixels.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static BtpError error;
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"BLD journey %d: %s (%s)\n",__LINE__,#x,error.text);exit(1); } } while (0)
static void held(BtpState *s,const BtpResources *r,const char *save)
{
    BtpState *copy=calloc(1,sizeof *copy);CHECK(copy);CHECK(btp_save_write(save,s,r,&error));CHECK(btp_save_load(save,copy,r,&error));
    uint8_t a[BTP_STATE_BYTES],b[BTP_STATE_BYTES];btp_state_encode(s,a);btp_state_encode(copy,b);CHECK(!memcmp(a,b,sizeof a));free(copy);
}
static void enter_armor(BtpState *s,const BtpResources *r)
{
    btp_start_content(s,r);s->project=1;btp_npc_init(s,&r->map);
    const BtpMap *m=&r->map;unsigned door=0;
    while (door<16 && m->room_map[door]!=4) ++door;
    CHECK(door<16);
    unsigned x=m->entrance_x[door]&127u,y=m->entrance_y[door]&127u;
    CHECK(x && btp_chi_preview(s,r,r->project->chi_spatial->maps[0].id,x-1,y));
    btp_game_tick(s,r,BTP_RIGHT);CHECK(s->mode==BTP_ENTRY);btp_game_tick(s,r,BTP_ACCEPT);
    CHECK(s->mode==BTP_BUILDING && s->script.status==BTP_SCRIPT_WAIT && !s->script.error);
}
int main(int argc,char **argv)
{
    CHECK(argc>=3);BtpContent a={0},b={0};
    if (!strcmp(argv[1],"--roundtrip")) {
        CHECK(argc==3 && btp_content_load_project(&b,argv[2],NULL,&error));
        for (unsigned slot=0;slot<26;++slot) {
            char path[4096];CHECK(snprintf(path,sizeof path,"%s/chi/%s",argv[2],btp_chi_resource_name(27+slot))<(int)sizeof path);
            uint8_t *raw=NULL;size_t length;BtpBld original={0};CHECK(btp_read_file(path,&raw,&length,&error));CHECK(btp_bld_decode(raw,length,&original,&error));free(raw);
            const BtpBld *actual=&b.resources->buildings[slot];CHECK(actual->length==original.length && !memcmp(actual->bytes,original.bytes,original.length));
            const BtpChiProgram *p=&b.resources->project->chi_scripts->programs[slot];
            for (unsigned i=0;i<p->count;++i) CHECK(p->nodes[i].offset==p->nodes[i].origin && p->nodes[i].length==p->nodes[i].original_size);
        }
        btp_content_close(&b);puts("Verified 26 byte-identical compiled BLD payloads and original/source/compiled offsets.");return 0;
    }
    if (!strcmp(argv[1],"--reject")) {
        CHECK(argc==4 && btp_content_load_project(&b,argv[2],NULL,&error));BtpState *s=calloc(1,sizeof *s);CHECK(s);
        CHECK(!btp_save_load(argv[3],s,b.resources,&error));free(s);btp_content_close(&b);puts("Changed BLD content rejects a save from the other revision.");return 0;
    }
    if (!strcmp(argv[1],"--story")) {
        CHECK(argc==4 && btp_content_load_project(&b,argv[2],NULL,&error));
        BtpState *s=calloc(1,sizeof *s);CHECK(s);enter_armor(s,b.resources);
        uint8_t text[BTP_BLD_MAX+1];CHECK(btp_script_text(&s->script,btp_state_bld(b.resources,s),text,sizeof text));
        CHECK(strstr((char *)text,"C4.1"));held(s,b.resources,argv[3]);
        uint32_t *frame=malloc(64000u*sizeof *frame);CHECK(frame);btp_render(b.resources,s,0,frame);free(frame);
        btp_game_tick(s,b.resources,BTP_ACCEPT);
        CHECK(s->script.status==BTP_SCRIPT_MENU && s->script.menu_id==24 && s->script.has_cash && !s->story_flags[80]);
        held(s,b.resources,argv[3]);btp_game_tick(s,b.resources,BTP_ACCEPT);
        CHECK(s->mode==BTP_EXPLORE && s->story_flags[81]==7 && !s->script.error);
        free(s);btp_content_close(&b);puts("Edited BLD text, condition, jump, menu and native action play through real building entry and held saves.");return 0;
    }
    int bridge_compare=!strcmp(argv[1],"--compare-bridge");
    CHECK((!strcmp(argv[1],"--compare") || bridge_compare) && argc==6);
    CHECK(btp_content_load_project(&a,argv[2],NULL,&error) && btp_content_load_project(&b,argv[3],NULL,&error));
    BtpState *x=calloc(1,sizeof *x),*y=calloc(1,sizeof *y),*adjusted=calloc(1,sizeof *adjusted);CHECK(x && y && adjusted);
    btp_start_content(x,a.resources);btp_start_content(y,b.resources);x->project=y->project=1;
    btp_npc_init(x,&a.resources->map);btp_npc_init(y,&b.resources->map);
    if (btp_resources_feature(a.resources,BTP_FEATURE_ENHANCED)) CHECK(btp_set_combat_profile(x,a.resources,1) && btp_set_combat_profile(y,b.resources,1));
    if(bridge_compare) { btp_bridge_initialize(y,b.resources);CHECK(y->bridge.enabled && !x->bridge.enabled); }
    BtpBridgeState initial_bridge=y->bridge;BtpEventState initial_events=y->event;
    uint32_t *pixels=bridge_compare ? malloc(2u*BTP_PIXELS*sizeof *pixels) : NULL;CHECK(!bridge_compare || pixels);
    FILE *f=fopen(argv[4],"r");CHECK(f);char line[128];unsigned ticks=0,held_mask=0;
    while (fgets(line,sizeof line,f)) {
        line[strcspn(line,"\r\n")]=0;if (!*line || *line=='#') continue;BtpAction action;CHECK(btp_action_parse(line,&action));
        btp_game_tick(x,a.resources,action);btp_game_tick(y,b.resources,action);++ticks;
        CHECK(!x->script.error && !y->script.error);
        CHECK(x->script.status==y->script.status && x->script.menu_id==y->script.menu_id && x->script.native_action==y->script.native_action);
        CHECK(x->script.selected==y->script.selected && !memcmp(x->script.choices,y->script.choices,sizeof x->script.choices));
        const BtpBld *program=btp_state_bld(b.resources,y);
        if (x->script.pc && x->mode!=BTP_EXPLORE && x->mode!=BTP_ENTRY && y->script.pc!=btp_bld_after(program,x->script.pc)) {
            fprintf(stderr,"Tick %u mode %u building %u: PC %04x -> %04x, expected %04x (%s)\n",ticks,y->mode,
                btp_building_kind(b.resources,y),x->script.pc,y->script.pc,btp_bld_after(program,x->script.pc),argv[4]);
            CHECK(0);
        }
        /* Text bytes/spans and byte PCs are expected edits. Every other
           encoded gameplay byte, including RNG, economy and party, must match. */
        *adjusted=*x;
        adjusted->script.pc=y->script.pc;adjusted->script.fault_pc=y->script.fault_pc;
        adjusted->script.menu_table=y->script.menu_table;adjusted->script.confirm_target=y->script.confirm_target;adjusted->script.money_target=y->script.money_target;
        adjusted->script.text_offset=y->script.text_offset;adjusted->script.text_length=y->script.text_length;
        memcpy(adjusted->script.text,y->script.text,sizeof y->script.text);
        if(bridge_compare) {
            /* Enabling an unused quest capability changes its save envelope,
               not native play. Account only for that fixed initial metadata. */
            CHECK(!memcmp(&y->bridge,&initial_bridge,sizeof initial_bridge) && !memcmp(&y->event,&initial_events,sizeof initial_events));
            adjusted->bridge=initial_bridge;adjusted->event=initial_events;
        }
        uint8_t one[BTP_STATE_BYTES],two[BTP_STATE_BYTES];
        btp_state_encode(adjusted,one);btp_state_encode(y,two);
        if(memcmp(one,two,sizeof one)) { unsigned at=0;while(at<sizeof one && one[at]==two[at])++at;fprintf(stderr,"Gameplay mismatch tick%u byte%u: %u/%u\n",ticks,at,one[at],two[at]);CHECK(0); }
        unsigned bit=y->school.phase ? 1u<<y->school.phase : y->bank.phase ? 1u<<(4+y->bank.phase) : y->script.status==BTP_SCRIPT_MENU ? 4096u : y->checkpoint_valid ? 8192u : 0u;
        if (y->campaign.invasion && y->late.invasion_event>=3 && y->mode==BTP_MISSION) { CHECK(program==&b.resources->training);bit=16384u; }
        if (bit && !(held_mask&bit)) {
            held(y,b.resources,argv[5]);held_mask|=bit;
            if(pixels) { btp_render(a.resources,x,0,pixels);btp_render(b.resources,y,0,pixels+BTP_PIXELS);CHECK(!memcmp(pixels,pixels+BTP_PIXELS,BTP_PIXELS*sizeof *pixels)); }
        }
        CHECK(ticks<120000);
    }
    CHECK(!fclose(f));CHECK(ticks && held_mask);printf("Verified %u edited-program gameplay/RNG ticks and held continuations: %s\n",ticks,argv[4]);
    free(pixels);free(x);free(y);free(adjusted);btp_content_close(&a);btp_content_close(&b);return 0;
}
