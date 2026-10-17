#include "frontend/cli.h"
#include "data/project.h"
#include "core/npc.h"
#include "core/training.h"
#include "core/world.h"
#include "core/audio.h"
#include "core/combat.h"
#include "core/events.h"
#include "data/save.h"
#include "data/sprites.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int btp_options(int argc, char **argv, BtpOptions *o)
{
    *o = (BtpOptions){.data = "Original DOS",.dialogue_data="work/talk-data.bin",.combat_data="work/combat-data.bin",.world_data="work/world-data.bin",
        .save_file="work/player-save.btp",.roster="content/updated/roster.json"};
    for (int i = 1; i < argc; ++i) {
        const char *arg = argv[i];
        if (!strcmp(arg, "--help")) {
            puts("BtechPort: training, world travel, party and mech services\n"
                 "  --data DIRECTORY     original resource directory (default: Original DOS)\n"
                 "  --dialogue-data FILE local EXE text cache (default: work/talk-data.bin)\n"
                 "  --combat-data FILE   local EXE combat cache (default: work/combat-data.bin)\n"
                 "  --world-data FILE    original numeric world-generation inputs\n"
                 "  --world-overview     show generated terrain around the party\n"
                 "  --conversation-checkpoint  isolated controlled Talk handler test\n"
                 "  --shop-talk-checkpoint armor|weapon  controlled two-NPC shop handler test\n"
                 "  --headless           run without SDL/display/audio\n"
                 "  --replay FILE        logical actions: arrows/idle/accept/cancel/0..9/clear\n"
                 "  --trace              print canonical JSON state after each replay action\n"
                 "  --event-trace FILE   headless JSONL command entries, flags and credits\n"
                 "  --frame FILE         write final 320x200 RGB PPM\n"
                 "  --sprite-preview     show original mech/human walking frames (diagnostic only)\n"
                 "  --title-preview      original title screen and PC speaker music\n"
                 "  --intro-preview      logos, title music and played-before question\n"
                 "  --edition NAME       original or updated; bypass the startup selector\n"
                 "  --roster FILE        updated edition's external mech definitions\n"
                 "  --project DIRECTORY authored project; independent projects need no DOS files\n"
                 "  --play-here MAP X Y  new authored playtest at half-tile coordinates\n"
                 "  --mute               disable the native audio device\n"
                 "  --export-sprites FILE write original sprite crops for verification\n"
                 "  --export-tiles FILE  write 64000 decoded tile pixel indices\n"
                 "  --record FILE        native logical input log for replay (includes idle ticks)\n"
                 "  --save-file FILE     slot for F5 save/F9 load (default: work/player-save.btp)\n"
                 "  --load FILE          restore a native or original GAME save\n"
                 "  --save FILE          write an internal save on successful exit\n"
                 "  --export-original FILE export an imported GAME save after returning outdoors\n"
                 "  --audio-report FILE  native diagnostic: audio device and PCM counts\n"
                 "  --debug              collision overlay and diagnostics (F3 toggles)\n"
                 "  --smoke              bounded native SDL event/presentation check\n"
                 "  --smoke-citadel      bounded native Citadel entry/dialogue/exit check\n"
                 "  --smoke-katrina      bounded native Katrina/repeat/exit/re-entry check\n"
                 "  --smoke-talk         bounded controlled NPC conversation check\n"
                 "  --smoke-arrival      feed --replay through native SDL events, then return/exit\n"
                 "  --smoke-shops        feed the two-shop --replay through SDL events\n"
                 "  --smoke-replay       feed any bounded --replay through SDL events\n"
                 "  --smoke-fast         accelerate native replay tests; logical ticks stay 32ms\n"
                 "Native controls: arrows move/select, Enter/Space confirms/continues,\n"
                 "Bank/ammo amounts: digits type, Backspace erases, Esc clears; Enter submits.\n"
                 "Space opens game settings, inspection and six save/load slots.\n"
                 "F4 toggles the area map, F5 saves, F9 loads. Backspace/Esc declines, R restarts, F3 debug.\n"
                 "Ctrl+Shift+Esc quits. Hold Shift and press K, Y, R for 10,000 credits.");
            return -1;
        }
        if (!strcmp(arg, "--headless")) o->headless = 1;
        else if (!strcmp(arg, "--sprite-preview")) o->sprite_preview = 1;
        else if (!strcmp(arg, "--world-overview")) o->world_overview = 1;
        else if (!strcmp(arg,"--title-preview")) o->title_preview=1;
        else if (!strcmp(arg,"--intro-preview")) o->intro_preview=1;
        else if (!strcmp(arg,"--mute")) o->mute=1;
        else if (!strcmp(arg,"--play-here")) {
            if (i+3>=argc) { fputs("--play-here needs MAP X Y\n",stderr);return 0; }
            o->play_map=argv[++i];char *end;unsigned long x=strtoul(argv[++i],&end,10);
            if (!*argv[i] || *end || x>127) { fputs("Invalid playtest X\n",stderr);return 0; }
            unsigned long y=strtoul(argv[++i],&end,10);
            if (!*argv[i] || *end || y>127) { fputs("Invalid playtest Y\n",stderr);return 0; }
            o->play_x=(unsigned)x;o->play_y=(unsigned)y;
        }
        else if (!strcmp(arg,"--edition")) {
            if (++i==argc || (strcmp(argv[i],"original") && strcmp(argv[i],"updated"))) {
                fputs("Edition must be original or updated\n",stderr); return 0;
            }
            o->edition=!strcmp(argv[i],"original") ? BTP_CONTENT_ORIGINAL_DOS_103 : BTP_CONTENT_UPDATED;
        }
        else if (!strcmp(arg, "--debug")) o->debug = 1;
        else if (!strcmp(arg, "--trace")) o->trace = 1;
        else if (!strcmp(arg,"--event-trace")) { if (++i==argc) return 0;o->event_trace=argv[i]; }
        else if (!strcmp(arg, "--smoke")) o->smoke = 1;
        else if (!strcmp(arg, "--smoke-citadel")) o->smoke = 2;
        else if (!strcmp(arg, "--smoke-katrina")) o->smoke = 3;
        else if (!strcmp(arg, "--smoke-talk")) { o->smoke = 4; o->conversation_checkpoint = 1; }
        else if (!strcmp(arg, "--smoke-arrival")) o->smoke = 5;
        else if (!strcmp(arg, "--smoke-shops")) o->smoke = 6;
        else if (!strcmp(arg, "--smoke-replay")) o->smoke = 7;
        else if (!strcmp(arg, "--smoke-fast")) o->smoke_fast = 1;
        else if (!strcmp(arg,"--shop-talk-checkpoint")) {
            if (++i == argc || (strcmp(argv[i],"armor") && strcmp(argv[i],"weapon"))) {
                fputs("Shop Talk checkpoint requires armor or weapon\n",stderr); return 0;
            }
            o->shop_talk_checkpoint = !strcmp(argv[i],"armor") ? 4 : 3;
        }
        else if (!strcmp(arg, "--conversation-checkpoint")) o->conversation_checkpoint = 1;
        else {
            const char **value = NULL;
            if (!strcmp(arg, "--data")) value = &o->data;
            if (!strcmp(arg, "--dialogue-data")) value = &o->dialogue_data;
            if (!strcmp(arg, "--combat-data")) value = &o->combat_data;
            if (!strcmp(arg, "--world-data")) value = &o->world_data;
            if (!strcmp(arg, "--replay")) value = &o->replay;
            if (!strcmp(arg, "--frame")) value = &o->frame;
            if (!strcmp(arg, "--record")) value = &o->record;
            if (!strcmp(arg, "--export-sprites")) value = &o->sprites_output;
            if (!strcmp(arg, "--export-tiles")) value = &o->tiles_output;
            if (!strcmp(arg, "--save-file")) value = &o->save_file;
            if (!strcmp(arg, "--roster")) value = &o->roster;
            if (!strcmp(arg, "--project")) value = &o->project;
            if (!strcmp(arg,"--data")) o->explicit_dependencies|=1;
            if (!strcmp(arg,"--dialogue-data")) o->explicit_dependencies|=2;
            if (!strcmp(arg,"--combat-data")) o->explicit_dependencies|=4;
            if (!strcmp(arg,"--world-data")) o->explicit_dependencies|=8;
            if (!strcmp(arg, "--load")) value = &o->load;
            if (!strcmp(arg, "--save")) value = &o->save;
            if (!strcmp(arg,"--audio-report")) value=&o->audio_report;
            if (!strcmp(arg,"--export-original")) value=&o->export_original;
            if (!value || i + 1 == argc) { fprintf(stderr, "Unknown/incomplete option: %s\n", arg); return 0; }
            *value = argv[++i];
        }
    }
    if (o->sprite_preview && (o->smoke || o->replay || o->load || o->save || o->record || o->conversation_checkpoint || o->shop_talk_checkpoint)) {
        fputs("Sprite preview cannot combine with gameplay, recording or save options\n",stderr); return 0;
    }
    if (o->conversation_checkpoint && o->shop_talk_checkpoint) {
        fputs("Choose one explicit Talk checkpoint\n",stderr); return 0;
    }
    if (o->load && (o->conversation_checkpoint || o->shop_talk_checkpoint)) {
        fputs("Loading a save cannot also inject a Talk checkpoint\n",stderr); return 0;
    }
    if (o->smoke >= 5 && (!o->replay || (o->smoke < 7 && (o->conversation_checkpoint || o->shop_talk_checkpoint)))) {
        fputs("Native route smoke requires --replay and the normal initial state\n",stderr); return 0;
    }
    if (o->smoke_fast && (o->smoke < 5 || !o->replay || o->headless)) {
        fputs("Accelerated smoke requires a native replay smoke mode\n",stderr); return 0;
    }
    if (o->play_map && (!o->project || o->load)) { fputs("Play here requires a project and a fresh campaign\n",stderr);return 0; }
    return 1;
}

