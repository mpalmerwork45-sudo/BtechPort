#include "core/original_actions.h"
#include "core/game.h"
#include "core/talk.h"
#include "core/npc.h"
#include "core/shop.h"
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
#include <string.h>

const BtpCombatProfile *btp_active_combat_profile(const BtpState *s,const BtpResources *r)
{
    return s->combat_profile==1 && r->roster.count && r->combat_profile.fingerprint &&
        s->combat_fingerprint==r->combat_profile.fingerprint ? &r->combat_profile : NULL;
}
int btp_set_combat_profile(BtpState *s,const BtpResources *r,unsigned enhanced)
{
    /* Never change the rules underneath a held encounter or scripted fight. */
    if (enhanced>1 || !r->roster.count || (enhanced && !r->combat_profile.fingerprint) ||
        s->combat.phase!=BTP_COMBAT_NONE || s->campaign.encounter ||
        (s->mode!=BTP_EXPLORE && s->mode!=BTP_ACTIONS && s->mode!=BTP_CACHE)) return 0;
    s->combat_profile=(uint8_t)enhanced;s->combat_fingerprint=enhanced ? r->combat_profile.fingerprint : 0;
    return 1;
}
void btp_start(BtpState *s)
{
    *s = (BtpState){.x_half = 69, .y_half = 25, .map_id = 1, .gate = 85,
        .credits=35,.allowance_cap=50,.menu={.steps=1,.sound=1,.speed=2,.outtakes=0}};
    static const uint8_t packed[8] = {99,81,53,99,18,4,4,70};
    for (unsigned i = 0; i < 8; ++i) s->npc_pairs[i][0] = packed[i];
    s->npc = (BtpNpcState){.enabled=1,.phase=1,.rng={31,66,171},.search=99,
        .loop_timer=249,.allowance_pending=1};
    /* Fresh first-time DOS snapshot: the familiar Citadel area is known.
       Other landscape cells are discovered by the original movement masks. */
    for (unsigned row=98;row<=103;++row) s->explored[row*16u+12u]=31;
    s->story_flags[51] = 50;btp_world_reveal(s);
}
const BtpMap *btp_active_map(const BtpResources *r,const BtpState *s)
{
    if (s->cache.active && s->story_flags[66]) return &r->maproom;
    /* Original 103B:0FC0 switches maps after the third invasion message,
       while TRAINING.BLD is still suspended in its combat native call. */
    if (s->campaign.invasion && s->late.invasion_event>=3) return &r->destroyed;
    return s->map_id==11 ? &r->destroyed : s->map_id>=2 && s->map_id<=14 ? &r->local[s->map_id-1] : &r->map;
}
unsigned btp_building_kind(const BtpResources *r,const BtpState *s)
{
    if (r->roster.count && s->map_id==2 && s->entry_slot==BTP_BROKER_ENTRY &&
        s->campaign.building==BTP_BROKER_BUILDING) return BTP_BROKER_BUILDING;
    if (s->disk_origin) return 18;
    if (s->cache.active || s->yard.active) return s->campaign.building;
    return !s->map_id ? s->campaign.building : s->map_id==1 ? s->entry_slot :
        btp_active_map(r,s)->room_map[s->entry_slot&15u];
}
const BtpBld *btp_state_bld(const BtpResources *r,const BtpState *s)
{
    unsigned kind=btp_building_kind(r,s);
    return kind<8 ? btp_building_bld(r,kind) : kind<26 ? &r->buildings[kind] : NULL;
}

