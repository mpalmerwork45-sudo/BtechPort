#ifndef BTP_CLI_H
#define BTP_CLI_H
#include "frontend/pixels.h"
#include "data/content.h"
typedef struct {
    const char *data, *dialogue_data, *combat_data, *world_data, *replay, *record, *frame, *tiles_output, *sprites_output;
    const char *save_file, *load, *save, *audio_report, *export_original;
    int sprite_preview, world_overview, headless, debug, trace, smoke, smoke_fast, conversation_checkpoint, shop_talk_checkpoint;
    int title_preview,intro_preview,mute;
} BtpOptions;
int btp_options(int argc, char **argv, BtpOptions *options);
int btp_cli_load_content(const BtpOptions *options, BtpContent *content, BtpError *error);
void btp_initial_state(const BtpOptions *options, BtpState *state, const BtpResources *resources);
void btp_print_state(const BtpState *state, const BtpResources *resources);
int btp_replay(const char *path, BtpState *state, const BtpResources *resources, int trace,const char *save_base);
int btp_run_headless(const BtpOptions *options, BtpResources *resources);
#endif
