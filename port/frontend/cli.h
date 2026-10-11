#ifndef BTP_CLI_H
#define BTP_CLI_H
#include "frontend/pixels.h"
typedef struct {
    const char *data, *replay, *record, *frame, *tiles_output;
    int headless, debug, trace, smoke;
} BtpOptions;
int btp_options(int argc, char **argv, BtpOptions *options);
void btp_print_state(const BtpState *state);
int btp_replay(const char *path, BtpState *state, const BtpMap *map, int trace);
int btp_run_headless(const BtpOptions *options, BtpResources *resources);
#endif
