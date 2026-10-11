#define SDL_MAIN_HANDLED
#include <SDL.h>
#include "frontend/cli.h"
#include "data/save.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static BtpAction key_action(SDL_Keycode key)
{
    if (key >= SDLK_0 && key <= SDLK_9) return (BtpAction)(BTP_DIGIT_0+key-SDLK_0);
    if (key >= SDLK_KP_1 && key <= SDLK_KP_9) return (BtpAction)(BTP_DIGIT_1+key-SDLK_KP_1);
    switch (key) {
        case SDLK_UP: return BTP_UP;
        case SDLK_DOWN: return BTP_DOWN;
        case SDLK_LEFT: return BTP_LEFT;
        case SDLK_RIGHT: return BTP_RIGHT;
        case SDLK_RETURN: case SDLK_KP_ENTER: case SDLK_SPACE: return BTP_ACCEPT;
        case SDLK_KP_0: return BTP_DIGIT_0;
        case SDLK_ESCAPE: return BTP_CLEAR_INPUT;
        case SDLK_BACKSPACE: return BTP_CANCEL;
        default: return BTP_IDLE;
    }
}
int main(int argc, char **argv)
{
    BtpOptions o;
    int parsed = btp_options(argc, argv, &o);
    if (parsed <= 0) return parsed == -1 ? 0 : 1;
    BtpResources *r = malloc(sizeof *r);
    uint32_t *frame = malloc(BTP_PIXELS * sizeof *frame);
    BtpError error;
    int result = 1;
    if (!r || !frame) { free(r); free(frame); return 1; }
    if (!btp_resources_load(o.data, r, &error) || !btp_dialogue_load(o.dialogue_data,&r->dialogue,&error)) {
        fprintf(stderr, "%s\nRun python3 tools/prepare_talk.py to prepare the dialogue cache.\n", error.text); goto done;
    }
    if (o.headless) { result = btp_run_headless(&o, r); goto done; }
    if (o.tiles_output) { fputs("--export-tiles requires --headless\n", stderr); goto done; }
    BtpState state; btp_initial_state(&o,&state,r);
    if (o.load && !btp_save_load(o.load,&state,r,&error)) { fprintf(stderr,"%s\n",error.text); goto done; }
    if (o.replay && o.smoke < 5 && !btp_replay(o.replay, &state, r, o.trace)) goto done;
    SDL_SetMainReady();
    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_EVENTS | SDL_INIT_TIMER)) {
        fprintf(stderr, "SDL: %s\n", SDL_GetError()); goto done;
    }
    SDL_SetHint(SDL_HINT_RENDER_SCALE_QUALITY, "0");
    SDL_Window *window = SDL_CreateWindow("BtechPort M2h - MAP1, paid classes and save/load", SDL_WINDOWPOS_CENTERED,
        SDL_WINDOWPOS_CENTERED, 960, 600, SDL_WINDOW_RESIZABLE);
    SDL_Renderer *renderer = window ? SDL_CreateRenderer(window, -1, SDL_RENDERER_SOFTWARE) : NULL;
    SDL_Texture *texture = renderer ? SDL_CreateTexture(renderer, SDL_PIXELFORMAT_ARGB8888,
        SDL_TEXTUREACCESS_STREAMING, 320, 200) : NULL;
    FILE *record = NULL;
    FILE *arrival = NULL;
    if (!texture || SDL_RenderSetLogicalSize(renderer, 320, 200)) goto sdl_done;
    if (o.record) { record = fopen(o.record, "w"); if (!record) goto sdl_done; }
    if (o.smoke >= 5) { arrival = fopen(o.replay,"r"); if (!arrival) goto sdl_done; }
    BtpAction queue[256]; unsigned read = 0, write = 0;
    uint64_t last = SDL_GetTicks64(), accumulator = 0;
    unsigned smoke_ticks = 0;
    unsigned smoke_sent = 0, tail_sent = 0;
    int arrival_done = 0;
    int running = 1, io_failed = 0;
    const char *notice = NULL;
    uint64_t notice_until = 0;
    if (o.smoke && o.smoke < 5) {
        const SDL_Keycode smoke_keys[] = {SDLK_RIGHT, SDLK_UP, SDLK_DOWN};
        const SDL_Keycode citadel_keys[] = {SDLK_UP,SDLK_UP,SDLK_UP,SDLK_UP,SDLK_UP,
            SDLK_RETURN,SDLK_DOWN,SDLK_RETURN,SDLK_SPACE,SDLK_SPACE,SDLK_SPACE,
            SDLK_SPACE,SDLK_SPACE,SDLK_SPACE,SDLK_DOWN,SDLK_DOWN,SDLK_DOWN,SDLK_RETURN,SDLK_DOWN};
        const SDL_Keycode katrina_keys[] = {SDLK_UP,SDLK_UP,SDLK_UP,SDLK_UP,SDLK_UP,
            SDLK_RETURN,SDLK_RETURN,SDLK_SPACE,SDLK_SPACE,SDLK_RETURN,SDLK_SPACE,
            SDLK_DOWN,SDLK_DOWN,SDLK_DOWN,SDLK_DOWN,SDLK_RETURN,SDLK_DOWN,SDLK_UP,SDLK_RETURN};
        const SDL_Keycode talk_keys[] = {SDLK_UP,SDLK_UP,SDLK_UP,SDLK_UP,SDLK_UP,SDLK_RETURN,
            SDLK_DOWN,SDLK_DOWN,SDLK_DOWN,SDLK_RETURN,SDLK_DOWN,SDLK_RETURN,SDLK_RETURN,
            SDLK_UP,SDLK_RETURN,SDLK_SPACE,SDLK_DOWN,SDLK_RETURN,SDLK_DOWN};
        const SDL_Keycode *keys = o.smoke == 1 ? smoke_keys : o.smoke == 2 ? citadel_keys :
            o.smoke == 3 ? katrina_keys : talk_keys;
        unsigned count = o.smoke == 1 ? 3 : o.smoke == 2 ?
            (unsigned)(sizeof citadel_keys / sizeof citadel_keys[0]) : o.smoke == 3 ?
            (unsigned)(sizeof katrina_keys / sizeof katrina_keys[0]) : (unsigned)(sizeof talk_keys / sizeof talk_keys[0]);
        for (unsigned i = 0; i < count; ++i) {
            SDL_Event event = {.type = SDL_KEYDOWN};
            event.key.keysym.sym = keys[i];
            if (SDL_PushEvent(&event) != 1) goto sdl_done;
        }
    }
    while (running) {
        if (o.smoke >= 5 && smoke_sent == smoke_ticks) {
            BtpAction a = BTP_IDLE; char line[64];
            if (!arrival_done) {
                if (fgets(line,sizeof line,arrival)) {
                    size_t length = strlen(line);
                    if (length && line[length-1] != '\n' && !feof(arrival)) {
                        fputs("Arrival smoke replay line too long\n",stderr); io_failed = 1; break;
                    }
                    line[strcspn(line,"\r\n")] = 0;
                    if (!btp_action_parse(line,&a)) { io_failed = 1; break; }
                } else {
                    if (ferror(arrival)) { io_failed = 1; break; }
                    arrival_done = 1;
                }
            }
            if (arrival_done) {
                static const BtpAction tail[] = {BTP_ACCEPT,BTP_DOWN,BTP_ACCEPT,BTP_DOWN,
                    BTP_IDLE,BTP_IDLE,BTP_IDLE,BTP_IDLE,BTP_IDLE};
                unsigned count = o.smoke == 5 ? (unsigned)(sizeof tail/sizeof tail[0]) : 5u;
                if (tail_sent == count) { running = 0; break; }
                a = o.smoke == 5 ? tail[tail_sent] : BTP_IDLE; ++tail_sent;
            }
            if (++smoke_sent > 8192) { fputs("Arrival smoke exceeded input bound\n",stderr); io_failed = 1; break; }
            if (a != BTP_IDLE) {
                static const SDL_Keycode codes[] = {0,SDLK_UP,SDLK_DOWN,SDLK_LEFT,SDLK_RIGHT,SDLK_RETURN,SDLK_BACKSPACE,
                    SDLK_0,SDLK_1,SDLK_2,SDLK_3,SDLK_4,SDLK_5,SDLK_6,SDLK_7,SDLK_8,SDLK_9,SDLK_ESCAPE};
                SDL_Event injected = {.type=SDL_KEYDOWN}; injected.key.keysym.sym = codes[a];
                if (SDL_PushEvent(&injected) != 1) { io_failed = 1; break; }
            }
        }
        SDL_Event event;
        while (SDL_PollEvent(&event)) {
            if (event.type == SDL_QUIT) running = 0;
            if (event.type == SDL_KEYDOWN) {
                SDL_Keycode key = event.key.keysym.sym;
                if (key == SDLK_ESCAPE && state.bank.phase != BTP_BANK_AMOUNT) running = 0;
                else if (key == SDLK_F3 && !event.key.repeat) o.debug = !o.debug;
                else if ((key == SDLK_F5 || key == SDLK_F9) && !event.key.repeat) {
                    int saving = key == SDLK_F5;
                    int ok;
                    if (!saving && record) {
                        fputs("Loading while recording is unsupported; start a new log after loading.\n",stderr);
                        ok = 0;
                    } else {
                        ok = saving ? btp_save_write(o.save_file,&state,r,&error) :
                            btp_save_load(o.save_file,&state,r,&error);
                        if (!ok) fprintf(stderr,"%s\n",error.text);
                    }
                    if (ok && !saving) { read = write = 0; accumulator = 0; last = SDL_GetTicks64(); }
                    notice = ok ? (saving ? "Saved" : "Loaded") : (saving ? "Save failed" : "Load failed");
                    notice_until = SDL_GetTicks64()+3000;
                    SDL_SetWindowTitle(window,notice);
                }
                else if (key == SDLK_r && !event.key.repeat) {
                    if (record) { fputs("Restart while recording is unsupported; start a new log.\n", stderr); }
                    else { btp_initial_state(&o,&state,r); read = write = 0; }
                } else {
                    BtpAction a = state.bank.phase == BTP_BANK_AMOUNT && key == SDLK_SPACE ?
                        BTP_IDLE : key_action(key);
                    if (a != BTP_IDLE) {
                        if (write - read == 256) { fputs("Input queue full\n", stderr); io_failed = 1; running = 0; }
                        else queue[write++ % 256] = a;
                    }
                }
            }
        }
        uint64_t now = SDL_GetTicks64(); accumulator += now - last; last = now;
        /* 32ms fixed simulation steps. Platform repeat/pacing remains approximate. */
        while (accumulator >= 32 && running) {
            accumulator -= 32;
            BtpAction a = read != write ? queue[read++ % 256] : BTP_IDLE;
            btp_game_tick(&state, r, a);
            if (record && fprintf(record, "%s\n", btp_action_name(a)) < 0) { io_failed = 1; running = 0; }
            if (o.smoke) {
                ++smoke_ticks;
                if (o.smoke < 5 && smoke_ticks >= (o.smoke == 1 ? 8u : 24u)) running = 0;
            }
            if (o.smoke >= 5) break; /* Inject exactly one input for each fixed step. */
        }
        btp_render(r, &state, o.debug, frame);
        if (SDL_UpdateTexture(texture, NULL, frame, 320 * (int)sizeof *frame) ||
            SDL_RenderClear(renderer) || SDL_RenderCopy(renderer, texture, NULL, NULL)) {
            io_failed = 1; running = 0;
        }
        SDL_RenderPresent(renderer);
        if (notice && SDL_GetTicks64() >= notice_until) {
            notice = NULL; SDL_SetWindowTitle(window,"BtechPort M2h - MAP1, paid classes and save/load");
        }
        if (o.debug && !notice) {
            char title[200];
            snprintf(title, sizeof title, "BtechPort M2h | %s | half=(%u,%u) | PC=%04x op=%02x | tick=%u",
                btp_mode_name(state.mode), state.x_half, state.y_half, state.script.pc,
                state.script.last_opcode, state.tick);
            SDL_SetWindowTitle(window, title);
        }
        SDL_Delay(2);
    }
    btp_print_state(&state, r);
    if (o.frame && !btp_write_ppm(o.frame, frame)) io_failed = 1;
    if ((o.smoke == 1 && (state.x_half != 70 || state.y_half != 25 || state.tick != 8)) ||
        (o.smoke == 2 && (state.x_half != 69 || state.y_half != 21 || state.tick != 24 ||
            state.mode != BTP_EXPLORE || state.script.status != BTP_SCRIPT_END || state.story_flags[10] != 1)) ||
        (o.smoke == 3 && (state.x_half != 69 || state.y_half != 21 || state.tick != 24 ||
            state.mode != BTP_BUILDING || state.script.status != BTP_SCRIPT_MENU || state.script.selected != 4 ||
            state.story_flags[6] != 1 || state.story_flags[10] != 1 || state.story_flags[22] != 255))) {
        fputs("Native smoke input/state mismatch\n", stderr); io_failed = 1;
    }
    result = io_failed ? 1 : 0;
    if (o.smoke == 5 && (state.mode != BTP_EXPLORE || state.x_half != 69 || state.y_half != 21 ||
        state.conversation_checkpoint || state.npc.enabled != 2 || state.npc.fault || state.story_flags[13] != 1)) {
        fputs("Native arrival smoke input/state mismatch\n",stderr); result = 1;
    }
    if (o.smoke == 6 && (state.mode != BTP_EXPLORE || state.x_half != 32 || state.y_half != 44 ||
        state.conversation_checkpoint || state.npc.enabled != 2 || state.npc.fault ||
        state.weapon != 1 || state.armor != 1 || state.armor_points != 25)) {
        fputs("Native shops smoke input/state mismatch\n",stderr); result = 1;
    }
    if (!result && o.save && !btp_save_write(o.save,&state,r,&error)) {
        fprintf(stderr,"%s\n",error.text); result = 1;
    }
sdl_done:
    if (arrival && fclose(arrival)) result = 1;
    if (record && fclose(record)) result = 1;
    if (result) fprintf(stderr, "Native frontend failed: %s\n", SDL_GetError());
    if (texture) SDL_DestroyTexture(texture);
    if (renderer) SDL_DestroyRenderer(renderer);
    if (window) SDL_DestroyWindow(window);
    SDL_Quit();
done:
    free(frame); free(r);
    return result;
}
