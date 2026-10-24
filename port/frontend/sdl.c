#define SDL_MAIN_HANDLED
#include <SDL.h>
#include "frontend/cli.h"
#include "data/project.h"
#include "data/save.h"
#include "core/audio.h"
#include "core/combat.h"
#include "core/menu.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int movement_mode(const BtpState *s)
{
    return s->mode == BTP_EXPLORE || s->mode==BTP_CACHE || (s->mode==BTP_YARD && !s->yard.phase) || (s->mode == BTP_MISSION && s->mission.phase == BTP_MISSION_DRIVE) ||
        (s->mode==BTP_ENCOUNTER && s->combat.phase==BTP_COMBAT_MOVE);
}
static int amount_editor(const BtpState *s)
{
    return s->bank.phase==BTP_BANK_AMOUNT || s->service.phase==5;
}
static SDL_Keycode navigation_key(SDL_Keycode key,SDL_Keymod modifiers)
{
    /* SDL reports keypad keycodes separately even with Num Lock off. Menus
       need the same arrow actions as the main cluster; Num Lock preserves
       numeric entry in the bank and ammunition editors. */
    if (!(modifiers&KMOD_NUM)) switch (key) {
    case SDLK_KP_8:return SDLK_UP;
    case SDLK_KP_2:return SDLK_DOWN;
    case SDLK_KP_4:return SDLK_LEFT;
    case SDLK_KP_6:return SDLK_RIGHT;
    default:break;
    }
    return key;
}
static unsigned arrow_bit(SDL_Keycode key)
{
    return key == SDLK_UP ? 1u : key == SDLK_DOWN ? 2u : key == SDLK_LEFT ? 4u : key == SDLK_RIGHT ? 8u : 0u;
}
static BtpAction held_action(unsigned held)
{
    int x = !!(held & 8u) - !!(held & 4u), y = !!(held & 2u) - !!(held & 1u);
    if (x < 0) return y < 0 ? BTP_UP_LEFT : y > 0 ? BTP_DOWN_LEFT : BTP_LEFT;
    if (x > 0) return y < 0 ? BTP_UP_RIGHT : y > 0 ? BTP_DOWN_RIGHT : BTP_RIGHT;
    return y < 0 ? BTP_UP : y > 0 ? BTP_DOWN : BTP_IDLE;
}
static BtpAction key_action(SDL_Keycode key, int moving)
{
    if (key >= SDLK_0 && key <= SDLK_9) return (BtpAction)(BTP_DIGIT_0+key-SDLK_0);
    if (moving) switch (key) {
        case SDLK_HOME: case SDLK_KP_7: return BTP_UP_LEFT;
        case SDLK_PAGEUP: case SDLK_KP_9: return BTP_UP_RIGHT;
        case SDLK_END: case SDLK_KP_1: return BTP_DOWN_LEFT;
        case SDLK_PAGEDOWN: case SDLK_KP_3: return BTP_DOWN_RIGHT;
        case SDLK_KP_8: return BTP_UP;
        case SDLK_KP_2: return BTP_DOWN;
        case SDLK_KP_4: return BTP_LEFT;
        case SDLK_KP_6: return BTP_RIGHT;
        default: break;
    }
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
static int startup(SDL_Window *window,SDL_Renderer *renderer,SDL_Texture *texture,
    uint32_t *frame,BtpOptions *o,BtpContent *content,unsigned *credits,SDL_Keycode *accepted)
{
    unsigned selected=0,cheat=0;BtpError error={0};
    SDL_SetWindowTitle(window,"BtechPort - Select game edition");
    for (;;) {
        btp_startup_screen(content->resources,selected,error.text,frame);
        if (SDL_UpdateTexture(texture,NULL,frame,320*(int)sizeof *frame) ||
            SDL_RenderClear(renderer) || SDL_RenderCopy(renderer,texture,NULL,NULL)) return -1;
        SDL_RenderPresent(renderer);
        SDL_Event event;
        if (!SDL_WaitEventTimeout(&event,32)) continue;
        if (event.type==SDL_QUIT) return 0;
        if (event.type==SDL_KEYUP && (event.key.keysym.sym==SDLK_LSHIFT || event.key.keysym.sym==SDLK_RSHIFT)) cheat=0;
        if (event.type!=SDL_KEYDOWN || event.key.repeat) continue;
        SDL_Keycode key=navigation_key(event.key.keysym.sym,event.key.keysym.mod);
        if (key==SDLK_ESCAPE && (event.key.keysym.mod&KMOD_CTRL) && (event.key.keysym.mod&KMOD_SHIFT)) return 0;
        if ((event.key.keysym.mod&KMOD_SHIFT) && (key==SDLK_k || key==SDLK_y || key==SDLK_r)) {
            const SDL_Keycode sequence[]={SDLK_k,SDLK_y,SDLK_r};
            cheat=key==sequence[cheat] ? cheat+1u : key==SDLK_k ? 1u : 0u;
            if (cheat==3) { cheat=0;if (*credits<1000) ++*credits; }
            continue;
        }
        cheat=0;
        if (key==SDLK_UP || key==SDLK_DOWN || key==SDLK_LEFT || key==SDLK_RIGHT) selected^=1u;
        else if (key==SDLK_ESCAPE || key==SDLK_BACKSPACE) selected=0;
        else if (key==SDLK_1 || key==SDLK_KP_1 || key==SDLK_2 || key==SDLK_KP_2 ||
            key==SDLK_RETURN || key==SDLK_KP_ENTER || key==SDLK_SPACE) {
            if (key==SDLK_1 || key==SDLK_KP_1) selected=0;
            if (key==SDLK_2 || key==SDLK_KP_2) selected=1;
            BtpContentProfile profile=selected ? BTP_CONTENT_UPDATED : BTP_CONTENT_ORIGINAL_DOS_103;
            if (!btp_content_select(content,profile,o->roster,&error)) { fprintf(stderr,"%s\n",error.text);continue; }
            o->edition=profile;*accepted=key;
            SDL_SetWindowTitle(window,selected ? "BtechPort - Updated BTECH CHI" : "BtechPort - Original BTECH CHI");
            return 1;
        }
    }
}
int main(int argc, char **argv)
{
    BtpOptions o;
    int parsed = btp_options(argc, argv, &o);
    if (parsed <= 0) return parsed == -1 ? 0 : 1;
    BtpContent content = {0};
    BtpBldTrace native_trace={0};
    uint32_t *frame = malloc(BTP_PIXELS * sizeof *frame);
    BtpError error;
    int result = 1;
    if (!frame) return 1;
    if (!btp_cli_load_content(&o, &content, &error)) {
        fprintf(stderr,"%s\n",error.text);
        if (!o.project) fputs("Run ./scripts/build.sh to prepare the resource caches.\n",stderr);
        goto done;
    }
    BtpResources *r = content.resources;
    if (o.headless) { result = btp_run_headless(&o, r); goto done; }
    if (o.tiles_output || o.sprites_output) { fputs("Asset export requires --headless\n", stderr); goto done; }
    BtpState state;
    if (!btp_bld_trace_open(&native_trace,&o,r,&error)) { fprintf(stderr,"%s\n",error.text);goto done; }
    btp_bld_trace_bind(&native_trace,&state);btp_initial_state(&o,&state,r);
    if (o.load && !btp_save_load(o.load,&state,r,&error)) { fprintf(stderr,"%s\n",error.text); goto done; }
    if (o.replay && o.smoke < 5 && !btp_replay(o.replay, &state, r, o.trace,o.save_file)) goto done;
    if (!state.event.enabled && !o.play_map && !o.replay && !o.load && !o.smoke && !o.sprite_preview && !o.world_overview && !o.conversation_checkpoint && !o.shop_talk_checkpoint && !o.title_preview) state.mode=BTP_LOGO;
    SDL_SetMainReady();
    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_EVENTS | SDL_INIT_TIMER)) {
        fprintf(stderr, "SDL: %s\n", SDL_GetError()); goto done;
    }
    SDL_SetHint(SDL_HINT_RENDER_SCALE_QUALITY, "0");
    SDL_Window *window = SDL_CreateWindow("BtechPort - Crescent Hawk's Inception", SDL_WINDOWPOS_CENTERED,
        SDL_WINDOWPOS_CENTERED, 960, 600, SDL_WINDOW_RESIZABLE);
    SDL_Renderer *renderer = window ? SDL_CreateRenderer(window, -1, SDL_RENDERER_SOFTWARE) : NULL;
    SDL_Texture *texture = renderer ? SDL_CreateTexture(renderer, SDL_PIXELFORMAT_ARGB8888,
        SDL_TEXTUREACCESS_STREAMING, 320, 200) : NULL;
    FILE *record = NULL;
    FILE *arrival = NULL;
    SDL_AudioDeviceID audio=0;
    int play=1;unsigned startup_credits=0;SDL_Keycode startup_key=0;
    if (!texture || SDL_RenderSetLogicalSize(renderer, 320, 200)) goto sdl_done;
    /* Explicit checkpoints/replays retain their old entry points. An ordinary
       launch chooses its content before either logo or a single audio tick. */
    if (!o.edition && !o.project && !o.load && !o.replay && !o.smoke && !o.sprite_preview && !o.world_overview &&
        !o.conversation_checkpoint && !o.shop_talk_checkpoint && !o.title_preview && !o.intro_preview) {
        play=startup(window,renderer,texture,frame,&o,&content,&startup_credits,&startup_key);
        if (play<0) goto sdl_done;
        /* Content was chosen after the provisional Original state. Apply
           fresh-campaign defaults before the logo; setup credits follow. */
        if (play) { btp_initial_state(&o,&state,r);state.mode=BTP_LOGO; }
    }
    const char *edition_title=r->project ? r->project->title : r->roster.count ? "BtechPort - Updated BTECH CHI" : "BtechPort - Original BTECH CHI";
    if (play) SDL_SetWindowTitle(window,edition_title);
    if (play && !o.mute && !SDL_InitSubSystem(SDL_INIT_AUDIO)) {
        SDL_AudioSpec spec={.freq=BTP_AUDIO_RATE,.format=AUDIO_S16SYS,.channels=1,.samples=512};
        audio=SDL_OpenAudioDevice(NULL,0,&spec,NULL,0);if (audio) SDL_PauseAudioDevice(audio,0);
    }
    if (o.record) { record = fopen(o.record, "w"); if (!record) goto sdl_done; }
    for (unsigned i=0;play && i<startup_credits;++i) {
        btp_game_tick(&state,r,BTP_CREDIT_10000);
        if (record && fprintf(record,"credit-10000\n")<0) goto sdl_done;
    }
    if (o.smoke >= 5) { arrival = fopen(o.replay,"r"); if (!arrival) goto sdl_done; }
    BtpAction queue[256]; unsigned read = 0, write = 0;
    unsigned held = 0, last_arrow_write = 0, cheat_step=0;
    uint64_t last = SDL_GetTicks64(), accumulator = 0;
    unsigned smoke_ticks = 0;
    uint64_t audio_samples=0,audio_nonzero=0;unsigned audio_peak_bytes=0;
    unsigned smoke_sent = 0, tail_sent = 0;
    int arrival_done = 0;
    int running = play, io_failed = 0;
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
            if (++smoke_sent > 131072) { fputs("Replay smoke exceeded input bound\n",stderr); io_failed = 1; break; }
            if (a != BTP_IDLE) {
                static const SDL_Keycode codes[] = {0,SDLK_UP,SDLK_DOWN,SDLK_LEFT,SDLK_RIGHT,SDLK_RETURN,SDLK_BACKSPACE,
                    SDLK_0,SDLK_1,SDLK_2,SDLK_3,SDLK_4,SDLK_5,SDLK_6,SDLK_7,SDLK_8,SDLK_9,SDLK_ESCAPE,
                    SDLK_HOME,SDLK_PAGEUP,SDLK_END,SDLK_PAGEDOWN,SDLK_SPACE};
                if (a==BTP_CREDIT_10000) {
                    const SDL_Keycode sequence[]={SDLK_k,SDLK_y,SDLK_r};
                    for (unsigned i=0;i<3;++i) {
                        SDL_Event injected={.type=SDL_KEYDOWN};injected.key.keysym.sym=sequence[i];injected.key.keysym.mod=KMOD_SHIFT;
                        if (SDL_PushEvent(&injected)!=1) { io_failed=1;break; }
                    }
                } else {
                    SDL_Event injected = {.type=SDL_KEYDOWN}; injected.key.keysym.sym = codes[a];
                    if (SDL_PushEvent(&injected) != 1) { io_failed = 1; break; }
                }
            }
        }
        SDL_Event event;
        while (SDL_PollEvent(&event)) {
            if (event.type == SDL_QUIT) running = 0;
            if (event.type == SDL_KEYUP) {
                if (navigation_key(event.key.keysym.sym,event.key.keysym.mod)==startup_key) startup_key=0;
                held &= ~arrow_bit(navigation_key(event.key.keysym.sym,event.key.keysym.mod));
                if (event.key.keysym.sym==SDLK_LSHIFT || event.key.keysym.sym==SDLK_RSHIFT) cheat_step=0;
            }
            if ((event.type == SDL_WINDOWEVENT && event.window.event == SDL_WINDOWEVENT_FOCUS_LOST) ||
                !movement_mode(&state)) held = 0;
            if (event.type == SDL_KEYDOWN) {
                SDL_Keycode key = navigation_key(event.key.keysym.sym,event.key.keysym.mod);
                /* Holding the setup confirmation must not also dismiss the
                   first logo through keyboard auto-repeat. */
                if (event.key.repeat && key==startup_key) continue;
                if (key == SDLK_ESCAPE && (event.key.keysym.mod&KMOD_CTRL) && (event.key.keysym.mod&KMOD_SHIFT)) running = 0;
                else if ((state.mode==BTP_ENDING || (state.mode==BTP_BUILDING && state.campaign.building==25 &&
                    state.script.status==BTP_SCRIPT_WAIT)) && key!=SDLK_LSHIFT && key!=SDLK_RSHIFT &&
                    key!=SDLK_LCTRL && key!=SDLK_RCTRL && key!=SDLK_LALT && key!=SDLK_RALT) {
                    /* WINSCENE says any key. Letters and function keys must
                       reach its wait instead of the normal map shortcuts. */
                    if (write-read<256) queue[write++%256]=BTP_ACCEPT;
                    else { io_failed=1;running=0; }
                }
                else if ((event.key.keysym.mod&KMOD_SHIFT) && (key==SDLK_k || key==SDLK_y || key==SDLK_r) && !event.key.repeat) {
                    const SDL_Keycode sequence[]={SDLK_k,SDLK_y,SDLK_r};
                    cheat_step=key==sequence[cheat_step] ? cheat_step+1u : key==SDLK_k ? 1u : 0u;
                    if (cheat_step==3) {
                        cheat_step=0;
                        if (write-read==256) { io_failed=1;running=0; }
                        else queue[write++%256]=BTP_CREDIT_10000;
                    }
                }
                else if (o.sprite_preview) continue;
                else if (key == SDLK_F3 && !event.key.repeat) o.debug = !o.debug;
                else if (key == SDLK_F4 && !event.key.repeat) o.world_overview = !o.world_overview;
                else if ((key == SDLK_F5 || key == SDLK_F9) && !event.key.repeat) {
                    int saving = key == SDLK_F5;
                    int ok;
                    if (!saving && record) {
                        fputs("Loading while recording is unsupported; start a new log after loading.\n",stderr);
                        ok = 0;
                    } else {
                        char slot_path[4096];
                        ok=btp_save_edition_slot_path(o.save_file,state.menu.slot,r,slot_path,sizeof slot_path,&error);
                        if (ok) ok = saving ? btp_save_write(slot_path,&state,r,&error) :
                            btp_save_load(slot_path,&state,r,&error);
                        if (!ok) fprintf(stderr,"%s\n",error.text);
                    }
                    if (ok && !saving) {
                        read = write = held = last_arrow_write = 0; accumulator = 0; last = SDL_GetTicks64();
                        if (audio) SDL_ClearQueuedAudio(audio);
                    }
                    notice = ok ? (saving ? "Saved" : "Loaded") : (saving ? "Save failed" : "Load failed");
                    notice_until = SDL_GetTicks64()+3000;
                    SDL_SetWindowTitle(window,notice);
                }
                else if (key == SDLK_r && !event.key.repeat) {
                    if (record) { fputs("Restart while recording is unsupported; start a new log.\n", stderr); }
                    else { btp_initial_state(&o,&state,r); read = write = held = last_arrow_write = 0; }
                } else {
                    /* Resolve Space when its queued input is consumed. Several
                       key events can arrive before exploration enters a popup. */
                    if (key!=SDLK_LSHIFT && key!=SDLK_RSHIFT) cheat_step=0;
                    BtpAction a=key==SDLK_SPACE ? BTP_OPEN_MENU : key==SDLK_ESCAPE && !amount_editor(&state) ? BTP_CANCEL : key_action(key,movement_mode(&state));
                    /* Real arrow chords use held keys. Scripted smoke events
                       have no physical scancode and remain individual actions. */
                    unsigned bit = arrow_bit(key);
                    int physical_arrow = bit && movement_mode(&state) && event.key.keysym.scancode != SDL_SCANCODE_UNKNOWN;
                    BtpAction previous = held_action(held);
                    if (physical_arrow) { held |= bit; a = held_action(held); }
                    if (a != BTP_IDLE) {
                        /* Two perpendicular presses before a fixed step are
                           one diagonal, rather than an extra cardinal step. */
                        if (physical_arrow && !event.key.repeat && a >= BTP_UP_LEFT &&
                            previous >= BTP_UP && previous <= BTP_RIGHT && read != write &&
                            last_arrow_write == write && queue[(write-1u)%256] == previous)
                            queue[(write-1u)%256] = a;
                        else if (write - read == 256) { fputs("Input queue full\n", stderr); io_failed = 1; running = 0; }
                        else { queue[write++ % 256] = a; last_arrow_write = physical_arrow ? write : 0; }
                    }
                }
            }
        }
        uint64_t now = SDL_GetTicks64(); accumulator += now - last; last = now;
        if (o.smoke_fast) accumulator = 32;
        /* 32ms fixed simulation steps. Platform repeat/pacing remains approximate. */
        while (accumulator >= 32 && running) {
            /* Hold the simulation when the device is behind. Replaying all
               elapsed wall time would queue seconds of sound after a stall. */
            if (audio && state.menu.sound && !o.smoke_fast && SDL_GetQueuedAudioSize(audio)>2u*BTP_AUDIO_TICK_SAMPLES*sizeof(int16_t)) {
                accumulator=0;break;
            }
            accumulator -= 32;
            BtpAction a = read != write ? queue[read++ % 256] : BTP_IDLE;
            if (a==BTP_OPEN_MENU && state.mode==BTP_ACTIONS) a=BTP_ACCEPT;
            if (a==BTP_OPEN_MENU && (state.combat.phase==BTP_COMBAT_CONTROL || state.combat.phase==BTP_COMBAT_MESSAGES ||
                state.combat.phase==BTP_COMBAT_GRAPHICS || state.combat.phase==BTP_COMBAT_NOTICE || state.combat.phase==BTP_COMBAT_STORY ||
                state.combat.phase==BTP_COMBAT_OFFER || state.combat.phase==BTP_COMBAT_AVOID)) a=BTP_ACCEPT;
            if (a==BTP_OPEN_MENU && state.mode!=BTP_EXPLORE && state.mode!=BTP_CACHE && !state.combat.phase && state.mode!=BTP_ACTIONS) a=amount_editor(&state) ? BTP_IDLE : BTP_ACCEPT;
            if (o.sprite_preview) ++state.tick;
            else {
                int16_t pcm[BTP_AUDIO_TICK_SAMPLES];
                btp_game_tick_audio(&state,r,a,audio && !o.smoke_fast ? pcm : NULL);
                if (audio && state.menu.sound && !o.smoke_fast && SDL_QueueAudio(audio,pcm,sizeof pcm)) { io_failed=1;running=0; }
                if (audio && state.menu.sound && !o.smoke_fast) {
                    unsigned queued=SDL_GetQueuedAudioSize(audio);if (queued>audio_peak_bytes) audio_peak_bytes=queued;
                    audio_samples+=BTP_AUDIO_TICK_SAMPLES;
                    for (unsigned n=0;n<BTP_AUDIO_TICK_SAMPLES;++n) audio_nonzero+=pcm[n]!=0;
                }
                if (state.menu.io) {
                    unsigned request=state.menu.io;
                    int ok=btp_save_menu(&state,r,o.save_file,1,&error);
                    if (!ok) fprintf(stderr,"%s\n",error.text);
                    if (ok && request==BTP_MENU_IO_LOAD) { read=write=held=last_arrow_write=0;accumulator=0;if (audio) SDL_ClearQueuedAudio(audio); }
                }
                if (audio && !state.menu.sound) SDL_ClearQueuedAudio(audio);
                if (state.menu.quit) running=0;
            }
            if (!movement_mode(&state)) held = 0;
            if (record && fprintf(record, "%s\n", btp_action_name(a)) < 0) { io_failed = 1; running = 0; }
            if (o.smoke) {
                ++smoke_ticks;
                if (o.smoke < 5 && smoke_ticks >= (o.smoke == 1 ? 8u : 24u)) running = 0;
            }
            if (o.smoke >= 5) break; /* Inject exactly one input for each fixed step. */
        }
        if (o.sprite_preview) btp_sprite_preview(r,state.tick,frame);
        else if (o.world_overview) btp_world_preview(r,&state,frame);
        else btp_render(r, &state, o.debug, frame);
        if (SDL_UpdateTexture(texture, NULL, frame, 320 * (int)sizeof *frame) ||
            SDL_RenderClear(renderer) || SDL_RenderCopy(renderer, texture, NULL, NULL)) {
            io_failed = 1; running = 0;
        }
        SDL_RenderPresent(renderer);
        if (notice && SDL_GetTicks64() >= notice_until) {
            notice = NULL; SDL_SetWindowTitle(window,edition_title);
        }
        if (o.debug && !notice) {
            char title[200];
            snprintf(title, sizeof title, "BtechPort | %s | half=(%u,%u) | PC=%04x op=%02x | tick=%u",
                btp_mode_name(state.mode), state.x_half, state.y_half, state.script.pc,
                state.script.last_opcode, state.tick);
            SDL_SetWindowTitle(window, title);
        }
        if (!o.smoke_fast) SDL_Delay(2);
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
    if (o.audio_report) {
        FILE *report=fopen(o.audio_report,"w");
        if (!report) result=1;
        else {
            if (fprintf(report,"{\"opened\":%u,\"rate\":%u,\"samples\":%llu,\"nonzero\":%llu,\"peak_queued_bytes\":%u}\n",audio!=0,BTP_AUDIO_RATE,
                (unsigned long long)audio_samples,(unsigned long long)audio_nonzero,audio_peak_bytes)<0) result=1;
            if (fclose(report)) result=1;
        }
    }
    if (o.smoke == 5 && (state.mode != BTP_EXPLORE || state.x_half != 69 || state.y_half != 21 ||
        state.conversation_checkpoint || state.npc.enabled != 2 || state.npc.fault || state.story_flags[13] != 1)) {
        fputs("Native arrival smoke input/state mismatch\n",stderr); result = 1;
    }
    if (o.smoke == 6 && (state.mode != BTP_EXPLORE || state.x_half != 32 || state.y_half != 44 ||
        state.conversation_checkpoint || state.npc.enabled != 2 || state.npc.fault ||
        state.weapon != 1 || state.armor != 1 || state.armor_points != 25)) {
        fputs("Native shops smoke input/state mismatch\n",stderr); result = 1;
    }
    if (!result && play && o.save && !btp_save_write(o.save,&state,r,&error)) {
        fprintf(stderr,"%s\n",error.text); result = 1;
    }
    if (!result && o.export_original && !btp_original_write(o.export_original,&state,&error)) {
        fprintf(stderr,"%s\n",error.text);result=1;
    }
sdl_done:
    if (audio) SDL_CloseAudioDevice(audio);
    if (arrival && fclose(arrival)) result = 1;
    if (record && fclose(record)) result = 1;
    if (result) fprintf(stderr, "Native frontend failed: %s\n", SDL_GetError());
    if (texture) SDL_DestroyTexture(texture);
    if (renderer) SDL_DestroyRenderer(renderer);
    if (window) SDL_DestroyWindow(window);
    SDL_Quit();
done:
    if (!btp_bld_trace_close(&native_trace)) result=1;
    free(frame); btp_content_close(&content);
    return result;
}