int btp_cli_load_content(const BtpOptions *o, BtpContent *content, BtpError *error)
{
    /* Both players use the same original profile and existing CLI defaults.
       Package selection can later enter here without changing game startup. */
    const BtpOriginalContentPaths paths = {
        .directory = o->data, .dialogue = o->dialogue_data,
        .combat = o->combat_data, .world = o->world_data
    };
    if (o->project) {
        if (o->edition || o->export_original) {
            snprintf(error->text,sizeof error->text,"Do not combine --project with --edition or --export-original");
            return 0;
        }
        /* Validate package identity first, so independent games can run with
           every original input absent. CHI packages retain explicit paths. */
        if (!btp_content_load_project(content,o->project,o->explicit_dependencies==15 ? &paths : NULL,error)) return 0;
        if (!content->resources->project->independent.loaded && o->explicit_dependencies!=15) {
            btp_content_close(content);snprintf(error->text,sizeof error->text,"CHI project needs explicit --data, --dialogue-data, --combat-data, --world-data");return 0;
        }
        if (content->resources->project->independent.loaded &&
            (o->intro_preview || o->title_preview || o->sprite_preview || o->tiles_output || o->sprites_output || o->conversation_checkpoint || o->shop_talk_checkpoint)) {
            btp_content_close(content);snprintf(error->text,sizeof error->text,"Original-resource diagnostics are unavailable in an independent game");return 0;
        }
        if (o->play_map) {
            const BtpAdventure *a=&content->resources->project->adventure;unsigned at=0;
            while (at<a->map_count && strcmp(a->maps[at].id,o->play_map)) ++at;
            /* World sector edges are continuous terrain. The complete-party
               probe below checks the composed world, including both sides. */
            if (at==a->map_count || (!a->maps[at].world && !btp_scene_stand(&a->maps[at],(int)o->play_x,(int)o->play_y,0)) ||
                o->play_x>=2u*a->maps[at].visual.width || o->play_y>=2u*a->maps[at].visual.height) {
                btp_content_close(content);snprintf(error->text,sizeof error->text,"Unknown or blocked Play here destination");return 0;
            }
            BtpState *probe=calloc(1,sizeof *probe);
            if (!probe) { btp_content_close(content);snprintf(error->text,sizeof error->text,"Playtest allocation failed");return 0; }
            btp_start(probe);probe->project=1;
            int fits=btp_events_preview(probe,content->resources,o->play_map,o->play_x,o->play_y);free(probe);
            if (!fits) { btp_content_close(content);snprintf(error->text,sizeof error->text,"The complete initial party cannot fit at this Play here destination");return 0; }
        }
        return 1;
    }
    if (!btp_content_load_original(content, &paths, error)) return 0;
    BtpContentProfile profile=o->edition;
    /* A supplied save identifies its edition before any state is decoded.
       Explicit Updated plus an original save makes a separate campaign copy. */
    if (profile==BTP_CONTENT_NONE && o->load && btp_save_is_updated(o->load)) profile=BTP_CONTENT_UPDATED;
    if (profile==BTP_CONTENT_UPDATED && !btp_content_select(content,profile,o->roster,error)) {
        btp_content_close(content);return 0;
    }
    if (profile==BTP_CONTENT_UPDATED && o->export_original) {
        snprintf(error->text,sizeof error->text,"Updated games cannot be exported as original GAME saves");
        btp_content_close(content);return 0;
    }
    return 1;
}

