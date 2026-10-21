/* Original-mode state codec. Keep field order, migrations and validation
   independent of the game loop. v44 adds weapon-presentation stage tags using
   the existing stage/age bytes; v40-v43 held stages retain their old meaning.
   Package identity stays in the outer save envelope. */
#include "core/game.h"
#include "core/mission_state.h"
#include "core/talk.h"
#include "core/npc.h"
#include "core/bank.h"
#include "core/economy.h"
#include "core/school.h"
#include "core/animation.h"
#include "core/training.h"
#include "core/combat.h"
#include "core/effects.h"
#include "core/world.h"
#include "core/party.h"
#include "core/campaign.h"
#include "core/service.h"
#include "core/audio.h"
#include "core/menu.h"
#include "core/story.h"
#include "core/yard.h"
#include "core/cache.h"
#include "core/roster_game.h"
#include "core/events.h"
#include <string.h>

static void put16(uint8_t *p, uint16_t v) { p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); }
static uint16_t get16(const uint8_t *p) { return (uint16_t)(p[0] | (uint16_t)p[1] << 8); }
static void put32(uint8_t *p,uint32_t n) { for (unsigned i=0;i<4;++i) p[i]=(uint8_t)(n>>(8u*i)); }
static uint32_t get32(const uint8_t *p) { return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }

