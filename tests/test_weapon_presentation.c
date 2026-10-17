#include "core/effects.h"
#include "core/audio.h"
#include "core/combat.h"
#include "core/npc.h"
#include "data/save.h"
#include "frontend/pixels.h"
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks,cases;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"%s:%d case %u: %s\n",__FILE__,__LINE__,cases,#x);exit(1); } } while (0)
static uint64_t word_hash(uint64_t h,unsigned n)
{
    h=(h^(n&255u))*UINT64_C(1099511628211);
    return (h^((n>>8)&255u))*UINT64_C(1099511628211);
}
static unsigned number(char **p) { return (unsigned)strtoul(*p,p,10); }
static uint64_t hexadecimal(char **p) { return strtoull(*p,p,16); }
static void phase(uint64_t *hash,unsigned *previous,unsigned value)
{
    if (value && value!=*previous) { *hash=word_hash(*hash,value);*previous=value; }
}
static void timeline(const BtpState *base,const BtpResources *r,const BtpCombatEffect *effect,
    unsigned graphics,uint64_t expected,int restore)
{
    BtpState s=*base;BtpCombatState *c=&s.combat;
    c->phase=BTP_COMBAT_ROUND;c->step=11;c->graphics=(uint8_t)graphics;c->shot=(BtpShot){.hit=effect->hit};
    c->unit[0].x=effect->x;c->unit[0].y=effect->y;c->unit[1].x=effect->tx;c->unit[1].y=effect->ty;
    s.x_half=effect->x;s.y_half=(uint16_t)(effect->y+2u);s.menu.speed=0;s.menu.sound=1;
    s.effects=(BtpEffectsState){0};s.audio=(BtpAudioState){0};
    btp_effects_shot(&s,0,1,effect->weapon);s.effects.shots[0]=*effect;
    uint64_t hash=UINT64_C(14695981039346656037);unsigned previous=0,ticks=0,pose_ticks=0;
    if (graphics) phase(&hash,&previous,1);
    while (s.effects.count && ticks++<1024) {
        unsigned busy=s.audio.sound_count,old_stage=s.effects.stage;
        /* Observe the queue before the audio tick consumes it. Some original
           personal effects last less than the host's 32ms audio block. */
        unsigned started=0;
        if (!busy) {
            BtpState observed=s;btp_combat_tick(&observed,r,BTP_IDLE);
            if (observed.audio.sound_count) started=observed.audio.sounds[0];
        }
        if (old_stage==BTP_EFFECT_POSES) ++pose_ticks;
        if (restore) {
            uint8_t a[BTP_STATE_BYTES],b[BTP_STATE_BYTES];BtpState copy;
            int16_t pcm[BTP_AUDIO_TICK_SAMPLES],again[BTP_AUDIO_TICK_SAMPLES];
            btp_state_encode(&s,a);CHECK(btp_state_decode(a,sizeof a,&r->map,&r->training,&copy));
            btp_game_tick_audio(&s,r,BTP_IDLE,pcm);btp_game_tick_audio(&copy,r,BTP_IDLE,again);
            btp_state_encode(&s,a);btp_state_encode(&copy,b);
            CHECK(!memcmp(a,b,sizeof a) && !memcmp(pcm,again,sizeof pcm));
        } else btp_game_tick(&s,r,BTP_IDLE);
        if (started) phase(&hash,&previous,100u+started);
        if (s.effects.count && s.effects.stage==BTP_EFFECT_FLIGHT)
            phase(&hash,&previous,btp_effects_trail_kind(effect->weapon)==1 ? 2u : 3u);
        if (s.effects.count && s.effects.stage==BTP_EFFECT_IMPACT_HOLD) phase(&hash,&previous,4);
        CHECK(s.audio.sound_count<=1 && c->step==11);
        if (restore && graphics && effect->hit && effect->target_base!=254 && s.effects.count) {
            const char *label=NULL;
            if (effect->weapon==25 && s.effects.stage==BTP_EFFECT_FLIGHT && s.effects.age==3) label="missile-flight";
            if (effect->weapon==15 && s.effects.stage==BTP_EFFECT_BEAM_SOUND) label="beam-sound";
            if (effect->weapon==15 && s.effects.stage==BTP_EFFECT_POSES && s.effects.age==1) label="firing-pose";
            if (effect->weapon==25 && s.effects.stage==BTP_EFFECT_IMPACT_HOLD && s.effects.age==1) label="impact";
            if (label) {
                char path[160];snprintf(path,sizeof path,"work/weapon-presentation/%s.btp",label);
                BtpError error;CHECK(btp_save_write(path,&s,r,&error));
            }
        }
    }
    if (ticks>=1024 || hash!=expected) fprintf(stderr,"timeline weapon %u ticks %u hash %016" PRIx64 "/%016" PRIx64 " stage %u sounds %u\n",effect->weapon,ticks,hash,expected,s.effects.stage,s.audio.sound_count);
    CHECK(ticks<1024 && hash==expected);
    unsigned n=r->combat.poses[effect->group][effect->direction][0];
    CHECK(pose_ticks==(graphics ? (n*500u+223u)/224u : 0u));
}
static void older_saves(const BtpState *base,const BtpResources *r)
{
    for (unsigned stage=0;stage<=BTP_EFFECT_LEGACY;++stage) {
        BtpState s=*base,copy;s.combat.phase=BTP_COMBAT_ROUND;s.combat.step=11;s.combat.shot=(BtpShot){.hit=1};
        s.effects=(BtpEffectsState){0};s.audio=(BtpAudioState){0};btp_effects_shot(&s,0,1,17);
        s.effects.stage=(uint8_t)stage;s.effects.age=(uint8_t)(stage==BTP_EFFECT_ATTACK ? 1 : stage>=BTP_EFFECT_HIT_SOUND ? 4 : 0);
        btp_audio_effect(&s,2);
        uint8_t a[BTP_STATE_BYTES],b[BTP_STATE_BYTES];btp_state_encode(&s,a);memcpy(a,"BTPe",4);a[4]=40;
        CHECK(btp_state_decode(a,sizeof a,&r->map,&r->training,&copy));CHECK(copy.effects.stage==stage);
        for (unsigned tick=0;tick<48;++tick) {
            int16_t pcm[BTP_AUDIO_TICK_SAMPLES],again[BTP_AUDIO_TICK_SAMPLES];
            btp_game_tick_audio(&s,r,BTP_IDLE,pcm);btp_game_tick_audio(&copy,r,BTP_IDLE,again);
            btp_state_encode(&s,a);btp_state_encode(&copy,b);CHECK(!memcmp(a,b,sizeof a) && !memcmp(pcm,again,sizeof pcm));
        }
        BtpState unchanged=copy;btp_state_encode(&s,a);memcpy(a,"BTPe",4);a[4]=40;a[18434]=BTP_EFFECT_POSES;
        CHECK(!btp_state_decode(a,sizeof a,&r->map,&r->training,&copy));CHECK(!memcmp(&copy,&unchanged,sizeof copy));
    }
}
static void queued_report_pixels(const BtpState *base,const BtpResources *r)
{
    BtpState s=*base;s.combat.phase=BTP_COMBAT_ROUND;s.combat.step=11;s.combat.graphics=0;
    s.combat.shot=(BtpShot){.hit=1};s.effects=(BtpEffectsState){0};s.audio=(BtpAudioState){0};
    btp_effects_shot(&s,0,1,17);btp_effects_shot(&s,1,0,9);btp_effects_tick(&s,r);
    CHECK(s.effects.count==1 && s.combat.delay && s.effects.stage==BTP_EFFECT_PENDING);
    uint32_t *first=malloc(BTP_PIXELS*sizeof *first),*changed=malloc(BTP_PIXELS*sizeof *changed);CHECK(first && changed);
    btp_render(r,&s,0,first);
    /* An undisplayed future actor's text must not leak into the held report. */
    s.effects.text[0].actor_name=9;s.effects.text[0].weapon=31;btp_render(r,&s,0,changed);
    for (unsigned y=0;y<200;++y) CHECK(!memcmp(first+y*320,changed+y*320,104*sizeof *first));
    free(first);free(changed);
}

