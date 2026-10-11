#include "frontend/cli.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int btp_options(int argc, char **argv, BtpOptions *o)
{
    *o = (BtpOptions){.data = "Original DOS"};
    for (int i = 1; i < argc; ++i) {
        const char *arg = argv[i];
        if (!strcmp(arg, "--help")) {
            puts("BtechPort M1: MAP1 exploration\n"
                 "  --data DIRECTORY     original resource directory (default: Original DOS)\n"
                 "  --headless           run without SDL/display/audio\n"
                 "  --replay FILE        one logical action per line: up/down/left/right/idle\n"
                 "  --trace              print canonical JSON state after each replay action\n"
                 "  --frame FILE         write final 320x200 RGB PPM\n"
                 "  --export-tiles FILE  write 64000 decoded tile pixel indices\n"
                 "  --record FILE        native logical input log for replay (includes idle ticks)\n"
                 "  --debug              collision overlay and diagnostics (F3 toggles)\n"
                 "  --smoke              bounded native SDL event/presentation check\n"
                 "Native controls: arrows move, R restarts, F3 debug, Esc quits.");
            return -1;
        }
        if (!strcmp(arg, "--headless")) o->headless = 1;
        else if (!strcmp(arg, "--debug")) o->debug = 1;
        else if (!strcmp(arg, "--trace")) o->trace = 1;
        else if (!strcmp(arg, "--smoke")) o->smoke = 1;
        else {
            const char **value = NULL;
            if (!strcmp(arg, "--data")) value = &o->data;
            if (!strcmp(arg, "--replay")) value = &o->replay;
            if (!strcmp(arg, "--frame")) value = &o->frame;
            if (!strcmp(arg, "--record")) value = &o->record;
            if (!strcmp(arg, "--export-tiles")) value = &o->tiles_output;
            if (!value || i + 1 == argc) { fprintf(stderr, "Unknown/incomplete option: %s\n", arg); return 0; }
            *value = argv[++i];
        }
    }
    return 1;
}

void btp_print_state(const BtpState *s)
{
    printf("{\"map\":%u,\"mode\":\"local-exploration\",\"x_half\":%u,\"y_half\":%u,"
           "\"tile\":[%u,%u],\"gate\":%u,\"tick\":%u,\"blocked\":%u}\n",
           s->map_id, s->x_half, s->y_half, s->x_half / 2, s->y_half / 2, s->gate, s->tick, s->blocked);
}

int btp_replay(const char *path, BtpState *s, const BtpMap *m, int trace)
{
    FILE *f = fopen(path, "r");
    if (!f) { fprintf(stderr, "Cannot read replay: %s\n", path); return 0; }
    char line[64]; unsigned number = 0;
    while (fgets(line, sizeof line, f)) {
        ++number;
        size_t n = strlen(line);
        if (n && line[n-1] != '\n' && !feof(f)) {
            fprintf(stderr, "Replay line %u too long\n", number); fclose(f); return 0;
        }
        line[strcspn(line, "\r\n")] = 0;
        BtpAction a;
        if (!btp_action_parse(line, &a)) {
            fprintf(stderr, "Unsupported replay action on line %u: %s\n", number, line);
            fclose(f); return 0;
        }
        btp_tick(s, m, a);
        if (trace) btp_print_state(s);
    }
    int ok = !ferror(f);
    if (fclose(f)) ok = 0;
    return ok;
}

int btp_run_headless(const BtpOptions *o, BtpResources *r)
{
    BtpState state; btp_start(&state);
    if (o->record || o->smoke) { fputs("--record/--smoke require the native frontend\n", stderr); return 1; }
    if (o->trace) btp_print_state(&state);
    if (o->replay && !btp_replay(o->replay, &state, &r->map, o->trace)) return 1;
    if (o->tiles_output) {
        FILE *f = fopen(o->tiles_output, "wb");
        if (!f) return 1;
        int ok = fwrite(r->tiles.pixels, 1, BTP_PIXELS, f) == BTP_PIXELS;
        if (fclose(f)) ok = 0;
        if (!ok) return 1;
    }
    if (o->frame) {
        uint32_t *frame = malloc(sizeof(*frame) * BTP_PIXELS);
        if (!frame) return 1;
        btp_render(r, &state, o->debug, frame);
        int ok = btp_write_ppm(o->frame, frame);
        free(frame);
        if (!ok) { fputs("Frame write failed\n", stderr); return 1; }
    }
    if (!o->trace) btp_print_state(&state);
    return 0;
}
