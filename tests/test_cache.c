#include "core/cache.h"
#include "core/party.h"
#include "data/save.h"
#include "frontend/pixels.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
static unsigned checks;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x);exit(1); } } while (0)
static void input(BtpState *s,const BtpResources *r,BtpAction action)
{
    uint8_t a[BTP_STATE_BYTES],b[BTP_STATE_BYTES];BtpState copy;btp_state_encode(s,a);
    if (!btp_state_decode(a,sizeof a,btp_active_map(r,s),btp_state_bld(r,s),&copy)) {
        fprintf(stderr,"Cache restore: tick=%u mode=%u map=%u at=%u,%u script=%u/%u disk=%u service=%u\n",
            s->tick,s->mode,s->map_id,s->x_half,s->y_half,s->script.status,s->script.pc,s->disk_origin,s->service.phase);
        CHECK(0);
    }
    btp_game_tick(s,r,action);btp_game_tick(&copy,r,action);btp_state_encode(s,a);btp_state_encode(&copy,b);CHECK(!memcmp(a,b,sizeof a));
}
static uint64_t hash(const uint8_t *p,unsigned n)
{
    uint64_t h=UINT64_C(14695981039346656037);for (unsigned i=0;i<n;++i) h=(h^p[i])*UINT64_C(1099511628211);return h;
}
static uint64_t map_hash(const BtpState *s,const BtpResources *r)
{
    uint8_t tiles[4096];for (unsigned y=0;y<64;++y) for (unsigned x=0;x<64;++x) tiles[y*64+x]=(uint8_t)btp_cache_tile(r,s,(int)x,(int)y);
    return hash(tiles,4096);
}
static unsigned normal(unsigned raw)
{
    return (raw/64/4*8+raw%64/8)*32+raw/64%4*8+raw%8;
}
int main(int argc,char **argv)
{
    if (argc!=2) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError e;CHECK(r && btp_resources_load(argv[1],r,&e));
    CHECK(btp_combat_data_load("work/combat-data.bin",&r->combat,&e));CHECK(btp_dialogue_load("work/talk-data.bin",&r->dialogue,&e));
    CHECK(btp_world_data_load("work/world-data.bin",&r->world,&e));
    BtpState base;CHECK(btp_save_load("Original DOS/GAME1",&base,r,&e));btp_cache_begin(&base,r);
    for (unsigned i=0;i<64 && base.mode==BTP_BUILDING;++i) input(&base,r,BTP_ACCEPT);
    CHECK(base.mode==BTP_CACHE && !base.cache.phase);for (unsigned i=0;i<256 && base.audio.sound_count;++i) input(&base,r,BTP_IDLE);
    CHECK(!base.audio.sound_count);
    /* GAME1 brings five people. Every foot sprite must contribute visible
       map pixels, and all follower positions must pass cache collision. */
    uint32_t complete[BTP_PIXELS],without[BTP_PIXELS];btp_render(r,&base,0,complete);
    CHECK(btp_party_count(&base.party)==5);
    for (unsigned i=1;i<5;++i) {
        CHECK(btp_party_walkable(&base,r,base.party.x[i],base.party.y[i],0));
        BtpState hidden=base;hidden.party.people[i][0]=255;btp_render(r,&hidden,0,without);
        unsigned different=0;for (unsigned y=0;y<200;++y) for (unsigned x=104;x<320;++x) different+=complete[y*320+x]!=without[y*320+x];
        CHECK(different);
    }
    BtpState stale=base;stale.campaign.world_x=776;stale.campaign.world_y=778;
    for (unsigned i=0;i<8;++i) { stale.party.x[i]=776;stale.party.y[i]=778; }
    CHECK(btp_save_write("work/m4-audit/cache-old-formation.btp",&stale,r,&e));
    CHECK(btp_save_load("work/m4-audit/cache-old-formation.btp",&stale,r,&e));btp_render(r,&stale,0,without);
    CHECK(!memcmp(complete,without,sizeof complete));
    memset(base.story_flags+67,0,12);
    FILE *f=fopen("tests/fixtures/cache-primary.txt","r");CHECK(f);char line[256];unsigned cases=0;
    while (fgets(line,sizeof line,f)) {
        if (line[0]=='#') continue;
        BtpState s=base;unsigned i=0,a=0,b=0,c=0,d=0,n=0;uint64_t mh=0,uh=0;
        if (line[0]=='T') {
            unsigned cards[3];CHECK(sscanf(line+1,"%u %u %u %u %u %u",&i,&a,&b,&cards[0],&cards[1],&cards[2])==6);
            s.cache.used[i]=(uint8_t)a;CHECK(btp_cache_terminal(&s,r,r->combat.cache_tx[i]-1u,r->combat.cache_ty[i]));
            if (!a && !b) input(&s,r,BTP_RIGHT);
            input(&s,r,BTP_ACCEPT);
            for (unsigned color=0;color<3;++color) CHECK(s.story_flags[59+color]==cards[color]);
        } else if (line[0]=='D') {
            CHECK(sscanf(line+1,"%u %u %u %" SCNx64 " %" SCNx64 " %u",&i,&a,&b,&mh,&uh,&n)==6);
            unsigned required[]={r->combat.cache_red[i],r->combat.cache_blue[i],r->combat.cache_yellow[i]};
            for (unsigned color=0;color<3;++color) s.story_flags[59+color]=(uint8_t)(a&(1u<<color) || i==11 ? 255u : required[color]-1u);
            CHECK((unsigned)btp_cache_door(&s,r,r->combat.cache_dx[i]-1u,r->combat.cache_dy[i],-1)==b);
            CHECK((s.audio.sound_count && s.audio.sounds[0]==10)==n);
            for (unsigned tick=0;tick<256 && s.cache.phase==BTP_CACHE_DOOR;++tick) input(&s,r,BTP_IDLE);
            CHECK(s.story_flags[67+i]==b && map_hash(&s,r)==mh && hash(s.cache.used,33)==uh);
            input(&s,r,BTP_IDLE);
        } else if (line[0]=='S') {
            CHECK(sscanf(line+1,"%" SCNx64,&mh)==1);s.cache.hall=1;CHECK(map_hash(&s,r)==mh);input(&s,r,BTP_IDLE);
        } else if (line[0]=='X') {
            CHECK(sscanf(line+1,"%u %u %u %u",&a,&b,&c,&n)==4);s.story_flags[66]=1;s.gate=139;s.x_half=4;s.y_half=34;
            memcpy(s.cache.maproom,r->maproom.tiles,768);btp_cache_toggle(&s,2*a-1,2*b);
            CHECK(s.cache.maproom[b*32+a]==c && s.audio.sound_count==n && s.audio.sounds[0]==15);input(&s,r,BTP_IDLE);
        } else if (line[0]=='P') {
            CHECK(sscanf(line+1,"%u %u %u %" SCNx64 " %u",&a,&b,&c,&mh,&d)==5);s.story_flags[66]=1;s.gate=139;s.x_half=4;s.y_half=34;
            memcpy(s.cache.maproom,r->maproom.tiles,768);
            for (unsigned j=0;j<7;++j) if (a&(1u<<j)) ++s.cache.maproom[normal(r->combat.cache_password[j])];
            if (b) for (unsigned raw=0;raw<768;++raw) {
                unsigned wanted=0;for (unsigned j=0;j<7;++j) wanted|=raw==r->combat.cache_password[j];
                unsigned at=normal(raw);if (s.cache.maproom[at]>=151 && s.cache.maproom[at]<=240 && !wanted) { ++s.cache.maproom[at];break; }
            }
            CHECK((unsigned)btp_cache_password(&s,r)==c && s.story_flags[62]==c && hash(s.cache.maproom,768)==mh);
            CHECK(s.audio.sound_count==1 && s.audio.sounds[0]==d);input(&s,r,BTP_IDLE);
        } else if (line[0]=='R') {
            unsigned enter,solved,active,x,y,gate;
            CHECK(sscanf(line+1,"%u %u %u %u %u %u",&enter,&solved,&active,&x,&y,&gate)==6);
            /* The original transition oracle covers cursor/room/gate. The
               party-size and old-save recovery checks below are native
               continuation checks, not original follower-coordinate claims. */
            for (unsigned count=1;count<=8;++count) {
                s=base;s.story_flags[66]=(uint8_t)!enter;s.story_flags[62]=(uint8_t)solved;
                s.gate=(uint8_t)(enter ? 33 : 139);s.x_half=(uint16_t)(enter ? 70 : 3);s.y_half=(uint16_t)(enter ? 57 : 34);
                memcpy(s.cache.maproom,r->maproom.tiles,768);
                for (unsigned member=0;member<8;++member) {
                    memcpy(s.party.people[member],base.party.people[0],17);
                    s.party.people[member][0]=(uint8_t)(member<count ? member : 255);
                }
                btp_cache_restore_party(&s,r);
                input(&s,r,enter ? BTP_RIGHT : BTP_LEFT);
                CHECK(s.cache.phase==(enter ? (solved ? BTP_CACHE_NOTICE : BTP_CACHE_PEER) : BTP_CACHE_EXIT));
                input(&s,r,BTP_ACCEPT);
                if (enter && !solved) { CHECK(s.cache.phase==BTP_CACHE_CLIMB);input(&s,r,BTP_ACCEPT); }
                CHECK(s.x_half==x && s.y_half==y && s.gate==gate && s.story_flags[66]==active);
                CHECK(!s.cache.phase && s.mode==BTP_CACHE);
                BtpState stable=s;btp_cache_restore_party(&s,r);CHECK(!memcmp(&stable,&s,sizeof s));
                for (unsigned member=0;member<count;++member) {
                    CHECK(btp_party_walkable(&s,r,s.party.x[member],s.party.y[member],0));
                    CHECK(abs((int)s.party.x[member]-(int)s.campaign.world_x)<=8);
                    CHECK(abs((int)s.party.y[member]-(int)s.campaign.world_y)<=8);
                    /* Even with a correct leader, a follower left at the
                       cave must be visible again on the first loaded frame. */
                    BtpState broken=s;broken.party.x[member]=776;broken.party.y[member]=778;
                    CHECK(btp_save_write("work/m4-audit/cache-split-formation.btp",&broken,r,&e));
                    CHECK(btp_save_load("work/m4-audit/cache-split-formation.btp",&broken,r,&e));
                    CHECK(btp_party_walkable(&broken,r,broken.party.x[member],broken.party.y[member],0));
                    CHECK(abs((int)broken.party.x[member]-(int)broken.campaign.world_x)<=8);
                    input(&broken,r,BTP_IDLE);
                }
            }
        } else CHECK(0);
        ++cases;
    }
    fclose(f);CHECK(cases==534);
    /* The original decoder/palette is now also checked against all 64,000
       pixels of the live DOSBox Phoenix screen; see its fixture metadata. */
    f=fopen("tests/fixtures/phoenix-palette-primary.txt","r");CHECK(f);
    uint64_t phoenix_rgb=0;CHECK(fscanf(f,"F %" SCNx64,&phoenix_rgb)==1 && !fclose(f));
    BtpState s;CHECK(btp_save_load("Original DOS/GAME1",&s,r,&e));f=fopen("tests/fixtures/ordinary-cache.actions","r");CHECK(f);
    unsigned ticks=0,animations=0,room=0,phoenix=0,terminal=0,door=0,final_key=0;
    while (fgets(line,sizeof line,f)) {
        line[strcspn(line,"\r\n")]=0;BtpAction action;CHECK(btp_action_parse(line,&action));input(&s,r,action);++ticks;
        if (s.cutscene.active && s.cutscene.kind>=10 && s.cutscene.kind<=14) animations|=1u<<(s.cutscene.kind-10u);
        room+=s.story_flags[66]!=0;phoenix+=s.cache.phase==BTP_CACHE_PHOENIX;terminal+=s.cache.phase==BTP_CACHE_TERMINAL;door+=s.cache.phase==BTP_CACHE_DOOR;
        if (s.cache.phase==BTP_CACHE_PHOENIX && phoenix==1) {
            btp_render(r,&s,0,complete);uint64_t rgb=UINT64_C(14695981039346656037);
            for (unsigned pixel=0;pixel<BTP_PIXELS;++pixel) for (unsigned c=0;c<3;++c)
                rgb=(rgb^((complete[pixel]>>(16u-8u*c))&255u))*UINT64_C(1099511628211);
            CHECK(rgb==phoenix_rgb);CHECK(btp_write_ppm("work/m4-audit/phoenix-palette-native.ppm",complete));
        }
        const BtpBld *script=btp_state_bld(r,&s);
        if (!final_key && s.campaign.building==25 && s.script.status==BTP_SCRIPT_WAIT &&
            !s.cutscene.active && !s.audio.sound_count && s.script.pc<script->length && script->bytes[s.script.pc]==255) {
            CHECK(btp_save_write("work/m4-audit/cache-final-key.btp",&s,r,&e));final_key=1;
        }
        CHECK(s.mode!=BTP_SCRIPT_FAULT);
    }
    fclose(f);CHECK(ticks>10000 && s.mode==BTP_ENDING && s.menu.quit && animations==31 && room && phoenix && terminal && door && final_key);
    CHECK(s.cache.hall && s.story_flags[62] && s.story_flags[63] && s.story_flags[64] && s.story_flags[65] && !s.story_flags[66]);
    for (unsigned j=67;j<=78;++j) CHECK(s.story_flags[j]==1);
    CHECK(btp_save_write("work/m4-audit/cache-ending.btp",&s,r,&e));BtpState restored;CHECK(btp_save_load("work/m4-audit/cache-ending.btp",&restored,r,&e));
    /* Earlier saves had already reached this screen without the exit flag.
       They remain viewable while idle, then leave on the next logical key. */
    BtpState old_end=restored;old_end.menu.quit=0;
    CHECK(btp_save_write("work/m4-audit/cache-old-ending.btp",&old_end,r,&e));
    input(&old_end,r,BTP_IDLE);CHECK(!old_end.menu.quit);
    input(&old_end,r,BTP_LEFT);CHECK(old_end.menu.quit);
    uint32_t *pixels=malloc(BTP_PIXELS*sizeof *pixels);CHECK(pixels);btp_render(r,&restored,0,pixels);free(pixels);
    btp_start(&s);f=fopen("tests/fixtures/ordinary-fresh-campaign.actions","r");CHECK(f);
    unsigned fresh_ticks=0,disk=0,qualified=0;
    FILE *primary=fopen("tests/fixtures/campaign-checkpoints-primary.txt","r");CHECK(primary);
    char projection[200];unsigned checkpoint_tick=0,checkpoint_cash=0,checkpoint_count=0;uint64_t checkpoint_hash=0;
    CHECK(fgets(projection,sizeof projection,primary));CHECK(sscanf(projection,"T %u %u %" SCNx64,&checkpoint_tick,&checkpoint_cash,&checkpoint_hash)==3);
    while (fgets(line,sizeof line,f)) {
        line[strcspn(line,"\r\n")]=0;BtpAction action;CHECK(btp_action_parse(line,&action));input(&s,r,action);++fresh_ticks;
        disk|=s.disk_origin==19;qualified|=s.party.people[2][9]==4 && s.party.people[3][10]==4 && s.story_flags[54];
        CHECK(!s.original.valid && s.mode!=BTP_SCRIPT_FAULT && s.audio.sound_count<=1);
        if (fresh_ticks==checkpoint_tick) {
            CHECK(s.credits==checkpoint_cash && hash((const uint8_t *)s.party.people,136)==checkpoint_hash);++checkpoint_count;
            CHECK(fgets(projection,sizeof projection,primary));
            if (projection[0]=='T') CHECK(sscanf(projection,"T %u %u %" SCNx64,&checkpoint_tick,&checkpoint_cash,&checkpoint_hash)==3);
            else checkpoint_tick=0;
        }
    }
    fclose(primary);fclose(f);CHECK(checkpoint_count==2 && fresh_ticks>40000 && disk && qualified && s.mode==BTP_ENDING);
    CHECK(s.story_flags[50] && s.story_flags[53] && s.story_flags[54] && s.story_flags[65]);
    CHECK(btp_save_write("work/m4-audit/fresh-ending.btp",&s,r,&e));
    CHECK(btp_save_load("work/m4-audit/fresh-ending.btp",&restored,r,&e));
    free(r);printf("PASS: %u checks, 534 primary cache cases, late-save ending and %u-input fresh-game ending\n",checks,fresh_ticks);return 0;
}