int main(int argc,char **argv)
{
    if (argc!=6) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError error;CHECK(r);
    CHECK(btp_resources_load(argv[1],r,&error));CHECK(btp_dialogue_load(argv[2],&r->dialogue,&error));
    CHECK(btp_combat_data_load(argv[3],&r->combat,&error));
    BtpState base;btp_start(&base);btp_npc_init(&base,&r->map);
    FILE *input=fopen(argv[4],"r");CHECK(input);char line[1024];
    while (base.combat.phase!=BTP_COMBAT_MENU && fgets(line,sizeof line,input)) {
        line[strcspn(line,"\r\n")]=0;BtpAction action;CHECK(btp_action_parse(line,&action));btp_game_tick(&base,r,action);
    }
    fclose(input);CHECK(base.combat.phase==BTP_COMBAT_MENU);
    FILE *file=fopen(argv[5],"r");CHECK(file);unsigned timelines=0;
    while (fgets(line,sizeof line,file)) {
        if (line[0]=='#') continue;
        char *p=line;unsigned w=number(&p),direction=number(&p),family=number(&p),human=number(&p);
        unsigned hit=number(&p),graphics=number(&p),layout=number(&p);++cases;
        BtpCombatEffect e={.actor=0,.target=1,.weapon=(uint8_t)w,.direction=(uint8_t)direction,.hit=(uint8_t)hit,
            .base=(uint8_t)(family==2 ? 254 : family ? 146 : 0),.target_base=(uint8_t)(human ? 254 : 0)};
        e.group=(uint8_t)(family==2 ? 4+w : family+(w==32 ? 2u : 0u));
        e.x=(uint8_t)number(&p);e.y=(uint8_t)number(&p);e.tx=(uint8_t)number(&p);e.ty=(uint8_t)number(&p);
        p=strchr(p,'|');CHECK(p);++p;unsigned pose_count=number(&p);uint64_t poses_hash=hexadecimal(&p);
        unsigned waits=number(&p),retraces=number(&p),sounds=number(&p),sound[3]={0};CHECK(sounds<=3);
        for (unsigned i=0;i<sounds;++i) sound[i]=number(&p);
        p=strchr(p,'|');CHECK(p);++p;unsigned kind=number(&p),count=number(&p);uint64_t trail_hash=hexadecimal(&p);
        p=strchr(p,'|');CHECK(p);++p;unsigned impact_count=number(&p);uint64_t impact_hash=hexadecimal(&p);
        p=strchr(p,'|');CHECK(p);++p;(void)hexadecimal(&p);uint64_t phase_hash=hexadecimal(&p);
        const uint8_t *poses=r->combat.poses[e.group][e.direction];uint64_t h=UINT64_C(14695981039346656037);
        unsigned actual_poses=graphics ? poses[0] : 0;
        for (unsigned i=0;i<actual_poses;++i) h=word_hash(h,poses[i+1]);
        CHECK(actual_poses==pose_count && h==poses_hash);
        int actor_visible=btp_combat_visible(e.x,e.y,e.base==254,64,64);
        int target_visible=btp_combat_visible(e.tx,e.ty,e.target_base==254,64,64);
        CHECK(waits==(graphics ? (actor_visible ? actual_poses : 0u)+(hit && w>=7 && target_visible) : 0u));
        CHECK(retraces==5*waits);
        unsigned expected_sound[3]={0},n=0;
        if (graphics) {
            unsigned fire=btp_effects_fire_sound(w,actor_visible || target_visible);
            if (fire) expected_sound[n++]=fire;
            if (hit) expected_sound[n++]=4;
        }
        CHECK(n==sounds && !memcmp(sound,expected_sound,sizeof sound));
        BtpEffectTrail trail;btp_effects_trail(&e,&r->combat,64,64,&trail);
        if (!graphics || (!actor_visible && !target_visible)) trail.count=0;
        unsigned actual_kind=trail.count ? trail.kind==1 ? 1u : 2u : 0u;
        h=UINT64_C(14695981039346656037);
        for (unsigned i=0;i<trail.count;++i) {
            h=word_hash(h,(unsigned)trail.points[i].x);h=word_hash(h,(unsigned)trail.points[i].y);
            h=word_hash(h,trail.kind==1 ? trail.points[i].sprite : btp_effects_beam_color(&e,family==2 ? 4u : 0u));
        }
        if (actual_kind!=kind || trail.count!=count || h!=trail_hash)
            fprintf(stderr,"weapon %u dir %u family %u layout %u: trail %u/%u %u/%u %016" PRIx64 "/%016" PRIx64 "\n",
                w,direction,family,layout,actual_kind,kind,trail.count,count,h,trail_hash);
        CHECK(actual_kind==kind && trail.count==count && h==trail_hash);
        h=UINT64_C(14695981039346656037);
        unsigned impacts=graphics && hit && w>=7 && target_visible ? 3u : 0u;
        for (unsigned i=0;i<impacts;++i) {
            h=word_hash(h,250u+r->combat.impact[i]);h=word_hash(h,208u+8u*(unsigned)((int)e.tx-64));
            h=word_hash(h,96u+8u*(unsigned)((int)e.ty-64)-(human ? 0u : 8u));
        }
        CHECK(impacts==impact_count && h==impact_hash);
        if (direction==2 && !layout) {
            timeline(&base,r,&e,graphics,phase_hash,family==0 && (w==15 || w==19 || w==25 || w==32));++timelines;
        }
    }
    fclose(file);older_saves(&base,r);queued_report_pixels(&base,r);free(r);CHECK(cases==2400);
    printf("PASS: %u assertions; %u original weapon sequences, %u timed/sound sequences and saved PCM continuations\n",checks,cases,timelines);
    return 0;
}