void btp_tick(BtpState *s, const BtpMap *m, BtpAction a)
{
    ++s->tick; /* Explicit unsigned wrapping; no clock or graphics dependency. */
    if (!btp_action_moves(a)) return;
    s->player_walk = btp_walk_next(s->player_walk,btp_player_direction(s->facing),btp_player_direction((unsigned)a));
    s->facing = (uint8_t)a;
    int x = s->x_half + btp_action_dx(a), y = s->y_half + btp_action_dy(a);
    if (x < 0 || y < 0 || x >= 2 * m->width || y >= 2 * m->height) {
        s->blocked = BTP_EDGE;
        return;
    }
    /* The reference trace includes x=68 -> 67 (free) -> 66 (blocked).
       Collision samples the player's offset position, not the cursor's tile:
       ceil(x_half/2), floor(y_half/2). Multi-unit footprints are deferred. */
    int tile_x = (x + 1) / 2, tile_y = y / 2;
    if (tile_x >= m->width) { s->blocked = BTP_EDGE; return; }
    if (btp_map_tile(m, tile_x, tile_y) >= s->gate) {
        s->blocked = BTP_WALL;
        return;
    }
    s->x_half = (uint16_t)x; s->y_half = (uint16_t)y; s->blocked = BTP_CLEAR;
}

int btp_entrance(const BtpState *s, const BtpMap *m)
{
    for (int i = 0; i < 16; ++i)
        if (m->entrance_x[i] && m->entrance_y[i] && s->x_half == (m->entrance_x[i] & 127) &&
            s->y_half == (m->entrance_y[i] & 127) + (s->campaign.mounted ? 2u : 0u)) return i;
    return -1;
}
const BtpBld *btp_building_bld(const BtpResources *r, unsigned slot)
{
    return !r ? NULL : slot == 0 ? &r->training : slot == 1 ? &r->citadel : slot == 2 ? &r->comstar :
        slot == 3 ? &r->weapon : slot == 4 ? &r->armor : slot == 5 ? &r->repair : slot == 6 ? &r->barracks : slot == 7 ? &r->lounge : NULL;
}
static void story_in(BtpState *s)
{
    s->story_flags[45] = s->recruitment; s->story_flags[46] = s->talk_result;
    s->story_flags[51] = (uint8_t)s->allowance_cap;
    s->story_flags[52] = (uint8_t)(s->allowance_cap>>8);
}
static void story_out(BtpState *s)
{
    s->recruitment = s->story_flags[45]; s->talk_result = s->story_flags[46];
    s->allowance_cap = (uint16_t)(s->story_flags[51]|(unsigned)s->story_flags[52]<<8);
    if (s->npc.enabled) s->npc.allowance_pending = (uint8_t)btp_economy_below_cap(s);
}
static void start_building(BtpState *s, const BtpResources *r)
{
    uint8_t choices[BTP_MENUS]; memcpy(choices,s->script.choices,sizeof choices);
    btp_script_start(&s->script,btp_state_bld(r,s),s->story_flags);
    memcpy(s->script.choices,choices,sizeof choices);
    if (s->script.status == BTP_SCRIPT_MENU) s->script.selected = choices[s->script.menu_id];
}

