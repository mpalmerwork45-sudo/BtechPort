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
            puts("BtechPort M2b: MAP1 exploration, Citadel Hall and first Katrina visit\n"
                 "  --data DIRECTORY     original resource directory (default: Original DOS)\n"
                 "  --headless           run without SDL/display/audio\n"
                 "  --replay FILE        logical actions: up/down/left/right/idle/accept/cancel\n"
                 "  --trace              print canonical JSON state after each replay action\n"
                 "  --frame FILE         write final 320x200 RGB PPM\n"
                 "  --export-tiles FILE  write 64000 decoded tile pixel indices\n"
                 "  --record FILE        native logical input log for replay (includes idle ticks)\n"
                 "  --debug              collision overlay and diagnostics (F3 toggles)\n"
                 "  --smoke              bounded native SDL event/presentation check\n"
                 "  --smoke-citadel      bounded native Citadel entry/dialogue/exit check\n"
                 "  --smoke-katrina      bounded native Katrina/repeat/exit/re-entry check\n"
                 "Native controls: arrows move/select, Enter/Space confirms/continues,\n"
                 "Backspace declines/recovers unsupported choices, R restarts, F3 debug, Esc quits.");
            return -1;
        }
        if (!strcmp(arg, "--headless")) o->headless = 1;
        else if (!strcmp(arg, "--debug")) o->debug = 1;
        else if (!strcmp(arg, "--trace")) o->trace = 1;
        else if (!strcmp(arg, "--smoke")) o->smoke = 1;
        else if (!strcmp(arg, "--smoke-citadel")) o->smoke = 2;
        else if (!strcmp(arg, "--smoke-katrina")) o->smoke = 3;
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

void btp_print_state(const BtpState *s, const BtpResources *r)
{
    uint32_t digest = s->script.text_length ? UINT32_C(2166136261) : 0;
    uint8_t body[BTP_BLD_MAX + 1];
    if (btp_script_text(&s->script, &r->citadel, body, sizeof body))
        for (unsigned i = 0; i < s->script.text_length; ++i)
            digest = (digest ^ body[i]) * UINT32_C(16777619);
    printf("{\"map\":%u,\"mode\":\"%s\",\"x_half\":%u,\"y_half\":%u,"
           "\"tile\":[%u,%u],\"gate\":%u,\"tick\":%u,\"blocked\":%u,"
           "\"script_pc\":%u,\"script_status\":%u,\"script_opcode\":%u,\"script_error\":%u,"
           "\"fault_pc\":%u,\"menu_selected\":%u,\"text_offset\":%u,\"text_length\":%u,"
           "\"text_digest\":%u,\"story_flags\":[",
           s->map_id, btp_mode_name(s->mode), s->x_half, s->y_half, s->x_half / 2, s->y_half / 2,
           s->gate, s->tick, s->blocked, s->script.pc, s->script.status, s->script.last_opcode,
           s->script.error, s->script.fault_pc, s->script.selected, s->script.text_offset,
           s->script.text_length, digest);
    for (unsigned i = 0; i < BTP_STORY_BYTES; ++i) printf("%s%u", i ? "," : "", s->story_flags[i]);
    fputs("],\"text_spans\":[", stdout);
    for (unsigned i = 0; i < s->script.text_count && i < BTP_TEXT_SPANS; ++i)
        printf("%s[%u,%u]", i ? "," : "", s->script.text[i].offset, s->script.text[i].length);
    puts("]}");
}

int btp_replay(const char *path, BtpState *s, const BtpResources *r, int trace)
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
        btp_game_tick(s, r, a);
        if (trace) btp_print_state(s, r);
    }
    int ok = !ferror(f);
    if (fclose(f)) ok = 0;
    if (s->mode == BTP_SCRIPT_FAULT) {
        fprintf(stderr, "BLD %s at payload 0x%04x (opcode 0x%02x)\n",
            btp_script_error_name(s->script.error), s->script.fault_pc, s->script.last_opcode);
        ok = 0;
    }
    return ok;
}

int btp_run_headless(const BtpOptions *o, BtpResources *r)
{
    BtpState state; btp_start(&state);
    int result = 0;
    if (o->record || o->smoke) { fputs("--record/--smoke require the native frontend\n", stderr); return 1; }
    if (o->trace) btp_print_state(&state, r);
    if (o->replay && !btp_replay(o->replay, &state, r, o->trace)) {
        if (state.mode != BTP_SCRIPT_FAULT) return 1;
        result = 1; /* A requested frame can still show the explicit script fault. */
    }
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
    if (!o->trace) btp_print_state(&state, r);
    return result;
}
