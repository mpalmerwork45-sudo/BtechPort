#include "core/training.h"
#include "core/npc.h"
#include "core/animation.h"
#include <string.h>

/* Numeric original DS:28C4/28D8/28EC tables, not a reference implementation. */
const uint16_t btp_quiz_x[10] = {151,230,240,221,239,248,213,217,193,157};
const uint16_t btp_quiz_y[10] = {186,189,168,120,88,55,69,26,38,95};
const uint8_t btp_quiz_answer[10] = {2,4,5,7,8,10,18,15,0,16};
const uint8_t btp_rubble_x[8] = {29,55,53,60,59,48,32,31};
const uint8_t btp_rubble_y[8] = {15,17,24,33,44,46,48,27};

void btp_quiz_begin(BtpState *s)
{
    uint8_t selected = s->quiz.selected;
    s->quiz = (BtpQuizState){.phase=BTP_QUIZ_INTRO,.selected=selected};
    s->mode = BTP_QUIZ;
}
static void next_question(BtpState *s)
{
    for (unsigned n = 0; n < 512; ++n) {
        unsigned point = btp_rng_next(s->npc.rng)%10u;
        if (s->quiz.used & (1u<<point)) continue;
        s->quiz.point = (uint8_t)point; s->quiz.used |= (uint16_t)(1u<<point);
        s->quiz.phase = BTP_QUIZ_QUESTION; return;
    }
    s->script.status = BTP_SCRIPT_ERROR; s->script.error = BTP_SCRIPT_BUDGET;
    s->mode = BTP_SCRIPT_FAULT;
}
int btp_quiz_tick(BtpState *s, BtpAction a)
{
    BtpQuizState *q = &s->quiz;
    if (q->phase == BTP_QUIZ_QUESTION) {
        if (a == BTP_UP) q->selected = (uint8_t)((q->selected+19u)%20u);
        if (a == BTP_DOWN) q->selected = (uint8_t)((q->selected+1u)%20u);
        if (a == BTP_ACCEPT) {
            if (q->selected != btp_quiz_answer[q->point]) q->failed = 1;
            if (++q->round == 3) {
                if (q->failed) { q->phase = BTP_QUIZ_FAILED; s->story_flags[20] = 255; }
                else { uint8_t selected = q->selected; *q = (BtpQuizState){.selected=selected}; return 1; }
            } else next_question(s);
        }
    } else if (a == BTP_ACCEPT) {
        if (q->phase == BTP_QUIZ_INTRO) next_question(s);
        else if (q->phase == BTP_QUIZ_FAILED) {
            uint8_t selected = q->selected; *q = (BtpQuizState){.selected=selected}; return 2;
        }
    }
    return 0;
}
static void fault(BtpState *s)
{
    s->script.status = BTP_SCRIPT_ERROR; s->script.error = BTP_SCRIPT_NATIVE_CONTEXT;
    s->script.fault_pc = s->script.pc >= 2 ? (uint16_t)(s->script.pc-2) : 0;
}
void btp_training_native(BtpState *s, const BtpResources *r)
{
    if (s->entry_slot || s->story_flags[4] || s->story_flags[2] > 2) { fault(s); return; }
    switch (s->script.native_action) {
    case 1:
        /* Two original noncombat assignments. Later cases require M3 combat. */
        if (s->story_flags[0] > 1 || s->mission.phase) { fault(s); return; }
        (void)btp_rng_next(s->npc.rng); /* Original O0 dispatcher, even forced. */
        s->mission = (BtpMissionState){.phase=BTP_MISSION_DRIVE,.walk=6,.direction=2,
            .assignment=s->story_flags[0]};
        if (s->mission.assignment) {
            s->mission.rubble = (uint8_t)(btp_rng_next(s->npc.rng)&7u);
            unsigned rubble = s->mission.rubble;
            s->mission.rubble_under = btp_map_tile(&r->map,btp_rubble_x[rubble],btp_rubble_y[rubble]);
            if (!s->story_flags[2]) s->mission.phase = BTP_MISSION_SNICKER;
        }
        s->x_half = 64; s->y_half = 79; s->blocked = 0; s->mode = BTP_MISSION;
        if (!btp_cutscene_begin(s,r,0,2)) { s->mission = (BtpMissionState){0}; fault(s); }
        return;
    case 2:
        if (s->mission.phase != BTP_MISSION_RESULT || !s->story_flags[1] ||
            s->mission.assignment || !s->script.text_count || s->script.mech_result) { fault(s); return; }
        s->script.mech_result = (uint8_t)(s->story_flags[2]+1u);
        s->script.mech_after = s->script.text_count;
        break;
    case 3:
        /* The tired-before-third refusal also exits through this routine. */
        if ((s->mission.phase != BTP_MISSION_RESULT && s->mission.phase != BTP_MISSION_NONE) ||
            s->script.pc != 0x1c6d) { fault(s); return; }
        s->mission = (BtpMissionState){0};
        s->script.mech_result = s->script.mech_after = 0;
        s->x_half = (uint16_t)(46 + btp_action_dx((BtpAction)s->entry_action));
        s->y_half = (uint16_t)(118 + btp_action_dy((BtpAction)s->entry_action));
        s->facing = s->entry_action;
        break;
    default: fault(s); return;
    }
    btp_script_native_return(&s->script,&r->training,s->story_flags);
}
uint8_t btp_mission_tile(const BtpState *s, const BtpMap *m, int x, int y)
{
    const BtpMissionState *mission = &s->mission;
    if (mission->phase && mission->phase != BTP_MISSION_RESULT) {
        if (!mission->assignment && x == 61 && y == 61) return 0;
        if (mission->assignment == 1 && mission->rubble < 8 &&
            x == btp_rubble_x[mission->rubble] && y == btp_rubble_y[mission->rubble])
            return mission->corner && s->story_flags[2] ? mission->rubble_under : 80;
    }
    return btp_map_tile(m,x,y);
}
uint8_t btp_mission_terrain(const BtpState *s, const BtpMap *m)
{
    /* Original mech slot 0 samples the feet at (ceil(x/2),floor(y/2)-1).
       DS:2E6 mask 1 becomes 4 on an odd half-row. Byte 32AE is a terrain
       obscuration flag here, not combat heat; the mission adds flag>>3. */
    unsigned tile = btp_mission_tile(s,m,(int)((s->x_half+1u)/2u),(int)(s->y_half/2u)-1);
    unsigned mask = (s->y_half & 1u) ? 4u : 1u;
    if (tile >= 48 || !(tile & mask)) return 0;
    return (uint8_t)(((tile & 15u) == 15 && ((tile & 48u) == 0 || (tile & 48u) == 32)) ? 16 : 8);
}
static void move(BtpState *s, const BtpMap *m, BtpAction a)
{
    unsigned direction = btp_player_direction((unsigned)a), before = s->mission.direction;
    /* Primary eight mech programs at image 280F0. Cardinal direction starts
       are N=0, E=6, S=8, W=15, with four-byte circular frame programs. */
    static const uint8_t frames[8][4] = {
        {0,1,2,3},{4,5,6,7},{6,7,4,5},{5,6,7,4},
        {8,9,10,11},{12,13,14,15},{15,12,13,14},{14,15,12,13}
    };
    unsigned next = 0;
    if (before == direction) for (unsigned i = 0; i < 4; ++i)
        if (frames[direction][i] == s->mission.walk) next = (i+1u)%4u;
    s->mission.walk = frames[direction][next]; s->mission.direction = (uint8_t)direction;
    int x = s->x_half + btp_action_dx(a), y = s->y_half + btp_action_dy(a);
    if (x < 0 || y < 2 || x >= 2*m->width-2 || y >= 2*m->height) { s->blocked = BTP_EDGE; return; }
    int tx = x/2, ty = (y-2)/2;
    if (btp_mission_tile(s,m,tx,ty) >= s->gate || btp_mission_tile(s,m,tx+1,ty) >= s->gate) {
        s->blocked = BTP_WALL; return;
    }
    s->x_half = (uint16_t)x; s->y_half = (uint16_t)y; s->blocked = BTP_CLEAR;
}
int btp_mission_tick(BtpState *s, const BtpResources *r, BtpAction a)
{
    BtpMissionState *m = &s->mission;
    if (m->phase != BTP_MISSION_DRIVE) {
        if (a == BTP_ACCEPT) m->phase = BTP_MISSION_DRIVE;
        return 0;
    }
    if (s->x_half <= 60 && s->y_half >= 73 && s->y_half <= 79) {
        if (m->corner) {
            if (m->assignment) {
                s->story_flags[1] = (uint8_t)(s->story_flags[2] != 0);
                if (s->mech_skills[1] < 3) ++s->mech_skills[1];
            } else {
                uint16_t adjusted = (uint16_t)(m->elapsed - (s->story_flags[2] ? 0u : 50u));
                int elapsed = adjusted < 32768 ? adjusted : (int)adjusted-65536;
                s->story_flags[1] = (uint8_t)(elapsed < 215);
            }
            m->phase = BTP_MISSION_RESULT; s->mode = BTP_BUILDING; return 1;
        }
        if (!m->warned) { m->warned = 1; m->phase = BTP_MISSION_WARNING; return 0; }
    }
    if (a == BTP_IDLE && m->idle) { --m->idle; return 0; }
    m->idle = 10;
    if (btp_action_moves(a)) move(s,&r->map,a);
    if (!m->assignment) m->elapsed = (uint16_t)(m->elapsed+1u+(unsigned)(btp_mission_terrain(s,&r->map)>>3));
    if (m->assignment && !m->corner && s->x_half/2u+1u >= btp_rubble_x[m->rubble] &&
        s->x_half/2u <= btp_rubble_x[m->rubble] && s->y_half/2u == (unsigned)btp_rubble_y[m->rubble]+1u) {
        m->corner = 1; m->phase = BTP_MISSION_PICKUP;
    } else if (!m->assignment && !m->corner && s->x_half >= 120 && s->y_half >= 124) {
        m->corner = 1; m->phase = BTP_MISSION_CORNER;
    }
    return 0;
}
static int literal(const BtpDialogue *d, unsigned id, uint8_t *out, size_t capacity, size_t *length)
{
    if (id >= BTP_TALK_STRINGS || !d->length || d->length > BTP_TALK_MAX || d->offset[id] >= d->length ||
        d->size[id] >= d->length-d->offset[id] || d->bytes[d->offset[id]+d->size[id]] ||
        *length >= capacity || d->size[id] >= capacity-*length) return 0;
    memcpy(out+*length,d->bytes+d->offset[id],d->size[id]); *length += d->size[id]; out[*length] = 0; return 1;
}
int btp_training_text(const BtpState *s, const BtpResources *r, uint8_t *out, size_t capacity, size_t *length)
{
    *length = 0; if (!capacity) return 0; out[0] = 0;
    if (s->mode == BTP_QUIZ) return literal(&r->dialogue,s->quiz.phase == BTP_QUIZ_INTRO ? 55u :
        s->quiz.phase == BTP_QUIZ_FAILED ? 57u : 56u,out,capacity,length);
    if (s->mode == BTP_MISSION) {
        if (s->mission.phase == BTP_MISSION_WARNING) return literal(&r->dialogue,78,out,capacity,length);
        if (s->mission.phase == BTP_MISSION_CORNER) return literal(&r->dialogue,79,out,capacity,length);
        if (s->mission.phase == BTP_MISSION_SNICKER) return literal(&r->dialogue,84,out,capacity,length);
        if (s->mission.phase == BTP_MISSION_PICKUP)
            return literal(&r->dialogue,s->story_flags[2] ? 86u : 85u,out,capacity,length);
        return 1;
    }
    const BtpScriptState *v = &s->script;
    if (!v->mech_result || v->mech_result > 3 || v->mech_after > v->text_count) return 0;
    for (unsigned i = 0; i < v->text_count; ++i) {
        BtpTextSpan span = v->text[i];
        if (span.offset > r->training.length || span.length > r->training.length-span.offset ||
            span.length >= capacity-*length) return 0;
        memcpy(out+*length,r->training.bytes+span.offset,span.length); *length += span.length; out[*length] = 0;
        if (i+1u == v->mech_after) {
            if (!literal(&r->dialogue,79u+v->mech_result,out,capacity,length)) return 0;
            if (v->mech_result != 1 && !literal(&r->dialogue,83,out,capacity,length)) return 0;
        }
    }
    return 1;
}
int btp_training_valid(const BtpState *s)
{
    const BtpQuizState *q = &s->quiz; const BtpMissionState *m = &s->mission;
    if (q->phase > BTP_QUIZ_FAILED || q->selected >= 20 || q->round > 3 || q->point >= 10 ||
        q->failed > 1 || q->used >= 1024 || m->phase > BTP_MISSION_PICKUP || m->corner > 1 ||
        m->warned > 1 || m->idle > 10 || m->walk > 15 || m->direction > 7 ||
        m->assignment > 1 || m->rubble > 7 || s->mech_skills[0] > 4 || s->mech_skills[1] > 4 ||
        s->checkpoint_mech_skills[0] > 4 || s->checkpoint_mech_skills[1] > 4 ||
        (s->entry_action != BTP_IDLE && !btp_action_moves((BtpAction)s->entry_action))) return 0;
    if ((s->mode == BTP_QUIZ) != (q->phase != 0)) return 0;
    if (!q->phase && (q->round || q->point || q->failed || q->used)) return 0;
    if (q->phase) {
        unsigned used = 0; for (unsigned i = 0; i < 10; ++i) used += !!(q->used & (1u<<i));
        if (s->entry_slot || s->story_flags[4] || s->mission.phase || s->checkpoint_valid ||
            s->script.status != BTP_SCRIPT_RUNNING) return 0;
        if (q->phase == BTP_QUIZ_INTRO && (q->round || q->failed || q->used || q->point)) return 0;
        if (q->phase == BTP_QUIZ_QUESTION && (q->round >= 3 || used != q->round+1u || !(q->used & (1u<<q->point)))) return 0;
        if (q->phase == BTP_QUIZ_FAILED && (q->round != 3 || used != 3 || !q->failed || s->story_flags[20] != 255)) return 0;
    }
    if (!m->phase) return s->mode != BTP_MISSION && !m->corner && !m->warned && !m->idle && !m->walk && !m->direction && !m->elapsed &&
        !m->assignment && !m->rubble && !m->rubble_under;
    if ((!m->assignment && (m->rubble || m->rubble_under)) || (m->assignment && m->elapsed)) return 0;
    if (s->entry_slot || s->story_flags[4] || s->story_flags[2] > 2 || !s->checkpoint_valid) return 0;
    if (m->phase == BTP_MISSION_RESULT) return s->mode == BTP_BUILDING;
    if (s->mode != BTP_MISSION || s->script.status != BTP_SCRIPT_NATIVE || s->script.native_action != 1 || s->story_flags[0] != m->assignment) return 0;
    if (m->phase == BTP_MISSION_WARNING && (!m->warned || m->corner)) return 0;
    if (m->phase == BTP_MISSION_CORNER && (!m->corner || m->assignment)) return 0;
    if (m->phase == BTP_MISSION_SNICKER && (!m->assignment || m->corner || s->story_flags[2])) return 0;
    if (m->phase == BTP_MISSION_PICKUP && (!m->assignment || !m->corner)) return 0;
    return 1;
}