static void finish_script(BtpState *s, const BtpResources *r, const BtpMap *m)
{
    unsigned invasion=s->campaign.invasion;
    unsigned status=s->script.status;
    story_out(s);
    if (s->script.status == BTP_SCRIPT_ERROR) {
        /* Prototype recovery: roll back the entire failed menu choice,
           including writes before a dialogue pause, not an original rule. */
        if (s->checkpoint_valid) {
            memcpy(s->story_flags, s->story_checkpoint, BTP_STORY_BYTES);
            s->talk_result = s->checkpoint_talk_result;
            s->credits = s->checkpoint_credits; s->weapon = s->checkpoint_weapon;
            s->allowance_cap = s->checkpoint_allowance_cap;
            s->recruitment = s->story_flags[45];
            memcpy(s->investments,s->checkpoint_investments,sizeof s->investments);
            memcpy(s->skills,s->checkpoint_skills,sizeof s->skills);
            memcpy(s->mech_skills,s->checkpoint_mech_skills,sizeof s->mech_skills);
            s->technician=s->checkpoint_technician;s->apprentice=s->checkpoint_apprentice;
            s->armor = s->checkpoint_armor; s->armor_points = s->checkpoint_armor_points;
            s->campaign.owned=s->campaign.checkpoint_owned;
            memcpy(s->campaign.mech,s->campaign.checkpoint_mech,125);
            s->party=s->party_checkpoint;
            if (s->npc.enabled) s->npc.allowance_pending = (uint8_t)btp_economy_below_cap(s);
        }
        s->bank = (BtpBankState){0};
        s->service=(BtpServiceState){0};
        s->school = (BtpSchoolState){0};
        s->script.has_accounts = 0;
        s->mission = (BtpMissionState){0};
        s->combat = (BtpCombatState){0};
        s->cutscene = (BtpCutsceneState){0};
        s->mode = BTP_SCRIPT_FAULT;
    } else if (s->script.status == BTP_SCRIPT_END) {
        unsigned kind=btp_building_kind(r,s);
        if (!s->disk_origin && btp_party_count(&s->party)>1 &&
            (kind==19 || (kind==8 && s->story_flags[48] && !s->story_flags[50]))) {
            /* Executed 07DC:00C3..015D chains VIEWDISK after the ruined
               barracks, or garage when a purchased viewer is available. */
            s->disk_origin=(uint8_t)kind;
            btp_script_start(&s->script,&r->buildings[18],s->story_flags);
            btp_original_checkpoint(s);return;
        }
        unsigned disk_finished=s->disk_origin;
        if (s->campaign.invasion) {
            /* Armour/services may have initialized the party during cadet
               training. Register the invasion's retained loan in that
               existing garage too, before any encounter or checkout. */
            if (s->party.enabled && s->campaign.owned) {
                s->party.mech_types[0]=s->campaign.mech[0];
                s->party.people[0][12]=0;s->campaign.mounted=1;
            }
            s->campaign.invasion=0;s->map_id=11;
            s->late.invasion_event=s->late.invasion_popup=s->late.invasion_end=0;
            s->mission=(BtpMissionState){0};s->combat=(BtpCombatState){0};
            s->effects=(BtpEffectsState){0};
            s->npc=(BtpNpcState){.rng={s->npc.rng[0],s->npc.rng[1],s->npc.rng[2]}};
            s->campaign.building=0;
            s->script=(BtpScriptState){0};
            if (s->campaign.world_y<1536 || s->campaign.world_x<1536 || s->campaign.world_y>=1664 || s->campaign.world_x>=1664) {
                s->map_id=0;s->x_half=s->campaign.world_x;s->y_half=s->campaign.world_y;
            }
        }
        /* The original commits the pending outdoor step after FF. */
        if (!invasion && !s->cache.active && s->map_id && !s->script.position_x && (s->map_id!=1 || s->entry_slot || s->script.native_action != 3)) {
            if (s->story_flags[4] && s->party.enabled) {
                /* An outer member may have opened this door. Keep the party
                   cursor and commit only the original pending legal step. */
                btp_world_step(s,r,(BtpAction)s->entry_action);
            } else {
                s->x_half = m->entrance_x[s->entry_slot] & 127;
                s->y_half = (uint16_t)((m->entrance_y[s->entry_slot] & 127) + (s->campaign.mounted ? 2u : 0u));
            }
        }
        s->mode = (uint8_t)(s->party.enabled && s->party.people[0][0]==255 ? BTP_GAME_OVER : BTP_EXPLORE);
        /* Scripted allocation can put Jason in any owned bay or passenger
           seat. Do not overwrite that choice with a slot-zero pilot check. */
        if (!invasion && !s->cache.active && s->story_flags[4]) {
            unsigned bay=s->party.people[0][12];
            s->campaign.mounted=(uint8_t)(s->campaign.owned && !s->story_flags[24] && bay<4 && btp_party_mech(s,bay)[0]!=255);
        }
        s->bank = (BtpBankState){0};
        s->school = (BtpSchoolState){0};
        s->script.has_accounts = 0;
        if (disk_finished) { s->disk_origin=0;s->script=(BtpScriptState){0}; }
    }
    if (status == BTP_SCRIPT_ERROR || status == BTP_SCRIPT_MENU || status == BTP_SCRIPT_END) {
        s->checkpoint_valid = 0; memset(s->story_checkpoint, 0, BTP_STORY_BYTES);
        s->checkpoint_talk_result = 0;
        s->checkpoint_credits = 0;
        s->checkpoint_allowance_cap = 0;
        memset(s->checkpoint_investments,0,sizeof s->checkpoint_investments);
        memset(s->checkpoint_skills,0,sizeof s->checkpoint_skills);
        memset(s->checkpoint_mech_skills,0,sizeof s->checkpoint_mech_skills);
        s->checkpoint_technician=s->checkpoint_apprentice=0;
        s->campaign.checkpoint_owned=0;memset(s->campaign.checkpoint_mech,0,125);
        s->party_checkpoint=(BtpPartyState){0};
        s->checkpoint_weapon = s->checkpoint_armor = s->checkpoint_armor_points = 0;
    }
    if (status==BTP_SCRIPT_END) btp_cache_script_end(s,r);
}
void btp_game_building(BtpState *s,const BtpResources *r,unsigned kind)
{
    s->mode=BTP_BUILDING;s->campaign.building=(uint8_t)kind;btp_original_checkpoint(s);
    start_building(s,r);
    if (s->script.status==BTP_SCRIPT_ANIMATION) {
        (void)btp_rng_next(s->npc.rng);
        if (!btp_cutscene_begin(s,r,s->script.animation_kind,1)) {
            s->script.status=BTP_SCRIPT_ERROR;s->script.error=BTP_SCRIPT_NATIVE_CONTEXT;
        }
    }
    finish_script(s,r,btp_active_map(r,s));
}
static void game_tick(BtpState *s, const BtpResources *r, BtpAction a)
{
    const BtpMap *map=btp_active_map(r,s);
    story_in(s);
    if (s->mode==BTP_GAME_OVER || s->mode==BTP_ENDING) {
        ++s->tick;
        /* Older saves can contain the formerly inert completed screen. */
        if (s->mode==BTP_ENDING && a!=BTP_IDLE) s->menu.quit=1;
        return;
    }
    if (s->mode==BTP_CACHE) { btp_cache_input(s,r,a);return; }
    if (s->mode==BTP_YARD) {
        ++s->tick;btp_yard_input(s,r,a);
        if (s->mode==BTP_BUILDING) { finish_script(s,r,map);if (s->script.status==BTP_SCRIPT_NATIVE || s->script.status>=BTP_SCRIPT_MONEY) goto services; }
        return;
    }
    if (s->mode==BTP_ENCOUNTER) {
        ++s->tick;if (s->aftermath.phase) btp_aftermath_input(s,r,a);else btp_combat_tick(s,r,a);
        btp_campaign_result(s,r);
        if (s->mode==BTP_BUILDING) {
            finish_script(s,r,map);
            /* Arena wins immediately award BLD money; theft epilogues can
               enter crew allocation. Finish either pending operation before
               exposing the returned page or allowing a save. */
            if (s->script.status==BTP_SCRIPT_NATIVE || s->script.status>=BTP_SCRIPT_MONEY) goto services;
        }
        return;
    }
    if (s->mode==BTP_ACTIONS) {
        btp_world_actions(s,r,a);
        if (s->mode==BTP_BUILDING && s->menu.from_story==2) goto services;
        return;
    }
    if (s->mode == BTP_EXPLORE) {
        if (a==BTP_OPEN_MENU || (s->story_flags[4] && a==BTP_ACCEPT)) {
            ++s->tick;btp_menu_open(s);
            return;
        }
        if (s->npc.fault) { ++s->tick; return; }
        BtpState moved = *s;
        unsigned steps=btp_action_moves(a) && !s->story_flags[66] ? s->menu.steps : 1u;
        for (unsigned step=0;step<steps;++step) {
        BtpState previous=moved;moved.tick=s->tick;
        if (s->story_flags[4] && steps==1) btp_world_move(&moved,r,a);
        else if (s->story_flags[4]) { ++moved.tick;btp_world_step(&moved,r,a); }
        else btp_tick(&moved,map,a);
        map=btp_active_map(r,&moved);
        int party_entry=s->story_flags[4] && previous.party.enabled && previous.map_id && moved.map_id==previous.map_id;
        int entrance = party_entry ? btp_party_entrance(&previous,r,map,
            (int)previous.x_half+btp_action_dx(a),(int)previous.y_half+btp_action_dy(a)) :
            moved.map_id ? btp_entrance(&moved,map) : -1;
        if (moved.mode==BTP_EXPLORE && btp_action_moves(a) && (party_entry || !moved.blocked) &&
            (party_entry || moved.x_half != previous.x_half || moved.y_half != previous.y_half) &&
            (moved.map_id==previous.map_id && entrance >= 0 &&
                ((r->roster.count && moved.map_id==2 && entrance==BTP_BROKER_ENTRY) || map->room_map[entrance]<26))) {
            moved.x_half = previous.x_half; moved.y_half = previous.y_half;
            if (party_entry) {
                moved.campaign.world_x=(uint16_t)((map->entrance_x[0]>>8)*128+previous.x_half);
                moved.campaign.world_y=(uint16_t)((map->entrance_y[0]>>12)*128+previous.y_half);
                moved.party=previous.party;
            }
            moved.mode = BTP_ENTRY; moved.entry_slot = (uint8_t)entrance; moved.entry_selected = 0;
            moved.entry_action = moved.facing;
            moved.campaign.building=(uint8_t)(r->roster.count && moved.map_id==2 && entrance==BTP_BROKER_ENTRY ?
                BTP_BROKER_BUILDING : moved.story_flags[4] ? map->room_map[entrance] : 0);
            uint8_t choices[BTP_MENUS]; memcpy(choices,moved.script.choices,sizeof choices);
            moved.script = (BtpScriptState){.selected=previous.script.selected};
            memcpy(moved.script.choices,choices,sizeof choices);
        }
        if (moved.mode!=BTP_EXPLORE || moved.blocked) break;
        }
        if (s->story_flags[4] && steps>1 && moved.mode==BTP_EXPLORE) btp_world_clock(&moved,r,a);
        if (btp_action_moves(a)) {
            if (moved.campaign.mounted) moved.campaign.mech_walk=(uint8_t)btp_combat_walk_frame(s->campaign.mech_walk,s->campaign.mech_direction,btp_player_direction((unsigned)a),0);
            moved.player_walk=btp_walk_next(s->player_walk,btp_player_direction(s->facing),btp_player_direction((unsigned)a));
            /* One key advances every formation sprite by one frame. In
               four-step mode four simulated moves would otherwise wrap the
               other pilots' gait back to its starting frame. */
            if (moved.campaign.world_x!=s->campaign.world_x || moved.campaign.world_y!=s->campaign.world_y) {
                for (unsigned i=1;i<8;++i) if (moved.party.people[i][0]!=255) {
                    unsigned mount=moved.party.people[i][12],direction=moved.party.direction[i];
                    if (mount>=8 && (moved.party.x[i]!=s->party.x[i] || moved.party.y[i]!=s->party.y[i]))
                        moved.party.walk[i]=btp_walk_next(s->party.walk[i],s->party.direction[i],direction);
                    else if (mount<4 && btp_party_mech(&moved,mount)[121]==i &&
                        (moved.party.mech_x[mount]!=s->party.mech_x[mount] || moved.party.mech_y[mount]!=s->party.mech_y[mount]))
                        moved.party.walk[i]=(uint8_t)btp_combat_walk_frame(s->party.walk[i],s->party.direction[i],direction,0);
                }
            }
        }
        *s = moved;btp_world_reveal(s);
        if (s->mode == BTP_EXPLORE && !s->story_flags[4]) btp_npc_input(s,&r->map,a);
        return;
    }
    ++s->tick;
    if (s->service.phase==8) {
        btp_service_input(s,r,a);finish_script(s,r,map);
        if (s->mode==BTP_BUILDING && (s->script.status==BTP_SCRIPT_NATIVE || s->script.status>=BTP_SCRIPT_MONEY)) goto services;
        return;
    }
    if (s->cutscene.active) {
        unsigned active = s->cutscene.active;
        if (btp_cutscene_tick(s,r) && active == 1) {
            btp_script_animation_return(&s->script,btp_state_bld(r,s),s->story_flags);
            finish_script(s,r,map);
            /* THEATER chains films directly. Begin the next EA in this same
               tick so there is no unsaveable ANIMATION-without-frames gap. */
            if (s->mode==BTP_BUILDING && (s->script.status==BTP_SCRIPT_NATIVE || s->script.status>=BTP_SCRIPT_MONEY ||
                s->script.status==BTP_SCRIPT_ANIMATION)) goto services;
        }
        return;
    }
    if (s->mode == BTP_QUIZ) {
        int result = btp_quiz_tick(s,a);
        if (result == 1) { s->mode = BTP_BUILDING; start_building(s,r); finish_script(s,r,map); }
        if (result == 2) {
            s->mode = BTP_EXPLORE; s->x_half = r->map.entrance_x[0]&127; s->y_half = r->map.entrance_y[0]&127;
        }
        return;
    }
    if (s->mode == BTP_MISSION) {
        if (!btp_mission_tick(s,r,a)) return;
        btp_script_native_return(&s->script,&r->training,s->story_flags);
        if (s->script.status == BTP_SCRIPT_NATIVE && s->script.native_action == 2) btp_training_native(s,r);
        if (s->script.status==BTP_SCRIPT_ANIMATION) {
            (void)btp_rng_next(s->npc.rng);
            if (!btp_cutscene_begin(s,r,s->script.animation_kind,1)) {
                s->script.status=BTP_SCRIPT_ERROR;s->script.error=BTP_SCRIPT_NATIVE_CONTEXT;
            }
        }
        finish_script(s,r,map); return;
    }
    if (s->mode == BTP_ENTRY) {
        if (a == BTP_LEFT || a == BTP_UP) s->entry_selected = 0;
        if (a == BTP_RIGHT || a == BTP_DOWN) s->entry_selected = 1;
        if (a == BTP_CANCEL || (a == BTP_ACCEPT && s->entry_selected)) {
            if (s->story_flags[4] && s->party.enabled) btp_world_step(s,r,(BtpAction)s->entry_action);
            else {
                s->x_half = map->entrance_x[s->entry_slot] & 127;
                s->y_half = (uint16_t)((map->entrance_y[s->entry_slot] & 127) + (s->campaign.mounted ? 2u : 0u));
            }
        s->mode = (uint8_t)(s->party.enabled && s->party.people[0][0]==255 ? BTP_GAME_OVER : BTP_EXPLORE);
            /* Declining the added doorway leaves no native building context
               behind in an otherwise ordinary exploration save. */
            if (s->campaign.building==BTP_BROKER_BUILDING) {
                s->campaign.building=0;s->entry_slot=0;s->script=(BtpScriptState){0};
            }
        } else if (a == BTP_ACCEPT) {
            if (btp_building_kind(r,s)==BTP_BROKER_BUILDING) { btp_broker_open(s);return; }
            s->story_flags[10] = 1;
            /* Entering a shop changes the scene, not the stored crew seats.
               Clearing mounted here made the end-of-tick party sync eject
               Jason. Parking and theft scripts handle actual disembarking. */
            if (!btp_building_kind(r,s) && !s->story_flags[20]) { btp_quiz_begin(s); return; }
            s->mode = BTP_BUILDING;
            if (s->story_flags[4]) btp_original_checkpoint(s);
            start_building(s,r);
            finish_script(s,r,map);
            if (s->mode==BTP_BUILDING && (s->script.status==BTP_SCRIPT_NATIVE || s->script.status>=BTP_SCRIPT_MONEY)) goto services;
        }
        return;
    }
    if (s->mode == BTP_SCRIPT_FAULT) {
        if (a == BTP_CANCEL) {
            /* Explicit prototype recovery; finish_script rolled back the choice. */
            start_building(s,r); s->mode = BTP_BUILDING;
            finish_script(s,r,map);
        }
        return;
    }
    if (s->script.status == BTP_SCRIPT_MENU) {
        unsigned count = btp_menu_count(s->script.menu_id);
        if (a == BTP_UP && count) s->script.selected = (uint8_t)((s->script.selected + count-1) % count);
        if (a == BTP_DOWN && count) s->script.selected = (uint8_t)((s->script.selected + 1u) % count);
        s->script.choices[s->script.menu_id] = s->script.selected;
        if (a == BTP_ACCEPT) {
            btp_original_checkpoint(s);
            s->school = (BtpSchoolState){0};
            (void)btp_script_choose(&s->script, btp_state_bld(r,s), s->script.selected, s->story_flags);
        }
    } else if (s->script.status == BTP_SCRIPT_WAIT && a == BTP_ACCEPT) {
        s->bank = (BtpBankState){0};
        s->school = (BtpSchoolState){0};
        btp_script_resume(&s->script, btp_state_bld(r,s), s->story_flags);
    }
    else if (s->script.status == BTP_SCRIPT_CONFIRM) {
        if (a == BTP_LEFT || a == BTP_UP) s->script.confirm_selected = 0;
        if (a == BTP_RIGHT || a == BTP_DOWN) s->script.confirm_selected = 1;
        if (a == BTP_ACCEPT) {
            if (!s->checkpoint_valid) btp_original_checkpoint(s);
            btp_script_confirm(&s->script,btp_state_bld(r,s),!s->script.confirm_selected,s->story_flags);
        }
    }
    else if (s->script.status == BTP_SCRIPT_NATIVE) btp_original_native_input(s,r,a);
services:
    btp_original_services(s,r);
    if (s->script.status == BTP_SCRIPT_ANIMATION) {
        (void)btp_rng_next(s->npc.rng);
        if (!btp_cutscene_begin(s,r,s->script.animation_kind,1)) {
            s->script.status = BTP_SCRIPT_ERROR; s->script.error = BTP_SCRIPT_NATIVE_CONTEXT;
            s->script.fault_pc = (uint16_t)(s->script.pc-3);
        }
    }
    if (s->script.has_position) {
        s->campaign.world_x=(uint16_t)((s->script.position_x>>8)*128+(s->script.position_x&127u));
        s->campaign.world_y=(uint16_t)((s->script.position_y>>12)*128+(s->script.position_y&127u));
        s->x_half=s->script.position_x&127u;s->y_half=s->script.position_y&127u;s->script.has_position=0;
    }
    finish_script(s,r,map);
}
void btp_game_tick_audio(BtpState *s,const BtpResources *r,BtpAction a,int16_t *samples)
{
    /* 0000:218F prints the direction for each exploration key. Keep the
       ten visible lines independent of the renderer and movement step size. */
    if (btp_action_moves(a) && !s->combat.phase &&
        (s->mode==BTP_EXPLORE || s->mode==BTP_CACHE || (s->mode==BTP_YARD && s->yard.phase==BTP_YARD_WALK) ||
         (s->mode==BTP_MISSION && s->mission.phase==BTP_MISSION_DRIVE))) {
        memmove(s->late.travel,s->late.travel+1,9);s->late.travel[9]=(uint8_t)(1u+btp_player_direction((unsigned)a));
    }
    if (a==BTP_CREDIT_10000) {
        ++s->tick;s->credits+=10000;
        if (s->checkpoint_valid) s->checkpoint_credits+=10000;
        if (s->script.has_cash) s->script.cash_value=s->credits;
        if (s->bank.phase==BTP_BANK_AMOUNT && s->script.native_action==7) s->bank.available=s->credits;
        if (s->npc.enabled) s->npc.allowance_pending=(uint8_t)btp_economy_below_cap(s);
        btp_audio_samples(&s->audio,r,BTP_AUDIO_TICK_SAMPLES,samples);return;
    }
    if (s->mode==BTP_LOGO) {
        ++s->tick;
        if (a==BTP_ACCEPT || a==BTP_OPEN_MENU) btp_audio_start(s);
        if (samples) memset(samples,0,BTP_AUDIO_TICK_SAMPLES*sizeof *samples);
        return;
    }
    if (s->mode==BTP_BEGIN) {
        ++s->tick;
        if (a==BTP_UP || a==BTP_DOWN || a==BTP_LEFT || a==BTP_RIGHT) s->entry_selected^=1u;
        if (a==BTP_ACCEPT || a==BTP_OPEN_MENU) {
            if (s->entry_selected) { s->mode=BTP_EXPLORE;s->entry_selected=0; }
            else { btp_menu_open(s);s->campaign.ui=BTP_MENU_LOAD;s->menu.from_intro=1; }
        }
        if (samples) memset(samples,0,BTP_AUDIO_TICK_SAMPLES*sizeof *samples);
        return;
    }
    if (s->mode==BTP_TITLE) {
        ++s->tick;
        if (a==BTP_ACCEPT || a==BTP_OPEN_MENU) { s->mode=BTP_BEGIN;s->entry_selected=1;s->audio=(BtpAudioState){0};if (samples) memset(samples,0,BTP_AUDIO_TICK_SAMPLES*sizeof *samples);return; }
        btp_audio_samples(&s->audio,r,BTP_AUDIO_TICK_SAMPLES,samples);
        if (!s->audio.active) { s->mode=BTP_BEGIN;s->entry_selected=1; }
        return;
    }
    unsigned previous_mode=s->mode;
    if (s->cutscene.active==3) {
        /* An outtake is still part of the current combat wave. Space must
           stop continuous play just as it does between animation frames. */
        if (a==BTP_OPEN_MENU) { s->combat.paused=1;s->combat.auto_run=0; }
        ++s->tick;btp_cutscene_tick(s,r);
    }
    else game_tick(s,r,a);
    /* Armour repair can initialise Jason's character record before the
       invasion. Keep his legacy training/shop aliases coherent from that
       point, rather than waiting for the destroyed-Citadel campaign flag. */
    if (!s->campaign.encounter && (s->story_flags[4] || s->party.enabled)) { btp_party_init(s);btp_party_sync(s); }
    /* Temporary stranded-follower recovery; party.c documents its removal
       plan. Run only after scene return, or a follower's distance limit. */
    btp_party_recover(s,r,previous_mode!=s->mode);
    btp_audio_samples(&s->audio,r,BTP_AUDIO_TICK_SAMPLES,samples);
}
void btp_game_tick(BtpState *s,const BtpResources *r,BtpAction a) { btp_game_tick_audio(s,r,a,NULL); }