void btp_initial_state(const BtpOptions *o, BtpState *s, const BtpResources *r)
{
    if (o->shop_talk_checkpoint) btp_start_shop_conversation_checkpoint(s,r,(unsigned)o->shop_talk_checkpoint);
    else if (o->conversation_checkpoint) btp_start_conversation_checkpoint(s);
    else btp_start(s);
    s->project=(uint8_t)(r->project!=NULL);
    btp_npc_init(s,&r->map);
    /* Fresh Updated campaigns opt in. Loading a save below replaces this
       state, preserving the saved policy (including old saves' Legacy). */
    if (r->roster.count && r->combat_profile.fingerprint) (void)btp_set_combat_profile(s,r,1);
    if (o->play_map) (void)btp_events_preview(s,r,o->play_map,o->play_x,o->play_y);
    else btp_events_start(s,r);
    if (o->title_preview) btp_audio_start(s);
    if (o->intro_preview) s->mode=BTP_LOGO;
}

void btp_print_state(const BtpState *s, const BtpResources *r)
{
    uint32_t digest = 0;
    uint8_t body[BTP_BLD_MAX + 1];
    size_t length = 0;
    if (btp_game_text(s, r, body, sizeof body, &length)) {
        digest = length ? UINT32_C(2166136261) : 0;
        for (size_t i = 0; i < length; ++i)
            digest = (digest ^ body[i]) * UINT32_C(16777619);
    }
    printf("{\"map\":%u,\"mode\":\"%s\",\"x_half\":%u,\"y_half\":%u,"
           "\"tile\":[%u,%u],\"gate\":%u,\"tick\":%u,\"blocked\":%u,"
           "\"script_pc\":%u,\"script_status\":%u,\"script_opcode\":%u,\"script_error\":%u,"
           "\"fault_pc\":%u,\"menu_selected\":%u,\"text_offset\":%u,\"text_length\":%u,"
           "\"text_digest\":%u,\"story_flags\":[",
           s->map_id, btp_mode_name(s->mode), s->x_half, s->y_half, s->x_half / 2, s->y_half / 2,
           s->gate, s->tick, s->blocked, s->script.pc, s->script.status, s->script.last_opcode,
           s->script.error, s->script.fault_pc, s->bank.phase == BTP_BANK_MENU ? s->script.choices[7] : s->script.selected, s->script.text_offset,
           (unsigned)length, digest);
    for (unsigned i = 0; i < BTP_STORY_PREFIX; ++i) printf("%s%u", i ? "," : "", s->story_flags[i]);
    fputs("],\"text_spans\":[", stdout);
    for (unsigned i = 0; i < s->script.text_count && i < BTP_TEXT_SPANS; ++i)
        printf("%s[%u,%u]", i ? "," : "", s->script.text[i].offset, s->script.text[i].length);
    printf("],\"talk_phase\":%u,\"talk_selected\":%u,\"talk_count\":%u,\"talk_mask\":%u,"
           "\"talk_actor\":%u,\"talk_result\":%u,\"conversation_checkpoint\":%u,\"npc_pairs\":[",
           s->talk.phase,s->talk.selected,s->talk.count,s->talk.mask,s->talk.actor,s->talk_result,
           s->conversation_checkpoint);
    for (unsigned i = 0; i < 8; ++i) printf("%s[%u,%u]",i ? "," : "",s->npc_pairs[i][0],s->npc_pairs[i][1]);
    printf("],\"npc_enabled\":%u,\"npc_phase\":%u,\"npc_clock\":%u,\"npc_fault\":%u,"
           "\"npc_rng\":[%u,%u,%u],\"npc_search\":[%u,%u],\"npc_loop_timer\":%u,\"npc_allowance_pending\":%u,\"npcs\":[",
           s->npc.enabled,s->npc.phase,s->npc.clock,s->npc.fault,s->npc.rng[0],s->npc.rng[1],
           s->npc.rng[2],s->npc.search,s->npc.bias,s->npc.loop_timer,s->npc.allowance_pending);
    for (unsigned i = 0; i < 8; ++i) printf("%s[%u,%u,%u]",i ? "," : "",
        s->npc.actor[i].x,s->npc.actor[i].y,s->npc.actor[i].direction);
    printf("],\"credits\":%u,\"allowance_cap\":%u,\"equipment\":{\"weapon\":%u,\"armor\":%u,\"armor_points\":%u},"
        "\"shop_refusal\":%u,\"menu_id\":%u,\"confirm_selected\":%u,\"menu_choices\":[",
        s->credits,s->allowance_cap,s->weapon,s->armor,s->armor_points,s->story_flags[39],
        s->script.menu_id,s->script.confirm_selected);
    for (unsigned i = 0; i < BTP_MENUS; ++i) printf("%s%u",i ? "," : "",s->script.choices[i]);
    printf("],\"investments\":[%u,%u,%u],\"bank_phase\":%u,\"bank_company\":%u,"
        "\"bank_outcome\":%u,\"bank_clamped\":%u,\"bank_available\":%u,\"bank_amount\":%u,"
        "\"bank_input\":\"%s\",\"has_accounts\":%u",
        s->investments[0],s->investments[1],s->investments[2],s->bank.phase,s->bank.company,
        s->bank.outcome,s->bank.clamped,s->bank.available,s->bank.amount,s->bank.input,s->script.has_accounts);
    printf(",\"skills\":[%u,%u,%u],\"school_phase\":%u,\"school_course\":%u,"
        "\"school_before\":%u,\"school_outcome\":%u",s->skills[0],s->skills[1],s->skills[2],
        s->school.phase,s->school.course,s->school.before,s->school.outcome);
    printf(",\"service\":{\"phase\":%u,\"action\":%u,\"mech\":%u,\"selected\":%u,\"kind\":%u,\"item\":%u,\"amount\":%u}",s->service.phase,s->service.action,s->service.mech,s->service.selected,s->service.kind,s->service.item,s->service.amount);
    printf(",\"campaign_flags\":[");for (unsigned i=0;i<64;++i) printf("%s%u",i ? "," : "",s->story_flags[i]);printf("]");
    printf(",\"people\":[");
    for (unsigned i=0;i<8;++i) {
        printf("%s[",i ? "," : "");for (unsigned j=0;j<17;++j) printf("%s%u",j ? "," : "",s->party.people[i][j]);printf("]");
    }
    printf("],\"mech_types\":[%u,%u,%u,%u]",s->party.mech_types[0],s->party.mech_types[1],s->party.mech_types[2],s->party.mech_types[3]);
    printf(",\"audio\":{\"active\":%u,\"position\":%u,\"divisor\":%u,\"effects\":%u,\"effect\":%u,\"event\":%u,\"remaining\":%u}",s->audio.active,s->audio.position,s->audio.divisor,
        s->audio.sound_count,s->audio.sounds[0],s->audio.event,s->audio.remaining);
    printf(",\"aftermath\":{\"phase\":%u,\"pilot\":%u,\"selected\":%u,\"cash\":%u,\"eject\":%u}",s->aftermath.phase,s->aftermath.pilot,s->aftermath.selected,s->aftermath.cash,s->aftermath.eject);
    printf(",\"actions_menu\":{\"phase\":%u,\"selected\":%u,\"steps\":%u,\"sound\":%u,\"speed\":%u,\"outtakes\":%u,\"slot\":%u,\"io\":%u,\"notice\":%u}",
        s->campaign.ui,s->campaign.selected,s->menu.steps,s->menu.sound,s->menu.speed,s->menu.outtakes,s->menu.slot,s->menu.io,s->menu.notice);
    printf(",\"campaign\":{\"invasion\":%u,\"owned\":%u,\"world\":[%u,%u],\"mounted\":%u,\"encounter\":%u,\"building\":%u},\"player_sprite\":%u,\"npc_sprites\":[",
        s->campaign.invasion,s->campaign.owned,s->campaign.world_x,s->campaign.world_y,s->campaign.mounted,s->campaign.encounter,s->campaign.building,
        s->mission.phase ? (s->story_flags[2] ? 146u : 0u)+s->mission.walk : 166u+s->player_walk);
    for (unsigned i = 0; i < 8; ++i) printf("%s%u",i ? "," : "",270u+s->npc_walk[i]);
    printf("],\"quiz\":{\"phase\":%u,\"selected\":%u,\"round\":%u,\"point\":%u,\"failed\":%u,\"used\":%u},"
        "\"mission\":{\"phase\":%u,\"corner\":%u,\"warned\":%u,\"elapsed\":%u,\"idle\":%u,\"terrain\":%u,"
        "\"assignment\":%u,\"rubble\":%u,\"carrying\":%u,\"rubble_target\":[%u,%u],\"rubble_tile\":%u},\"mech_skills\":[%u,%u],"
        "\"device\":%u,\"recruitment\":%u,\"animation_request\":[%u,%u],"
        "\"animation\":{\"active\":%u,\"kind\":%u,\"step\":%u,\"cycle\":%u,\"hold\":%u,\"remaining\":%u,\"fraction\":%u}",
        s->quiz.phase,s->quiz.selected,s->quiz.round,s->quiz.point,s->quiz.failed,s->quiz.used,
        s->mission.phase,s->mission.corner,s->mission.warned,s->mission.elapsed,s->mission.idle,
        s->mission.phase ? btp_mission_terrain(s,&r->map) : 0u,
        s->mission.assignment,s->mission.rubble,s->mission.assignment && s->mission.corner && s->story_flags[2] != 0,
        s->mission.assignment ? btp_rubble_x[s->mission.rubble] : 0u,
        s->mission.assignment ? btp_rubble_y[s->mission.rubble] : 0u,
        s->mission.assignment ? btp_mission_tile(s,&r->map,btp_rubble_x[s->mission.rubble],btp_rubble_y[s->mission.rubble]) : 0u,
        s->mech_skills[0],s->mech_skills[1],s->story_flags[47],s->recruitment,s->script.animation_kind,s->script.animation_flags,
        s->cutscene.active,s->cutscene.kind,s->cutscene.step,s->cutscene.cycle,s->cutscene.hold,s->cutscene.remaining,s->cutscene.refresh_fraction);
    const BtpCombatState *c=&s->combat;
    if (r->roster.count) printf(",\"combat_rules\":\"%s\",\"combat_fingerprint\":%u",
        s->combat_profile ? "enhanced" : "legacy",s->combat_fingerprint);
    uint32_t fog=UINT32_C(2166136261);for (unsigned i=0;i<sizeof s->explored;++i) fog=(fog^s->explored[i])*UINT32_C(16777619);
    printf(",\"explored_digest\":%u,\"map_center\":[%u,%u],\"intro_load\":%u",fog,s->menu.map_x,s->menu.map_y,s->menu.from_intro);
    printf(",\"cache\":{\"active\":%u,\"phase\":%u,\"terminal\":%u,\"hall\":%u,\"cards\":[%u,%u,%u],\"white\":%u,\"power\":%u,\"found\":%u,\"room\":%u}",
        s->cache.active,s->cache.phase,s->cache.terminal,s->cache.hall,s->story_flags[59],s->story_flags[60],s->story_flags[61],s->story_flags[62],s->story_flags[64],s->story_flags[65],s->story_flags[66]);
    printf(",\"yard\":{\"active\":%u,\"phase\":%u,\"timer\":%u,\"checked\":%u,\"attempts\":%u,\"selected\":%u,\"slot\":%u,\"rental\":%u,\"variant\":%u}",
        s->yard.active,s->yard.phase,s->yard.timer,s->yard.checked,s->yard.attempts,s->yard.selected,s->yard.slot,s->yard.rental,s->yard.variant);
    uint8_t encoded[BTP_STATE_BYTES];btp_state_encode(s,encoded);uint64_t state_hash=UINT64_C(14695981039346656037);
    for (unsigned i=0;i<BTP_STATE_BYTES;++i) state_hash=(state_hash^encoded[i])*UINT64_C(1099511628211);
    printf(",\"state_digest\":\"%016llx\",\"effect_stage\":%u",(unsigned long long)state_hash,s->effects.stage);
    if (s->event.enabled) {
        printf(",\"authored_event\":{\"node\":%u,\"phase\":%u,\"page\":%u,\"selected\":%u,\"map\":%u,\"planet\":%u,\"flags\":[",
            s->event.node,s->event.phase,s->event.page,s->event.selected,s->event.map,s->event.planet);
        const BtpAdventure *a=btp_adventure(r);
        for (unsigned i=0;i<a->flag_count;++i) printf("%s%u",i ? "," : "",s->event.flags[i]);
        fputs("]}",stdout);
    }
    printf(",\"combat\":{\"phase\":%u,\"selected\":%u,\"round\":%u,\"step\":%u,\"won\":%u,\"fled\":%u,\"event\":%u,\"fired\":%u,"
        "\"weapon\":%u,\"flash\":%u,\"goal\":[%u,%u,%u,%u],\"orders\":[",c->phase,c->selected,c->round,c->step,c->won,c->fled,c->last_event,c->fired,
        c->weapon_selected,c->flash,c->goal_active,c->movement,c->goal_x,c->goal_y);
    for (unsigned i=0;i<11;++i) printf("%s%u",i ? "," : "",c->orders[i]);
    printf("],\"target_choice\":%u,\"weapon_ui\":%u",c->target_selected,c->weapon_ui);
    printf(",\"count\":%u,\"target\":%u,\"kick\":%u,\"lost\":%u,\"attacker\":%u,\"shot_target\":%u,\"technician\":%u,\"apprentice\":%u,\"automatic\":%u,\"auto_run\":%u,\"paused\":%u,\"friends\":%u,\"active\":%u,\"scan\":%u,\"menu_commands\":[",
        c->count,c->target_unit,c->kick_target,c->lost,c->last_attacker,c->last_target,s->technician,s->apprentice,c->automatic,c->auto_run,c->paused,c->friends,c->active_unit,c->scan_unit);
    for (unsigned i=0;c->phase && i<btp_combat_menu_count(c);++i) printf("%s%u",i ? "," : "",btp_combat_menu_command(c,i));
    printf("],\"units\":[");
    for (unsigned i=0;i<(c->count ? c->count : 2u);++i) {
        const BtpCombatUnit *u=&c->unit[i];
        printf("%s{\"x\":%u,\"y\":%u,\"direction\":%u,\"heat\":%u,\"pool\":%u,\"cover\":%u,\"infantry\":%u,\"burning\":%u,\"record\":[",i ? "," : "",u->x,u->y,u->direction,u->heat,u->pool,u->cover,u->infantry,u->burning);
        for (unsigned j=0;j<125;++j) printf("%s%u",j ? "," : "",u->record[j]);
        fputs("]}",stdout);
    }
    printf("],\"waypoints\":[");
    if (c->goal_active) {
        printf("[%u,%u]",c->goal_x,c->goal_y);
        for (unsigned i=0;i<c->waypoint_count;++i) printf(",[%u,%u]",c->waypoint_x[i],c->waypoint_y[i]);
    }
    printf("],\"effects\":[%u,%u,%u],\"shot\":[%d,%u,%u,%u,%u]}",
        s->effects.count,s->effects.age,s->effects.pending,c->shot.needed,c->shot.hit,c->shot.location,c->shot.damage,c->shot.destroyed);
    puts("}");
}