#include "core/battle_mission.h"
void btp_state_encode(const BtpState *s, uint8_t b[BTP_STATE_BYTES])
{
    memset(b, 0, BTP_STATE_BYTES);
    memcpy(b, "BTPi", 4); b[4] = 44;
    /* Original/ordinary Legacy states keep their v44 bytes. Updated rule
       identity and the new settings pages require an explicit v45 payload. */
    if (s->combat_profile || (s->campaign.ui>=BTP_MENU_UPDATED_SETTINGS && s->campaign.ui<=BTP_MENU_COMBAT_RULES)) {
        memcpy(b,"BTPj",4);b[4]=45;b[20000]=s->combat_profile;
        put32(b+20001,s->combat_fingerprint);
    }
    /* Category state needs v46, including Legacy games with no combat pack.
       Ordinary saves retain v44/v45; zero class still means the old flat list. */
    if (s->menu.broker_class || s->campaign.ui==BTP_MENU_BROKER_CLASSES) {
        memcpy(b,"BTPk",4);b[4]=46;b[20005]=s->menu.broker_class;
    }
    if (s->project) { memcpy(b,"BTPl",4);b[4]=47;b[20006]=s->project; }
    if (s->event.enabled) {
        memcpy(b,"BTPn",4);b[4]=49;btp_events_encode(s,b+20057);
        if (s->event.mission_state) { memcpy(b,"BTPo",4);b[4]=50;btp_mission_encode(s,b+20185); }
    }
    for (unsigned i = 0; i < 4; ++i) b[8+i] = (uint8_t)(s->tick >> (8 * i));
    b[12] = (uint8_t)s->x_half; b[13] = (uint8_t)(s->x_half >> 8);
    b[14] = (uint8_t)s->y_half; b[15] = (uint8_t)(s->y_half >> 8);
    b[16] = s->map_id; b[17] = s->gate; b[18] = s->facing; b[19] = s->blocked;
    b[20] = s->mode; b[21] = s->entry_selected; b[22] = s->entry_slot;
    memcpy(b + 24, s->story_flags, 16);
    put16(b + 40, s->script.pc); put16(b + 42, s->script.text_offset);
    put16(b + 44, s->script.text_length); put16(b + 46, s->script.menu_table);
    put16(b + 48, s->script.fault_pc); put16(b + 50, s->script.pause_units);
    b[52] = s->script.status; b[53] = s->script.selected; b[54] = s->script.menu_id;
    b[55] = s->script.font; b[56] = s->script.scene; b[57] = s->script.last_opcode; b[58] = s->script.error;
    memcpy(b + 59, s->story_flags + 16, BTP_STORY_PREFIX - 16);
    b[66] = s->script.text_count;
    for (unsigned i = 0; i < BTP_TEXT_SPANS; ++i) {
        put16(b + 68 + 4*i, s->script.text[i].offset);
        put16(b + 70 + 4*i, s->script.text[i].length);
    }
    memcpy(b + 100, s->story_checkpoint, BTP_STORY_PREFIX); b[123] = s->checkpoint_valid;
    b[124] = s->talk.phase; b[125] = s->talk.selected; b[126] = s->talk.count; b[127] = s->talk.mask;
    memcpy(b+128,s->npc_pairs,16);
    b[144] = s->talk.room; b[145] = s->talk.actor; b[146] = s->talk_result; b[147] = s->recruitment;
    b[148] = s->checkpoint_talk_result; b[149] = s->conversation_checkpoint;
    b[150] = s->npc.enabled; b[151] = s->npc.phase;
    memcpy(b+153,s->npc.rng,3); put16(b+156,s->npc.search);
    b[158] = s->npc.bias; b[159] = s->npc.fault;
    for (unsigned i = 0; i < 8; ++i) {
        put16(b+160+5*i,s->npc.actor[i].x); put16(b+162+5*i,s->npc.actor[i].y);
        b[164+5*i] = s->npc.actor[i].direction;
    }
    b[200] = s->npc.loop_timer;
    b[201] = s->npc.allowance_pending;
    for (unsigned i = 0; i < 4; ++i) {
        b[224+i] = (uint8_t)(s->credits >> (8*i));
        b[238+i] = (uint8_t)(s->script.cash_value >> (8*i));
        b[294+i] = (uint8_t)(s->checkpoint_credits >> (8*i));
    }
    put16(b+228,s->allowance_cap); b[230] = s->weapon; b[231] = s->armor; b[232] = s->armor_points;
    b[233] = s->story_flags[39]; b[234] = s->story_checkpoint[39];
    b[235] = s->script.confirm_selected; b[236] = s->script.native_action; b[237] = s->script.cash_after;
    memcpy(b+242,s->script.choices,31); put16(b+273,s->script.confirm_target);
    b[275] = s->script.column; b[276] = s->script.row; b[277] = s->script.has_cash;
    memcpy(b+278,s->script.text_column,BTP_TEXT_SPANS); memcpy(b+286,s->script.text_row,BTP_TEXT_SPANS);
    b[298] = s->checkpoint_weapon; b[299] = s->checkpoint_armor; b[300] = s->checkpoint_armor_points;
    for (unsigned i = 0; i < 3; ++i) for (unsigned j = 0; j < 4; ++j) {
        b[320+4*i+j] = (uint8_t)(s->investments[i] >> (8*j));
        b[332+4*i+j] = (uint8_t)(s->checkpoint_investments[i] >> (8*j));
    }
    b[344] = s->bank.phase; b[345] = s->bank.company; b[346] = s->bank.outcome; b[347] = s->bank.clamped;
    for (unsigned i = 0; i < 4; ++i) {
        b[348+i] = (uint8_t)(s->bank.available >> (8*i));
        b[352+i] = (uint8_t)(s->bank.amount >> (8*i));
    }
    memcpy(b+356,s->bank.input,8); b[364] = s->script.has_accounts;
    memcpy(b+384,s->skills,3); memcpy(b+387,s->checkpoint_skills,3);
    b[390] = s->school.phase; b[391] = s->school.course;
    b[392] = s->school.before; b[393] = s->school.outcome;
    b[394] = s->player_walk; memcpy(b+395,s->npc_walk,8);
    const unsigned sparse[4] = {45,46,47,51};
    for (unsigned i = 0; i < 4; ++i) { b[403+i] = s->story_flags[sparse[i]]; b[407+i] = s->story_checkpoint[sparse[i]]; }
    put16(b+411,s->checkpoint_allowance_cap);
    b[413] = s->script.animation_kind; b[414] = s->script.animation_flags;
    b[415] = s->script.mech_result; b[416] = s->script.mech_after; b[417] = s->entry_action;
    b[418] = s->quiz.phase; b[419] = s->quiz.selected; b[420] = s->quiz.round;
    b[421] = s->quiz.point; b[422] = s->quiz.failed; put16(b+423,s->quiz.used);
    b[426] = s->mission.phase; b[427] = s->mission.corner; b[428] = s->mission.warned;
    b[429] = s->mission.idle; b[430] = s->mission.walk; b[431] = s->mission.direction; put16(b+432,s->mission.elapsed);
    b[434] = s->mission.assignment; b[435] = s->mission.rubble; b[436] = s->mission.rubble_under;
    memcpy(b+437,s->mech_skills,2); memcpy(b+439,s->checkpoint_mech_skills,2);
    b[441]=s->cutscene.active; b[442]=s->cutscene.kind; b[443]=s->cutscene.step;
    b[444]=s->cutscene.cycle; b[445]=s->cutscene.hold;
    put16(b+446,s->cutscene.remaining); put16(b+448,s->cutscene.refresh_fraction);
    b[450]=s->story_flags[52];b[451]=s->story_checkpoint[52];
    b[452]=s->technician;b[453]=s->apprentice;b[454]=s->checkpoint_technician;b[455]=s->checkpoint_apprentice;
    b[456]=s->story_flags[24];b[457]=s->story_checkpoint[24];
    b[458]=s->story_flags[32];b[459]=s->story_checkpoint[32];
    btp_combat_encode(&s->combat,b+4096);
    if (s->battle_mission.enabled) {
        memcpy(b,"BTPp",4);b[4]=51;btp_battle_mission_encode(s,b+BTP_BATTLE_MISSION_OFFSET);
    }
    b[2048]=s->terrain_next;
    for (unsigned i=0;i<64;++i) {
        const BtpTerrainMark *mark=&s->terrain_marks[i];unsigned p=2049+4*i;
        b[p]=mark->sprite;b[p+1]=mark->sector;b[p+2]=mark->x;b[p+3]=mark->y;
    }
    b[2305]=s->effects.count;b[2306]=s->effects.age;b[2307]=s->effects.pending;
    memcpy(b+2308,s->effects.shots,7*sizeof s->effects.shots[0]);
    b[2399]=s->campaign.invasion;b[2400]=s->campaign.owned;
    memcpy(b+2401,s->campaign.mech,125);b[2526]=s->campaign.checkpoint_owned;
    memcpy(b+2527,s->campaign.checkpoint_mech,125);
    put16(b+2652,s->campaign.world_x);put16(b+2654,s->campaign.world_y);
    b[2656]=s->story_flags[36];b[2657]=s->story_checkpoint[36];
    b[2658]=s->campaign.building;
    b[2660]=s->campaign.encounter_mask;b[2661]=s->campaign.encounter;
    b[2662]=s->campaign.mounted;b[2663]=s->campaign.mech_walk;b[2664]=s->campaign.mech_direction;
    b[2665]=s->campaign.ui;b[2666]=s->campaign.selected;b[2667]=s->campaign.member;
    put16(b+2668,s->campaign.mech_x);put16(b+2670,s->campaign.mech_y);
    b[2672]=s->story_flags[55];b[2673]=s->story_checkpoint[55];
    b[2674]=s->script.money_kind;b[2675]=s->script.has_position;
    put16(b+2676,s->script.money_amount);put16(b+2678,s->script.money_target);
    put16(b+2680,s->script.position_x);put16(b+2682,s->script.position_y);
    memcpy(b+2684,s->story_flags,64);memcpy(b+2748,s->story_checkpoint,64);
    btp_party_encode(&s->party,b+2812);btp_party_encode(&s->party_checkpoint,b+10240);
    put16(b+11264,s->campaign.battle_x);put16(b+11266,s->campaign.battle_y);
    put16(b+11268,s->campaign.return_x);put16(b+11270,s->campaign.return_y);b[11272]=s->campaign.return_map;
    b[11280]=s->service.phase;b[11281]=s->service.action;b[11282]=s->service.mech;b[11283]=s->service.selected;
    b[11284]=s->service.kind;b[11285]=s->service.item;b[11286]=s->service.outcome;
    put16(b+11288,s->service.amount);memcpy(b+11290,s->service.input,8);
    b[11300]=s->audio.active;b[11301]=s->audio.countdown;put16(b+11302,s->audio.position);
    put16(b+11304,s->audio.divisor);put16(b+11306,s->audio.phase);put16(b+11308,s->audio.irq_phase);
    for (unsigned i=0;i<4;++i) b[11310+i]=(uint8_t)(s->audio.fraction>>(i*8));
    b[11314]=s->menu.steps;b[11315]=s->menu.sound;b[11316]=s->menu.speed;b[11317]=s->menu.outtakes;
    b[11318]=s->menu.slot;b[11319]=s->menu.io;b[11320]=s->menu.notice;b[11321]=s->menu.quit;
    put16(b+11322,s->menu.map_x);put16(b+11324,s->menu.map_y);
    b[11326]=s->audio.sound_count;memcpy(b+11327,s->audio.sounds,24);put16(b+11351,s->audio.event);
    put16(b+11357,s->audio.sound_phase);
    for (unsigned i=0;i<4;++i) { b[11353+i]=(uint8_t)(s->audio.remaining>>(8*i));b[11359+i]=(uint8_t)(s->audio.sound_fraction>>(8*i)); }
    b[11363]=s->presentation.count;memcpy(b+11364,s->presentation.kinds,24);
    memcpy(b+11424,s->story_flags+64,36);memcpy(b+11460,s->story_checkpoint+64,36);
    memcpy(b+11500,s->original.bytes,BTP_ORIGINAL_BYTES);b[15413]=s->original.valid;
    memcpy(b+15414,s->audio.sounds+24,24);
    memcpy(b+15438,s->effects.shots+7,17*sizeof s->effects.shots[0]);
    put16(b+15659,s->aftermath.eject);b[15661]=s->aftermath.phase;b[15662]=s->aftermath.selected;
    b[15663]=s->aftermath.pilot;b[15664]=s->aftermath.unit;b[15665]=s->aftermath.notice;b[15666]=s->aftermath.applied;
    put16(b+15667,s->aftermath.cash);memcpy(b+15669,s->aftermath.wrecks,24);
    b[15702]=s->aftermath.attempts;memcpy(b+15703,s->aftermath.inspected,16);memcpy(b+15719,s->aftermath.models,16);
    memcpy(b+15693,s->script.choices+31,6);b[15699]=s->script.has_name;b[15700]=s->script.name_after;b[15701]=s->script.name_id;memcpy(b+16384,s->explored,sizeof s->explored);
    b[18432]=s->menu.from_intro;
    b[18433]=s->menu.from_story;
    /* Keep v38's ten-byte report layout, with v39 death flags in the next
       reserved bytes. Older held shots migrate without invented deaths. */
    for (unsigned i=0;i<25;++i) {
        const BtpBattleText *t=i<24 ? &s->effects.text[i] : &s->effects.shown;
        memcpy(b+15735+10*i,t,10);b[15985+i]=t->dead;
        if (s->project) { b[20007+2*i]=t->authored;b[20008+2*i]=t->content_weapon; }
    }
    /* v40 retains the fractional retrace phase; the old byte clocks are
       reserved rather than silently truncating a partial idle interval. */
    put16(b+16010,s->npc.clock);put16(b+16012,s->campaign.world_clock);
    memcpy(b+16014,&s->effects.quiet,sizeof s->effects.quiet);
    b[18434]=s->effects.stage;memcpy(b+18435,s->effects.outtakes,sizeof s->effects.outtakes);
    memcpy(b+18483,&s->cache,sizeof s->cache);
    memcpy(b+19292,&s->late,sizeof s->late);
    memcpy(b+19305,&s->yard,sizeof s->yard);
    b[19305+sizeof s->yard]=s->talk.reply;
    b[19306+sizeof s->yard]=s->disk_origin;
    b[19307+sizeof s->yard]=s->spy_discovered;
    memcpy(b+19308+sizeof s->yard,s->service.damaged,sizeof s->service.damaged);
    for (unsigned i=0;i<4;++i) b[19325+sizeof s->yard+i]=(uint8_t)(s->service.quote_credits>>(8u*i));
}