const char *btp_action_name(BtpAction a)
{
    static const char *names[] = {"idle", "up", "down", "left", "right", "accept", "cancel",
        "0","1","2","3","4","5","6","7","8","9","clear","up-left","up-right","down-left","down-right","menu","credit-10000"};
    return a >= BTP_IDLE && a <= BTP_CREDIT_10000 ? names[a] : "invalid";
}
int btp_action_parse(const char *name, BtpAction *a)
{
    for (int i = BTP_IDLE; i <= BTP_CREDIT_10000; ++i)
        if (!strcmp(name, btp_action_name((BtpAction)i))) { *a = (BtpAction)i; return 1; }
    return 0;
}
int btp_action_moves(BtpAction a)
{
    return (a >= BTP_UP && a <= BTP_RIGHT) || (a >= BTP_UP_LEFT && a <= BTP_DOWN_RIGHT);
}
int btp_action_dx(BtpAction a)
{
    return (a == BTP_RIGHT || a == BTP_UP_RIGHT || a == BTP_DOWN_RIGHT) -
        (a == BTP_LEFT || a == BTP_UP_LEFT || a == BTP_DOWN_LEFT);
}
int btp_action_dy(BtpAction a)
{
    return (a == BTP_DOWN || a == BTP_DOWN_LEFT || a == BTP_DOWN_RIGHT) -
        (a == BTP_UP || a == BTP_UP_LEFT || a == BTP_UP_RIGHT);
}
const char *btp_mode_name(unsigned mode)
{
    static const char *names[] = {"local-exploration", "entry-confirm", "building", "script-error", "training-quiz", "training-mission","actions","encounter","title","game-over","logos","played-before","cache","ending","impound-yard"};
    return mode <= BTP_YARD ? names[mode] : "invalid";
}
