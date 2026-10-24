#ifndef BTP_CLI_H
#define BTP_CLI_H
#include "frontend/pixels.h"
#include "data/content.h"
#include <stdio.h>
typedef struct {
    const char *data, *dialogue_data, *combat_data, *world_data, *replay, *record, *frame, *tiles_output, *sprites_output;
    const char *save_file, *load, *save, *audio_report, *export_original, *roster, *project;
    const char *play_map,*event_trace,*bld_trace;unsigned play_x,play_y;
    unsigned explicit_dependencies;
    int sprite_preview, world_overview, headless, debug, trace, smoke, smoke_fast, conversation_checkpoint, shop_talk_checkpoint;
    int title_preview,intro_preview,mute;
    BtpContentProfile edition; /* NONE asks on an ordinary interactive launch. */
} BtpOptions;
typedef struct {
    FILE *file;
    const BtpState *state;
    const BtpResources *resources;
    unsigned last_fault[5],previous_fault;
} BtpBldTrace;
int btp_bld_trace_open(BtpBldTrace *trace,const BtpOptions *options,const BtpResources *resources,BtpError *error);
void btp_bld_trace_bind(BtpBldTrace *trace,const BtpState *state);
int btp_bld_trace_close(BtpBldTrace *trace);
int btp_options(int argc, char **argv, BtpOptions *options);
int btp_cli_load_content(const BtpOptions *options, BtpContent *content, BtpError *error);
void btp_initial_state(const BtpOptions *options, BtpState *state, const BtpResources *resources);
void btp_initial_state_seeded(const BtpOptions *options,BtpState *state,const BtpResources *resources,const uint8_t seed[3]);
void btp_print_state(const BtpState *state, const BtpResources *resources);
int btp_replay(const char *path, BtpState *state, const BtpResources *resources, int trace,const char *save_base);
int btp_run_headless(const BtpOptions *options, BtpResources *resources);
#endif