int btp_replay(const char *path, BtpState *s, const BtpResources *r, int trace,const char *save_base)
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
        if (s->menu.io) {
            BtpError e;if (!btp_save_menu(s,r,save_base,1,&e)) fprintf(stderr,"%s\n",e.text);
        }
        if (trace) btp_print_state(s, r);
    }
    int ok = !ferror(f);
    if (fclose(f)) ok = 0;
    if (s->mode == BTP_SCRIPT_FAULT) {
        fprintf(stderr, "BLD %s at payload 0x%04x (opcode 0x%02x)\n",
            btp_script_error_name(s->script.error), s->script.fault_pc, s->script.last_opcode);
        ok = 0;
    }
    if (s->npc.fault) { fprintf(stderr,"NPC movement context/data fault %u\n",s->npc.fault); ok = 0; }
    return ok;
}

static void event_trace(void *context,const BtpState *s,const BtpResources *r,const BtpEventNode *e);
static int run_headless(const BtpOptions *o, BtpResources *r,FILE *trace)
{
    /* Loading a checkpoint replaces the bootstrap state. Do not report the
       discarded bootstrap commands as if they ran in the resumed session. */
    if (o->load) btp_events_observe(NULL,NULL);
    BtpState state; btp_initial_state(o,&state,r);
    BtpError error;
    if (o->load && !btp_save_load(o->load,&state,r,&error)) {
        fprintf(stderr,"%s\n",error.text); return 1;
    }
    if (trace) btp_events_observe(event_trace,trace);
    int result = 0;
    if (o->record || o->smoke) { fputs("--record/--smoke require the native frontend\n", stderr); return 1; }
    if (o->trace) btp_print_state(&state, r);
    if (o->replay && !btp_replay(o->replay, &state, r, o->trace,o->save_file)) {
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
    if (o->sprites_output) {
        FILE *out = fopen(o->sprites_output,"wb");
        if (!out) return 1;
        int ok = fwrite("BTSP",1,4,out) == 4;
        for (unsigned id = 0; id < BTP_SPRITE_COUNT && ok; ++id) {
            BtpSpriteRect rect;
            ok = btp_sprite_rect(id,&rect);
            if (!ok) break;
            ok = fputc((int)rect.width,out) != EOF && fputc((int)rect.height,out) != EOF;
            for (unsigned y = 0; y < rect.height && ok; ++y)
                ok = fwrite(r->sprites.pixels+(rect.y+y)*320+rect.x,1,rect.width,out) == rect.width;
        }
        if (fclose(out)) ok = 0;
        if (!ok) return 1;
    }
    if (o->frame) {
        uint32_t *frame = malloc(sizeof(*frame) * BTP_PIXELS);
        if (!frame) return 1;
        if (o->sprite_preview) btp_sprite_preview(r,state.tick,frame);
        else if (o->world_overview) btp_world_preview(r,&state,frame);
        else btp_render(r, &state, o->debug, frame);
        int ok = btp_write_ppm(o->frame, frame);
        free(frame);
        if (!ok) { fputs("Frame write failed\n", stderr); return 1; }
    }
    if (!o->trace) btp_print_state(&state, r);
    if (!result && o->save && !btp_save_write(o->save,&state,r,&error)) {
        fprintf(stderr,"%s\n",error.text); return 1;
    }
    if (!result && o->export_original && !btp_original_write(o->export_original,&state,&error)) {
        fprintf(stderr,"%s\n",error.text);result=1;
    }
    return result;
}

static void event_trace(void *context,const BtpState *s,const BtpResources *r,const BtpEventNode *e)
{
    FILE *f=context;const BtpAdventure *a=btp_adventure(r);
    fprintf(f,"{\"tick\":%u,\"event\":\"%s\",\"op\":%u,\"credits\":%u,\"flags\":{",s->tick,e->id,e->op,s->credits);
    for (unsigned i=0;i<a->flag_count;++i) fprintf(f,"%s\"%s\":%u",i ? "," : "",a->flags[i],s->event.flags[i]);
    fputs("}}\n",f);
}
int btp_run_headless(const BtpOptions *o,BtpResources *r)
{
    FILE *trace=NULL;
    if (o->event_trace) {
        trace=fopen(o->event_trace,"wb");if (!trace) { fputs("Cannot open event trace\n",stderr);return 1; }
        btp_events_observe(event_trace,trace);
    }
    int result=run_headless(o,r,trace);btp_events_observe(NULL,NULL);
    if (trace) { int bad=ferror(trace);if (fclose(trace) || bad) result=1; }
    return result;
}