int btp_state_decode(const uint8_t *b, size_t n, const BtpMap *m, const BtpBld *script, BtpState *s)
{
    if (!b || !m || !s || n < 24) return 0;
    int version = n == 24 && !memcmp(b, "BTP1", 4) && b[4] == 1 ? 1 :
        n == 64 && !memcmp(b, "BTP2", 4) && b[4] == 2 ? 2 :
        n == 128 && !memcmp(b, "BTP3", 4) && b[4] == 3 ? 3 :
        n == 160 && !memcmp(b, "BTP4", 4) && b[4] == 4 ? 4 :
        n == 224 && !memcmp(b, "BTP5", 4) && b[4] == 5 ? 5 :
        n == 320 && !memcmp(b, "BTP6", 4) && b[4] == 6 ? 6 :
        n == 384 && !memcmp(b, "BTP7", 4) && b[4] == 7 ? 7 :
        n == 416 && !memcmp(b, "BTP8", 4) && b[4] == 8 ? 8 :
        n == 416 && !memcmp(b, "BTP9", 4) && b[4] == 9 ? 9 :
        n == 448 && !memcmp(b,"BTPA",4) && b[4] == 10 ? 10 :
        n == 512 && !memcmp(b,"BTPB",4) && b[4] == 11 ? 11 :
        n == 512 && !memcmp(b,"BTPC",4) && b[4] == 12 ? 12 :
        n == 1024 && !memcmp(b,"BTPD",4) && b[4] == 13 ? 13 :
        n == 1024 && !memcmp(b,"BTPE",4) && b[4] == 14 ? 14 :
        n == 2048 && !memcmp(b,"BTPF",4) && b[4] == 15 ? 15 :
        n == 4096 && !memcmp(b,"BTPG",4) && b[4] == 16 ? 16 :
        n == 4096 && !memcmp(b,"BTPH",4) && b[4] == 17 ? 17 :
        n == 16384 && !memcmp(b,"BTPI",4) && b[4] == 18 ? 18 :
        n == 16384 && !memcmp(b,"BTPJ",4) && b[4] == 19 ? 19 :
        n == 16384 && !memcmp(b,"BTPK",4) && b[4] == 20 ? 20 :
        n == 16384 && !memcmp(b,"BTPL",4) && b[4] == 21 ? 21 :
        n == 16384 && !memcmp(b,"BTPM",4) && b[4] == 22 ? 22 :
        n == 16384 && !memcmp(b,"BTPN",4) && b[4] == 23 ? 23 :
        n == 16384 && !memcmp(b,"BTPO",4) && b[4] == 24 ? 24 :
        n == BTP_STATE_BYTES && !memcmp(b,"BTPP",4) && b[4]==25 ? 25 :
        n == BTP_STATE_BYTES && !memcmp(b,"BTPQ",4) && b[4]==26 ? 26 :
        n == BTP_STATE_BYTES && !memcmp(b,"BTPR",4) && b[4]==27 ? 27 :
        n == BTP_STATE_BYTES && !memcmp(b,"BTPS",4) && b[4]==28 ? 28 :
        n == BTP_STATE_BYTES && !memcmp(b,"BTPT",4) && b[4]==29 ? 29 :
        n == BTP_STATE_BYTES && !memcmp(b,"BTPU",4) && b[4]==30 ? 30 :
        n == BTP_STATE_BYTES && !memcmp(b,"BTPV",4) && b[4]==31 ? 31 :
        n == BTP_STATE_BYTES && !memcmp(b,"BTPW",4) && b[4]==32 ? 32 :
        n == BTP_STATE_BYTES && !memcmp(b,"BTPX",4) && b[4]==33 ? 33 :
        n == BTP_STATE_BYTES && !memcmp(b,"BTPY",4) && b[4]==34 ? 34 :
        n == BTP_STATE_BYTES && !memcmp(b,"BTPZ",4) && b[4]==35 ? 35 :
        n == BTP_STATE_BYTES && !memcmp(b,"BTPa",4) && b[4]==36 ? 36 :
        n == BTP_STATE_BYTES && !memcmp(b,"BTPb",4) && b[4]==37 ? 37 :
        n == BTP_STATE_BYTES && !memcmp(b,"BTPc",4) && b[4]==38 ? 38 :
        n == BTP_STATE_BYTES && !memcmp(b,"BTPd",4) && b[4]==39 ? 39 :
        n == BTP_STATE_BYTES && !memcmp(b,"BTPe",4) && b[4]==40 ? 40 :
        n == BTP_STATE_BYTES && !memcmp(b,"BTPf",4) && b[4]==41 ? 41 :
        n == BTP_STATE_BYTES && !memcmp(b,"BTPg",4) && b[4]==42 ? 42 :
        n == BTP_STATE_BYTES && !memcmp(b,"BTPh",4) && b[4]==43 ? 43 :
        n == BTP_STATE_BYTES && !memcmp(b,"BTPi",4) && b[4]==44 ? 44 :
        n == BTP_STATE_BYTES && !memcmp(b,"BTPj",4) && b[4]==45 ? 45 :
        n == BTP_STATE_BYTES && !memcmp(b,"BTPk",4) && b[4]==46 ? 46 :
        n == BTP_STATE_BYTES && !memcmp(b,"BTPl",4) && b[4]==47 ? 47 :
        n == BTP_STATE_BYTES && !memcmp(b,"BTPm",4) && b[4]==48 ? 48 :
        n == BTP_STATE_BYTES && !memcmp(b,"BTPn",4) && b[4]==49 ? 49 :
        n == BTP_STATE_BYTES && !memcmp(b,"BTPo",4) && b[4]==50 ? 50 :
        n == BTP_STATE_BYTES && !memcmp(b,"BTPp",4) && b[4]==51 ? 51 : 0;
    if (!version) return 0;
    if (version>=18 && version<38 && b[10232]) return 0; /* v38 critical report count. */
    if (version>=18 && version<35 && b[10233]) return 0; /* v35 weapon-window presentation bits. */
    for (unsigned i = 5; i < 8; ++i) if (b[i]) return 0;
    if (version == 1) { for (unsigned i = 20; i < 24; ++i) if (b[i]) return 0; }
    else {
        if (b[23]) return 0;
        if (version == 2) { for (unsigned i = 59; i < 64; ++i) if (b[i]) return 0; }
        else {
            if (b[67]) return 0;
            unsigned end = version >= 6 ? 224u : (unsigned)n;
            for (unsigned i = version == 3 ? 124u : version == 4 ? 150u : 202u; i < end; ++i) if (b[i]) return 0;
            if (version >= 6) for (unsigned i = 301; i < 320; ++i) if (b[i]) return 0;
            if (version >= 7) for (unsigned i = 365; i < 384; ++i) if (b[i]) return 0;
            if (version == 8) for (unsigned i = 394; i < n; ++i) if (b[i]) return 0;
            if (version == 9) for (unsigned i = 403; i < n; ++i) if (b[i]) return 0;
            if (version >= 10) {
                if (b[425]) return 0;
                unsigned start=version==10 ? 434u : version==11 ? 441u : version==12 ? 450u : version<15 ? 896u : version>=33 ? 19329u+(unsigned)sizeof(BtpYardState) : version>=31 ? 19308u+(unsigned)sizeof(BtpYardState) : version>=30 ? 19307u+(unsigned)sizeof(BtpYardState) : version>=29 ? 19306u+(unsigned)sizeof(BtpYardState) : version>=28 ? 19292u+(unsigned)sizeof(BtpLateState) : version>=27 ? 18483u+(unsigned)sizeof(BtpCacheState) : version>=26 ? 18483u : version>=25 ? 18433u : version>=24 ? 15702u : version>=22 ? 15693u : version>=21 ? 15414u : version>=20 ? 11388u : version>=19 ? 11326u : version>=18 ? 11314u : version>=17 ? 2684u : version>=16 ? 2399u : 1803u;
                for (unsigned i=start;i<n;++i) if (b[i] && !(version>=45 && i>=20000 && i<(version>=50 ? 20185u+BTP_MISSION_BYTES : version>=48 ? 20185u : version>=47 ? 20057u : version>=46 ? 20006u : 20005u))) return 0;
                if (version>=13) for (unsigned i=version>=15 ? 460u : 452u;i<512;++i) if (b[i]) return 0;
                if (version==13 && b[878]) return 0; /* v14 firing-effect countdown. */
            }
        }
    }
    BtpState result = {.credits=35,.allowance_cap=50};
    if (version>=48 && !btp_events_decode(&result,b+20057)) return 0;
    if (version>=50 && !btp_mission_decode(&result,b+20185)) return 0;
    if (version>=51 && !btp_battle_mission_decode(&result,b+BTP_BATTLE_MISSION_OFFSET)) return 0;
    if (version>=45) {
        result.combat_profile=b[20000];result.combat_fingerprint=get32(b+20001);
        if (result.combat_profile>1 || (!!result.combat_profile != !!result.combat_fingerprint)) return 0;
    }
    if (version>=27) memcpy(&result.cache,b+18483,sizeof result.cache);
    if (version>=28) {
        memcpy(&result.late,b+19292,sizeof result.late);
        for (unsigned i=0;i<10;++i) if (result.late.travel[i]>8) return 0;
        if (result.late.invasion_event>5 || result.late.invasion_popup>6 || result.late.invasion_end>1) return 0;
    }
    if (version>=29) memcpy(&result.yard,b+19305,sizeof result.yard);
    if (version>=30) result.disk_origin=b[19306+sizeof result.yard];
    if (version>=31) result.spy_discovered=b[19307+sizeof result.yard];
    if (version>=33) {
        memcpy(result.service.damaged,b+19308+sizeof result.yard,sizeof result.service.damaged);
        for (unsigned i=0;i<4;++i) result.service.quote_credits|=(uint32_t)b[19325+sizeof result.yard+i]<<(8u*i);
    }
    if (result.spy_discovered>1) return 0;
    if (version>=25) {
        memcpy(result.explored,b+16384,sizeof result.explored);
        for (unsigned i=version>=40 ? 16032u : version>=39 ? 16010u : version>=38 ? 15985u : version>=37 ? 15735u : 15702u;i<16384;++i) if (b[i]) return 0;
    }
    if (version>=22) {
        memcpy(result.audio.sounds+24,b+15414,24);memcpy(result.effects.shots+7,b+15438,17*sizeof result.effects.shots[0]);
        result.aftermath=(BtpAftermathState){.eject=get16(b+15659),.phase=b[15661],.selected=b[15662],.pilot=b[15663],.unit=b[15664],.notice=b[15665],.applied=b[15666],.cash=get16(b+15667)};
        memcpy(result.aftermath.wrecks,b+15669,24);
        if (version>=37) {
            result.aftermath.attempts=b[15702];memcpy(result.aftermath.inspected,b+15703,16);memcpy(result.aftermath.models,b+15719,16);
        }
    }
    result.menu=(BtpMenuState){.steps=1,.sound=1,.speed=2,.outtakes=0};
    if (version>=19) {
        result.menu=(BtpMenuState){b[11314],b[11315],b[11316],b[11317],b[11318],b[11319],b[11320],b[11321],get16(b+11322),get16(b+11324),0,0,0};
    }
    if (version>=25) result.menu.from_intro=b[18432];
    if (version>=26) result.menu.from_story=b[18433];
    if (version>=46) result.menu.broker_class=b[20005];
    if (version>=47) { result.project=b[20006];if (result.project!=1) return 0; }
    if (version>=38) {
        for (unsigned i=0;i<25;++i) {
            BtpBattleText *t=i<24 ? &result.effects.text[i] : &result.effects.shown;
            memcpy(t,b+15735+10*i,10);if (version>=39) t->dead=b[15985+i];
            if (version>=47) { t->authored=b[20007+2*i];t->content_weapon=b[20008+2*i]; }
        }
    }
    if (version>=40) memcpy(&result.effects.quiet,b+16014,sizeof result.effects.quiet);
    if (version>=26) { result.effects.stage=b[18434];memcpy(result.effects.outtakes,b+18435,sizeof result.effects.outtakes); }
    if (version<44 && result.effects.stage>BTP_EFFECT_LEGACY) return 0;
    if (version>=18) {
        memcpy(result.story_flags,b+2684,64);memcpy(result.story_checkpoint,b+2748,64);
        if (version>=21) {
            memcpy(result.story_flags+64,b+11424,36);memcpy(result.story_checkpoint+64,b+11460,36);
            memcpy(result.original.bytes,b+11500,BTP_ORIGINAL_BYTES);result.original.valid=b[15413];
            if (result.original.valid>1 || (result.original.valid && result.original.bytes[0]!=12)) return 0;
            if (!result.original.valid) for (unsigned i=0;i<BTP_ORIGINAL_BYTES;++i) if (result.original.bytes[i]) return 0;
            for (unsigned i=11388;i<11424;++i) if (b[i]) return 0;
            for (unsigned i=11496;i<11500;++i) if (b[i]) return 0;
        }
        if (!btp_party_decode(b+2812,&result.party) || !btp_party_decode(b+10240,&result.party_checkpoint)) return 0;
        result.campaign.battle_x=get16(b+11264);result.campaign.battle_y=get16(b+11266);
        result.campaign.return_x=get16(b+11268);result.campaign.return_y=get16(b+11270);result.campaign.return_map=b[11272];
        result.service.phase=b[11280];result.service.action=b[11281];result.service.mech=b[11282];result.service.selected=b[11283];
        result.service.kind=b[11284];result.service.item=b[11285];result.service.outcome=b[11286];result.service.amount=get16(b+11288);
        memcpy(result.service.input,b+11290,8);
        result.audio=(BtpAudioState){.active=b[11300],.countdown=b[11301],.position=get16(b+11302),.divisor=get16(b+11304),.phase=get16(b+11306),.irq_phase=get16(b+11308)};
        if (version>=22) memcpy(result.audio.sounds+24,b+15414,24);
        for (unsigned i=0;i<4;++i) result.audio.fraction|=(uint32_t)b[11310+i]<<(i*8);
        if (version>=20) {
            result.audio.sound_count=b[11326];memcpy(result.audio.sounds,b+11327,24);result.audio.event=get16(b+11351);
            result.audio.sound_phase=get16(b+11357);
            for (unsigned i=0;i<4;++i) { result.audio.remaining|=(uint32_t)b[11353+i]<<(8*i);result.audio.sound_fraction|=(uint32_t)b[11359+i]<<(8*i); }
            result.presentation.count=b[11363];memcpy(result.presentation.kinds,b+11364,24);
            if (result.presentation.count>24) return 0;
            for (unsigned i=0;i<24;++i) if (i<result.presentation.count ? !result.presentation.kinds[i] || result.presentation.kinds[i]>=BTP_ANM_COUNT : result.presentation.kinds[i]!=0) return 0;
        }
        if (b[11298] || b[11299]) return 0;
        if (b[11287]) return 0;
        for (unsigned i=11273;i<11280;++i) if (b[i]) return 0;
        for (unsigned i=3836;i<4096;++i) if (b[i]) return 0;
        for (unsigned i=512;i<2048;++i) if (b[i]) return 0;
    }
    if (version>=17) {
        result.campaign.invasion=b[2399];result.campaign.owned=b[2400];
        memcpy(result.campaign.mech,b+2401,125);result.campaign.checkpoint_owned=b[2526];
        memcpy(result.campaign.checkpoint_mech,b+2527,125);
        result.campaign.world_x=get16(b+2652);result.campaign.world_y=get16(b+2654);
        result.story_flags[36]=b[2656];result.story_checkpoint[36]=b[2657];
        result.campaign.building=b[2658];
        if (b[2659]>=(version>=40 ? 1u : 4u)) return 0;
        result.campaign.world_clock=version>=40 ? get16(b+16012) : (uint16_t)(b[2659]*BTP_OUTDOOR_TICK);
        result.campaign.encounter_mask=b[2660];result.campaign.encounter=b[2661];
        result.campaign.mounted=b[2662];result.campaign.mech_walk=b[2663];result.campaign.mech_direction=b[2664];
        result.campaign.ui=b[2665];result.campaign.selected=b[2666];result.campaign.member=b[2667];
        result.campaign.mech_x=get16(b+2668);result.campaign.mech_y=get16(b+2670);
        if (result.campaign.invasion>1 || result.campaign.owned>1 || result.campaign.checkpoint_owned>1 ||
            result.campaign.world_x>2047 || result.campaign.world_y>2047 || result.campaign.building>=(version>=42 ? 27u : 26u) ||
            result.campaign.world_clock>=BTP_OUTDOOR_PERIOD || result.campaign.encounter>(version>=48 ? 5u : version>=29 ? 4u : 2u) || result.campaign.mounted>result.campaign.owned ||
            result.campaign.mech_walk>15 || result.campaign.mech_direction>7 || result.campaign.ui>(version>=49 ? BTP_MENU_JOURNAL : version>=46 ? BTP_MENU_BROKER_CLASSES : version>=45 ? BTP_MENU_COMBAT_RULES : version>=42 ? BTP_MENU_BROKER_SELL_RESULT : version>=41 ? BTP_MENU_BROKER_RESULT : version>=30 ? BTP_MENU_MECH_PICK : version>=25 ? BTP_MENU_MECH : version>=23 ? BTP_MENU_RECIPIENT : version>=19 ? BTP_MENU_QUIT : 6) ||
            result.campaign.selected>(version>=23 ? 8u : 7u) ||
            result.campaign.member>(version>=49 && result.campaign.ui==BTP_MENU_JOURNAL ? 31u : version>=43 && result.campaign.ui>=BTP_MENU_BROKER &&
                result.campaign.ui<=BTP_MENU_BROKER_RESULT ? (version>=47 ? BTP_ROSTER_MAX : BTP_LEGACY_ROSTER_MAX)-1u : 7u) ||
            result.campaign.mech_x>2047 || result.campaign.mech_y>2047) return 0;
    }
    if (version>=16) {
        result.terrain_next=b[2048];if (result.terrain_next>63) return 0;
        for (unsigned i=0;i<64;++i) {
            unsigned p=2049+4*i;BtpTerrainMark *mark=&result.terrain_marks[i];
            *mark=(BtpTerrainMark){b[p],b[p+1],b[p+2],b[p+3]};
            if (version>=34) {
                /* Original cleared entries can retain a harmless old Y byte. */
                if ((mark->sprite && (mark->sprite<124 || mark->sprite>129)) || mark->x>127 || mark->y>127) return 0;
            } else {
                if (mark->sprite ? (mark->sprite!=124 && mark->sprite!=125 && mark->sprite!=126 && mark->sprite!=128 && mark->sprite!=129) ||
                    (version>=29 ? mark->sector>14 : mark->sector!=1) || (!result.campaign.invasion && (mark->x>127 || mark->y>127)) :
                    mark->sector || mark->x || mark->y) return 0;
                /* Old saves stored a town ID and discarded the battlefield
                   origin. Clear that ambiguous decoration on migration;
                   retaining it would invent wrecks at the next encounter. */
                *mark=(BtpTerrainMark){0};
            }
        }
        if (version<34) result.terrain_next=0;
        result.effects.count=b[2305];result.effects.age=b[2306];result.effects.pending=b[2307];
        if (version<26 && result.effects.pending>2) return 0;
        if (version<26 && result.effects.count) result.effects.stage=BTP_EFFECT_LEGACY;
        if (version<29 && result.effects.stage==BTP_EFFECT_DEATH_SOUND) return 0;
        memcpy(result.effects.shots,b+2308,7*sizeof result.effects.shots[0]);
    }
    for (unsigned i = 0; i < 4; ++i) result.tick |= (uint32_t)b[8+i] << (8 * i);
    if (version<44) for (unsigned i=0;i<64;++i)
        if ((result.terrain_marks[i].sprite&254u)==124)
            result.terrain_marks[i].sprite=(uint8_t)((124u+(result.tick&1u))^1u);
    result.x_half = (uint16_t)(b[12] | (uint16_t)b[13] << 8);
    result.y_half = (uint16_t)(b[14] | (uint16_t)b[15] << 8);
    result.map_id = b[16]; result.gate = b[17]; result.facing = b[18]; result.blocked = b[19];
    if (version==48) { result.event.map=(uint16_t)(result.map_id-16u);result.event.return_map=(uint16_t)(result.campaign.return_map>=16 ? result.campaign.return_map-16u : 0u); }
    if ((result.map_id != 1 && !(version>=48 && result.map_id>=16 && (version>=49 || result.map_id<32)) && !(version>=17 && result.map_id<=14 && b[28])) || (result.cache.active ? result.gate!=33 && result.gate!=139 : result.gate!=85) ||
        (version >= 10 ? result.facing != BTP_IDLE && !btp_action_moves((BtpAction)result.facing) : result.facing > BTP_RIGHT) ||
        result.blocked > (version>=30 ? BTP_WATER : BTP_EDGE) ||
        (version>=30 && result.campaign.invasion ? result.x_half>=256 : result.campaign.encounter ? result.x_half>=128 : result.map_id ? result.x_half >= 2 * m->width : result.x_half>=2048) ||
        (version>=30 && result.campaign.invasion ? result.y_half>257 : result.campaign.encounter ? result.y_half>=128 : result.map_id ? result.y_half >= 2 * m->height && !(version>=17 && result.campaign.invasion && result.y_half<=129) : result.y_half>=2048))
        return 0;
    if (version > 1) {
        result.mode = b[20]; result.entry_selected = b[21]; result.entry_slot = b[22];
        memcpy(result.story_flags, b + 24, 16);
        result.script = (BtpScriptState){.pc=get16(b+40),.text_offset=get16(b+42),
            .text_length=get16(b+44),.menu_table=get16(b+46),.fault_pc=get16(b+48),.pause_units=get16(b+50),
            .status=b[52],.selected=b[53],.menu_id=b[54],.font=b[55],.scene=b[56],.last_opcode=b[57],.error=b[58]};
        BtpScriptState *v = &result.script;
        if (version>=24) {
            memcpy(v->choices+31,b+15693,6);v->has_name=b[15699];v->name_after=b[15700];v->name_id=b[15701];
            if (v->has_name>1 || v->name_id>=10 || (!v->has_name && (v->name_after || v->name_id))) return 0;
        }
        if (version>=17) {
            result.story_flags[55]=b[2672];result.story_checkpoint[55]=b[2673];
            v->money_kind=b[2674];v->has_position=b[2675];v->money_amount=get16(b+2676);v->money_target=get16(b+2678);
            v->position_x=get16(b+2680);v->position_y=get16(b+2682);
            if (v->money_kind || v->money_target || v->has_position ||
                (v->money_amount && !(version>=28 && b[20]==BTP_BUILDING && b[52]==BTP_SCRIPT_EFFECT && v->money_amount<=18))) return 0;
        }
        if (version >= 3) {
            memcpy(result.story_flags + 16, b + 59, BTP_STORY_PREFIX - 16);
            v->text_count = b[66];
            for (unsigned i = 0; i < BTP_TEXT_SPANS; ++i)
                v->text[i] = (BtpTextSpan){get16(b+68+4*i),get16(b+70+4*i)};
            memcpy(result.story_checkpoint, b + 100, BTP_STORY_PREFIX); result.checkpoint_valid = b[123];
            if (version >= 4) {
                result.talk = (BtpTalkState){.phase=b[124],.selected=b[125],.count=b[126],.mask=b[127],
                    .room=b[144],.actor=b[145]};
                if (version>=29) result.talk.reply=b[19305+sizeof result.yard];
                memcpy(result.npc_pairs,b+128,16);
                result.talk_result = b[146]; result.recruitment = b[147];
                result.checkpoint_talk_result = b[148]; result.conversation_checkpoint = b[149];
                if (version >= 5) {
                    result.npc.enabled = b[150]; result.npc.phase = b[151];
                    if (b[152]>=(version>=40 ? 1u : 4u)) return 0;
                    /* Legacy clocks counted elapsed 32 ms ticks. Migrate
                       that elapsed time without consuming RNG or timers. */
                    result.npc.clock=version>=40 ? get16(b+16010) : (uint16_t)(b[152]*BTP_OUTDOOR_TICK);
                    memcpy(result.npc.rng,b+153,3); result.npc.search = get16(b+156);
                    result.npc.bias = b[158]; result.npc.fault = b[159];
                    result.npc.loop_timer = b[200];
                    result.npc.allowance_pending = b[201];
                    if (version == 5 && result.npc.enabled && !result.npc.allowance_pending) result.credits = 50;
                    for (unsigned i = 0; i < 8; ++i) result.npc.actor[i] =
                        (BtpNpc){get16(b+160+5*i),get16(b+162+5*i),b[164+5*i]};
                }
            }
        } else {
            if (v->text_offset || v->text_length) {
                v->text_count = 1; v->text[0] = (BtpTextSpan){v->text_offset,v->text_length};
            }
            if (v->status == BTP_SCRIPT_WAIT) {
                result.checkpoint_valid = 1;
                memcpy(result.story_checkpoint, result.story_flags, BTP_STORY_BYTES);
            }
        }
        if (version >= 6) {
            result.credits = result.checkpoint_credits = 0;
            for (unsigned i = 0; i < 4; ++i) {
                result.credits |= (uint32_t)b[224+i] << (8*i);
                v->cash_value |= (uint32_t)b[238+i] << (8*i);
                result.checkpoint_credits |= (uint32_t)b[294+i] << (8*i);
            }
            result.allowance_cap = get16(b+228); result.weapon = b[230]; result.armor = b[231]; result.armor_points = b[232];
            result.story_flags[39] = b[233]; result.story_checkpoint[39] = b[234];
            v->confirm_selected = b[235]; v->native_action = b[236]; v->cash_after = b[237];
            memcpy(v->choices,b+242,31); v->confirm_target = get16(b+273);
            v->column = b[275]; v->row = b[276]; v->has_cash = b[277];
            memcpy(v->text_column,b+278,BTP_TEXT_SPANS); memcpy(v->text_row,b+286,BTP_TEXT_SPANS);
            result.checkpoint_weapon = b[298]; result.checkpoint_armor = b[299]; result.checkpoint_armor_points = b[300];
            if (version >= 7) {
                for (unsigned i = 0; i < 3; ++i) for (unsigned j = 0; j < 4; ++j) {
                    result.investments[i] |= (uint32_t)b[320+4*i+j] << (8*j);
                    result.checkpoint_investments[i] |= (uint32_t)b[332+4*i+j] << (8*j);
                }
                result.bank = (BtpBankState){.phase=b[344],.company=b[345],.outcome=b[346],.clamped=b[347]};
                for (unsigned i = 0; i < 4; ++i) {
                    result.bank.available |= (uint32_t)b[348+i] << (8*i);
                    result.bank.amount |= (uint32_t)b[352+i] << (8*i);
                }
                memcpy(result.bank.input,b+356,8); v->has_accounts = b[364];
            }
            if (version >= 8) {
                memcpy(result.skills,b+384,3); memcpy(result.checkpoint_skills,b+387,3);
                result.school = (BtpSchoolState){b[390],b[391],b[392],b[393]};
            }
            if (version >= 10) {
                const unsigned sparse[4] = {45,46,47,51};
                for (unsigned i = 0; i < 4; ++i) {
                    result.story_flags[sparse[i]] = b[403+i]; result.story_checkpoint[sparse[i]] = b[407+i];
                }
                result.checkpoint_allowance_cap = get16(b+411);
                v->animation_kind = b[413]; v->animation_flags = b[414];
                v->mech_result = b[415]; v->mech_after = b[416]; result.entry_action = b[417];
                result.quiz = (BtpQuizState){.phase=b[418],.selected=b[419],.round=b[420],.point=b[421],.failed=b[422],.used=get16(b+423)};
                result.mission = (BtpMissionState){.phase=b[426],.corner=b[427],.warned=b[428],.idle=b[429],
                    .walk=b[430],.direction=b[431],.elapsed=get16(b+432)};
                if (version >= 11) {
                    result.mission.assignment=b[434]; result.mission.rubble=b[435]; result.mission.rubble_under=b[436];
                    if (version<16 && result.mission.assignment>4) return 0;
                    memcpy(result.mech_skills,b+437,2); memcpy(result.checkpoint_mech_skills,b+439,2);
                    if (version >= 12) result.cutscene=(BtpCutsceneState){.active=b[441],.kind=b[442],.step=b[443],
                        .cycle=b[444],.hold=b[445],.remaining=get16(b+446),.refresh_fraction=get16(b+448)};
                    if (version >= 13) {
                        result.story_flags[52]=b[450];result.story_checkpoint[52]=b[451];
                        uint8_t combat[BTP_COMBAT_SAVE_BYTES]={0};
                        memcpy(combat,b+(version>=18 ? 4096 : 512),version>=18 ? BTP_COMBAT_SAVE_BYTES : version>=15 ? BTP_COMBAT_LEGACY_BYTES : 384u);
                        if (version>=51) memset(combat+5600,0,BTP_BATTLE_MISSION_BYTES);
                        if (!btp_combat_decode(combat,&result.combat)) return 0;
                        if (version<=15) for (unsigned i=0;i<result.combat.count;++i) {
                            BtpCombatUnit *u=&result.combat.unit[i];
                            if (u->infantry && (u->cover==8 || u->cover==16)) u->cover/=4;
                        }
                        if (version<15 && result.mission.assignment==2 && result.mission.phase) {
                            result.combat.count=2;result.combat.target_unit=1;result.combat.kick_target=255;
                            result.combat.last_target=1;
                            memset(result.combat.enemy_orders,255,sizeof result.combat.enemy_orders);
                            memset(result.combat.enemy_modes,255,sizeof result.combat.enemy_modes);
                        }
                        if (version>=15) {
                            result.technician=b[452];result.apprentice=b[453];
                            result.checkpoint_technician=b[454];result.checkpoint_apprentice=b[455];
                            result.story_flags[24]=b[456];result.story_checkpoint[24]=b[457];
                            result.story_flags[32]=b[458];result.story_checkpoint[32]=b[459];
                        }
                    }
                }
                if (result.story_flags[45] != result.recruitment || result.story_flags[46] != result.talk_result ||
                    result.story_flags[51] != (uint8_t)result.allowance_cap || result.story_flags[52] != (uint8_t)(result.allowance_cap>>8) || result.story_flags[47] > 1 ||
                    result.recruitment > 1 || v->mech_result > 3 || v->mech_after > v->text_count ||
                    (!v->mech_result && v->mech_after) ||
                    (v->mech_result && (result.entry_slot || result.mission.phase != BTP_MISSION_RESULT ||
                        !result.story_flags[1] || !v->mech_after)) ||
                    (!(version>=28 && result.campaign.building==16 && v->animation_kind<10 && (v->animation_flags==1 || v->animation_flags==2)) &&
                    (v->animation_kind ? (v->animation_kind != 8 && !(version>=17 && v->animation_kind==9) && !(version>=18 && v->animation_kind==6) && !(version>=27 && v->animation_kind>=10 && v->animation_kind<=14)) || v->animation_flags != 1 ||
                        (v->animation_kind==8 ? result.entry_slot != 6 : v->animation_kind==9 ? result.entry_slot != 0 : v->animation_kind>=10 ? !result.cache.active || result.campaign.building!=25 : result.campaign.building!=5 && result.campaign.building!=9 && result.campaign.building!=11 && result.campaign.building!=13) : v->animation_flags != 0))) return 0;
            } else {
                result.entry_action = result.facing;
                result.story_flags[45] = result.recruitment; result.story_flags[46] = result.talk_result;
                result.story_flags[51] = (uint8_t)result.allowance_cap;
                if (result.checkpoint_valid) {
                    result.checkpoint_allowance_cap = result.allowance_cap;
                    result.story_checkpoint[45] = result.recruitment; result.story_checkpoint[46] = result.checkpoint_talk_result;
                    result.story_checkpoint[51] = (uint8_t)result.allowance_cap;
                }
            }
            static const uint8_t protection[6] = {0,25,40,30,50,50};
            if ((result.allowance_cap != 50 && !(version >= 10 && result.allowance_cap == 150) && !(version >= 11 && result.allowance_cap == 250) && !(version >= 13 && result.allowance_cap == 500) && !(version>=15 && (result.allowance_cap==1000 || result.allowance_cap==2000)) && !(version>=16 && result.allowance_cap==3000)) || result.weapon > 13 || result.armor > 5 ||
                result.armor_points > protection[result.armor] || result.checkpoint_weapon > 13 || result.checkpoint_armor > 5 ||
                result.checkpoint_armor_points > protection[result.checkpoint_armor] ||
                v->confirm_selected > 1 || v->has_cash > 1 || v->cash_after > v->text_count ||
                (!v->has_cash && (v->cash_after || v->cash_value)) || (v->has_cash && !v->cash_after) ||
                (version>=24 ? v->column>26 || v->row>24 : v->column || (v->row && v->row != 14 && v->row != 22 && !(version >= 7 && v->row == 15))) ||
                (v->native_action && (v->native_action < (version >= 10 ? 1 : version >= 8 ? 4 : version == 7 ? 6 : 9) || !btp_native_supported(v->native_action) || (version<15 && v->native_action>12)) &&
                    !(v->status == BTP_SCRIPT_ERROR && v->error == BTP_SCRIPT_OPCODE && v->last_opcode == 0xf5)) ||
                (result.npc.enabled && result.npc.allowance_pending != btp_economy_below_cap(&result))) return 0;
            for (unsigned i = 0; i < BTP_TEXT_SPANS; ++i)
                if ((version>=24 ? v->text_column[i]>26 || v->text_row[i]>24 : v->text_column[i] || (v->text_row[i] && v->text_row[i] != 14 && v->text_row[i] != 22 &&
                    !(version >= 7 && v->text_row[i] == 15))) ||
                    (i >= v->text_count && (v->text_row[i] || v->text_column[i]))) return 0;
            for (unsigned i = 0; i < BTP_MENUS; ++i) {
                unsigned count = btp_menu_count(i);
                if (count ? v->choices[i] >= count : v->choices[i] != 0) return 0;
            }
        } else {
            if (v->menu_id == 8) v->choices[8] = v->selected;
            if (v->status == BTP_SCRIPT_NATIVE) v->native_action = 12;
            if (result.checkpoint_valid) result.checkpoint_credits = result.credits;
            result.entry_action = result.facing;
            result.story_flags[45] = result.recruitment; result.story_flags[46] = result.talk_result;
            result.story_flags[51] = (uint8_t)result.allowance_cap;
            if (result.checkpoint_valid) {
                result.checkpoint_allowance_cap = result.allowance_cap;
                result.story_checkpoint[45] = result.recruitment;
                result.story_checkpoint[46] = result.checkpoint_talk_result;
                result.story_checkpoint[51] = (uint8_t)result.allowance_cap;
            }
        }
        if (result.mode > (version>=48 ? BTP_EVENT : version>=29 ? BTP_YARD : version>=27 ? BTP_ENDING : version>=25 ? BTP_BEGIN : version>=24 ? BTP_LOGO : version>=22 ? BTP_GAME_OVER : version>=18 ? BTP_TITLE : version>=17 ? BTP_ACTIONS : version >= 10 ? BTP_MISSION : BTP_SCRIPT_FAULT) || result.entry_selected > 1 || result.entry_slot > (version>=17 ? 15 : 7) ||
            v->status > (version>=24 ? BTP_SCRIPT_EFFECT : version>=18 ? BTP_SCRIPT_RECRUIT : version >= 12 ? BTP_SCRIPT_ANIMATION : version >= 6 ? BTP_SCRIPT_CONFIRM : version >= 4 ? BTP_SCRIPT_NATIVE : BTP_SCRIPT_ERROR) || v->selected > (version>=24 ? 7u : version >= 6 ? 6u : 4u) ||
            v->error > (version >= 4 ? BTP_SCRIPT_NATIVE_CONTEXT : BTP_SCRIPT_TEXT_LIMIT) ||
            v->text_count > BTP_TEXT_SPANS || result.checkpoint_valid > 1) return 0;
        for (unsigned i = v->text_count; i < BTP_TEXT_SPANS; ++i)
            if (v->text[i].offset || v->text[i].length) return 0;
        if (result.checkpoint_valid) {
            if ((result.mode != BTP_BUILDING && result.mode != BTP_MISSION && result.mode!=BTP_ENCOUNTER && result.mode!=BTP_GAME_OVER && result.mode!=BTP_YARD && !(result.mode==BTP_ACTIONS && result.menu.from_story)) || (v->status != BTP_SCRIPT_WAIT && v->status != BTP_SCRIPT_NATIVE &&
                v->status != BTP_SCRIPT_CONFIRM && v->status != BTP_SCRIPT_ANIMATION && v->status!=BTP_SCRIPT_RECRUIT &&
                !(version>=28 && v->status==BTP_SCRIPT_EFFECT))) return 0;
            if (version >= 6 && result.checkpoint_allowance_cap != 50 && result.checkpoint_allowance_cap != 150 && !(version >= 11 && result.checkpoint_allowance_cap == 250) && !(version >= 13 && result.checkpoint_allowance_cap == 500) && !(version>=15 && (result.checkpoint_allowance_cap==1000 || result.checkpoint_allowance_cap==2000)) && !(version>=16 && result.checkpoint_allowance_cap==3000)) return 0;
        } else {
            if (result.checkpoint_talk_result || result.checkpoint_credits || result.checkpoint_weapon ||
                result.checkpoint_armor || result.checkpoint_armor_points || result.checkpoint_allowance_cap) return 0;
            for (unsigned i = 0; i < 3; ++i) if (result.checkpoint_investments[i] || result.checkpoint_skills[i]) return 0;
            if (result.checkpoint_mech_skills[0] || result.checkpoint_mech_skills[1] || result.checkpoint_technician || result.checkpoint_apprentice) return 0;
            for (unsigned i = 0; i < BTP_STORY_BYTES; ++i) if (result.story_checkpoint[i]) return 0;
        }
        if (result.mode != BTP_EXPLORE && result.entry_slot != 1 &&
            !(version>=42 && result.map_id==2 && result.story_flags[4] &&
                result.entry_slot==BTP_BROKER_ENTRY && result.campaign.building==BTP_BROKER_BUILDING) &&
            !(version>=17 && result.story_flags[4] && m->room_map[result.entry_slot]<26) &&
            !(version >= 6 && (result.entry_slot == 3 || result.entry_slot == 4)) &&
            !(version >= 7 && result.entry_slot == 2) &&
            !(version >= 15 && result.entry_slot == 5) &&
            !(version >= 10 && (result.entry_slot == 0 || result.entry_slot == 6 || result.entry_slot == 7))) return 0;
        if (result.mode == BTP_BUILDING && v->status != BTP_SCRIPT_MENU && v->status != BTP_SCRIPT_WAIT &&
            v->status != BTP_SCRIPT_NATIVE && v->status != BTP_SCRIPT_CONFIRM && v->status != BTP_SCRIPT_ANIMATION && v->status!=BTP_SCRIPT_RECRUIT &&
            !(version>=28 && v->status==BTP_SCRIPT_EFFECT)) return 0;
        if ((result.mode == BTP_SCRIPT_FAULT) != (v->status == BTP_SCRIPT_ERROR) ||
            (v->status == BTP_SCRIPT_ERROR) != (v->error != 0)) return 0;
        if ((result.mode == BTP_EXPLORE || result.mode == BTP_ENTRY) &&
            v->status != BTP_SCRIPT_RUNNING && v->status != BTP_SCRIPT_END) return 0;
        if (v->pc || v->text_offset || v->text_length || v->text_count || v->status != BTP_SCRIPT_RUNNING) {
            if (!script || script->length > BTP_BLD_MAX || v->pc > script->length || v->fault_pc > script->length) return 0;
            uint8_t text[BTP_BLD_MAX + 1];
            if (!btp_script_text(v, script, text, sizeof text)) return 0;
            if (v->status == BTP_SCRIPT_NATIVE && (v->pc < 2 || script->bytes[v->pc-2] != 0xf5 ||
                script->bytes[v->pc-1] != v->native_action || v->pause_units ||
                (v->native_action == 12 ? v->text_count != 0 :
                    version < 7 || (v->native_action != 7 && v->native_action != 8 &&
                        !(version >= 10 && v->native_action == 1 && result.mode == BTP_MISSION) &&
                        !(version>=18 && v->native_action==30 && (result.mode==BTP_ENCOUNTER || result.mode==BTP_GAME_OVER)) &&
                        !(version>=26 && (v->native_action==39 || v->native_action==46 || (version>=29 && v->native_action==27)) && result.menu.from_story) &&
                        !(version>=29 && result.yard.active && (v->native_action==33 || v->native_action==34 || v->native_action==35 || v->native_action==40)) &&
                        !(version>=27 && v->native_action==45 && result.cache.active && result.campaign.building==22 && result.cache.phase==BTP_CACHE_PHOENIX) &&
                        !(version>=18 && result.service.phase))))) return 0;
            if (v->status == BTP_SCRIPT_ANIMATION && (version < 12 || v->pc < 3 ||
                script->bytes[v->pc-3] != 0xea || script->bytes[v->pc-2] != v->animation_kind ||
                script->bytes[v->pc-1] != v->animation_flags || v->pause_units)) return 0;
            if (v->status==BTP_SCRIPT_EFFECT && (version<28 || result.mode!=BTP_BUILDING || v->pc<2 ||
                script->bytes[v->pc-2]!=0xe4 || !script->bytes[v->pc-1] || script->bytes[v->pc-1]>18 ||
                (v->money_amount && v->money_amount!=script->bytes[v->pc-1]) || v->pause_units)) return 0;
            if (v->status==BTP_SCRIPT_RECRUIT && (version<18 || v->pc<2 || script->bytes[v->pc-2]!=0xe9 || script->bytes[v->pc-1]!=result.service.kind || result.service.phase!=8)) return 0;
            if (v->status == BTP_SCRIPT_CONFIRM && (v->pc < 3 || script->bytes[v->pc-3] != 0xf6 ||
                v->confirm_target != get16(script->bytes+v->pc-2) || v->confirm_target >= script->length)) return 0;
            unsigned count = btp_menu_count(v->menu_id);
            if (v->status == BTP_SCRIPT_MENU && (!count || v->selected >= count ||
                v->menu_table < 2 || v->menu_table > script->length || (unsigned)(script->length - v->menu_table) < 2*count ||
                script->bytes[v->menu_table-2] != 0xf9 || script->bytes[v->menu_table-1] != v->menu_id ||
                v->pc != v->menu_table+2*count || v->selected != v->choices[v->menu_id])) return 0;
            if (v->status == BTP_SCRIPT_MENU)
                for (unsigned i = 0; i < count; ++i)
                    if (get16(script->bytes + v->menu_table + 2*i) >= script->length) return 0;
        }
        if (version<30 && result.campaign.invasion && result.combat.phase) {
            /* v29's invasion used a cropped town frame. Translate its live
               positions and goals into the padded world frame; paths are deltas. */
            BtpCombatState *c=&result.combat;result.x_half+=64;result.y_half+=64;
            result.campaign.battle_x=result.campaign.battle_y=1472;
            for (unsigned i=0;i<c->count;++i) { c->unit[i].x+=64;c->unit[i].y+=64; }
            if (c->goal_active || c->goal_x || c->goal_y) { c->goal_x+=64;c->goal_y+=64; }
            if (c->cursor_x || c->cursor_y || c->phase==BTP_COMBAT_MOVE) { c->cursor_x+=64;c->cursor_y+=64; }
            for (unsigned i=0;i<c->waypoint_count;++i) { c->waypoint_x[i]+=64;c->waypoint_y[i]+=64; }
            /* Saved per-actor orders use that same old coordinate frame,
               including a computer pilot's remembered destination. */
            for (unsigned i=0;i<c->count;++i) {
                BtpCombatPlan *p=&c->plans[i];
                if (p->active || p->x || p->y) { p->x+=64;p->y+=64; }
                for (unsigned j=0;j<p->count && j<11;++j) { p->wx[j]+=64;p->wy[j]+=64; }
            }
            for (unsigned i=0;i<result.effects.count;++i) { BtpCombatEffect *e=&result.effects.shots[i];e->x+=64;e->y+=64;e->tx+=64;e->ty+=64; }
        }
        if (version<32 && result.combat.phase) {
            BtpCombatState *c=&result.combat;
            if (c->phase>BTP_COMBAT_SPY || c->selected>9 || !c->count ||
                c->active_unit>=c->count || c->scan_unit>=c->count) return 0;
            /* Older Scan opened the mech diagram immediately. Preserve that
               paused view; on-foot scans become the original summary menu. */
            if (c->phase==BTP_COMBAT_SCAN) {
                c->phase=(uint8_t)(c->unit[c->scan_unit].infantry ? BTP_COMBAT_SCAN : BTP_COMBAT_SCAN_DETAIL);
                c->target_selected=(uint8_t)(c->scan_unit>=(c->friends ? c->friends : 1u));c->selected=0;
            }
            if (c->phase==BTP_COMBAT_MENU)
                c->selected=(uint8_t)btp_combat_menu_command(c,btp_combat_menu_row(c));
        }
        if (version<36 && result.combat.notice>19) return 0;
        if (version<35 && result.combat.phase) {
            BtpCombatState *c=&result.combat;
            if (c->phase>BTP_COMBAT_SCAN_DETAIL || c->notice>17 || c->active_unit>=BTP_COMBAT_UNITS) return 0;
            /* Old versions put infantry into a one-weapon list. Preserve
               its pending choice using the original direct target selector. */
            if (c->phase==BTP_COMBAT_WEAPONS && c->unit[c->active_unit].infantry) {
                c->phase=(uint8_t)(c->weapon_selected ? BTP_COMBAT_MENU : BTP_COMBAT_TARGET);
                c->selected=3;c->target_selected=2;
            }
        }
        if (version<33 && result.service.phase) btp_service_upgrade(&result);
        if (result.disk_origin && ((result.disk_origin!=8 && result.disk_origin!=19) || result.mode!=BTP_BUILDING || !result.checkpoint_valid || result.campaign.building!=result.disk_origin)) return 0;
        if (!btp_talk_valid(&result,m) || !btp_npc_valid(&result,m) || !btp_bank_valid(&result) ||
            !btp_school_valid(&result) || !btp_training_valid(&result) || !btp_cutscene_valid(&result) || !btp_combat_valid(&result) || !btp_effects_valid(&result) || !btp_service_valid(&result) ||
            (result.presentation.count && result.combat.phase!=BTP_COMBAT_ROUND) || !btp_cache_valid(&result) || !btp_yard_valid(&result)) return 0;
        if (result.technician>4 || result.apprentice>1 || result.checkpoint_technician>4 ||
            result.checkpoint_apprentice>1 || (result.apprentice && !result.technician)) return 0;
    }
    if (version >= 9) {
        result.player_walk = b[394]; memcpy(result.npc_walk,b+395,8);
        if (result.player_walk > 15) return 0;
        for (unsigned i = 0; i < 8; ++i) if (result.npc_walk[i] > 15) return 0;
    } else {
        result.player_walk = btp_walk_first(btp_player_direction(result.facing));
        if (result.npc.enabled == 2) for (unsigned i = 0; i < 8; ++i)
            result.npc_walk[i] = btp_walk_first(result.npc.actor[i].direction);
    }
    if (version == 1) result.story_flags[51] = (uint8_t)result.allowance_cap;
    if (version<25) {
        if (version>=18) for (unsigned i=10234;i<10240;++i) if (b[i]) return 0;
        unsigned ui=result.campaign.ui;
        if (result.party.enabled && (ui==BTP_MENU_PERSON || ui==BTP_MENU_EQUIPMENT || ui==BTP_MENU_HEAL || ui==BTP_MENU_ALLOCATE || ui==BTP_MENU_RECIPIENT)) {
            unsigned slot=result.campaign.selected,count=btp_party_count(&result.party);
            unsigned ordinal=slot==8 ? count : btp_party_ordinal(&result.party,slot);
            if (ordinal>=count && ui!=BTP_MENU_ALLOCATE && ui!=BTP_MENU_RECIPIENT) ordinal=0;
            result.campaign.selected=(uint8_t)ordinal;
        }
        if (result.service.phase==7) result.service.selected=(uint8_t)btp_party_ordinal(&result.party,result.service.selected);
        if (result.original.valid) memcpy(result.explored,result.original.bytes+0x4f9,sizeof result.explored);
        else {
            for (unsigned row=98;row<=103;++row) result.explored[row*16u+12u]=31;
            btp_world_reveal(&result);
        }
    }
    if (version>=41 && version<=42 && result.campaign.ui>=BTP_MENU_BROKER &&
        result.campaign.ui<=BTP_MENU_BROKER_RESULT) {
        /* v41/42 stored a seven-model page number. v43 stores the first row
           of a scrolling window. Preserve the selected model, including an
           old page's Back choice, before checking the new menu invariants. */
        unsigned total=result.menu.map_x,first=7u*result.campaign.member;
        if (!total || total>BTP_ROSTER_MAX || first>=total || result.menu.map_y>=total) return 0;
        unsigned rows=total-first;if (rows>7) rows=7;
        unsigned selected=result.campaign.selected;
        if (result.campaign.ui==BTP_MENU_BROKER && selected>rows) return 0;
        unsigned item=result.campaign.ui==BTP_MENU_BROKER ?
            (selected==rows ? total : first+selected) : result.menu.map_y;
        result.campaign.member=0;btp_broker_select(&result,item);
        if (result.campaign.ui!=BTP_MENU_BROKER) result.campaign.selected=(uint8_t)selected;
    }
    if (!btp_actions_valid(&result) || !btp_audio_valid(&result) || !btp_aftermath_valid(&result)) return 0;
    if (version==41) {
        /* Existing Updated games keep their purchases and pending choices.
           Retire the old Space entry; held broker pages become the native
           building screen and return to the same outdoor position on exit. */
        if (result.campaign.ui==BTP_MENU_UPDATED_ROOT) {
            result.campaign.ui=BTP_MENU_ROOT;
            if (result.campaign.selected>=btp_actions_count(&result)) result.campaign.selected=0;
        } else if (btp_broker_page(result.campaign.ui)) {
            result.campaign.building=BTP_BROKER_BUILDING;result.entry_slot=BTP_BROKER_ENTRY;
            result.script=(BtpScriptState){0};
        }
    }
    *s = result;
    return 1;
}

