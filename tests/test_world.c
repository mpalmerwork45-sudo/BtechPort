#include "core/world.h"
#include "core/party.h"
#include "core/menu.h"
#include "core/animation.h"
#include "frontend/pixels.h"
#include "data/save.h"
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks;
#define CHECK(x) do { ++checks;if (!(x)) { fprintf(stderr,"%s:%d: %s\n",__FILE__,__LINE__,#x);return 1; } } while (0)
static uint64_t fingerprint(const uint8_t *b,size_t n)
{
    uint64_t h=UINT64_C(14695981039346656037);
    for (size_t i=0;i<n;++i) h=(h^b[i])*UINT64_C(1099511628211);
    return h;
}
int main(int argc,char **argv)
{
    if (argc!=4) return 2;
    BtpResources *r=calloc(1,sizeof *r);BtpError e;
    CHECK(r && btp_resources_load(argv[1],r,&e) && btp_world_data_load(argv[2],&r->world,&e));
    CHECK(btp_combat_data_load("work/combat-data.bin",&r->combat,&e));
    CHECK(btp_dialogue_load("work/talk-data.bin",&r->dialogue,&e));
    FILE *f=fopen(argv[3],"r");CHECK(f);char line[200];unsigned cases=0;
    while (fgets(line,sizeof line,f)) if (line[0]=='W') {
        unsigned x,y,seed;uint64_t expected;uint8_t sector[4096];
        CHECK(sscanf(line+1,"%u %u %u %" SCNx64,&x,&y,&seed,&expected)==4);
        CHECK(x>=11 && x<=13 && y>=11 && y<=13 && seed==r->world.seed);
        for (unsigned row=0;row<64;++row)
            memcpy(sector+64*row,r->world.tiles+((y-11)*64+row)*192+(x-11)*64,64);
        CHECK(fingerprint(sector,sizeof sector)==expected);++cases;
    }
    fclose(f);CHECK(cases==9);
    f=fopen("tests/fixtures/world-native.txt","r");CHECK(f);cases=0;
    while (fgets(line,sizeof line,f)) if (line[0]=='G') {
        unsigned seed,x,y;uint64_t expected;uint8_t sector[4096];
        CHECK(sscanf(line+1,"%u %u %u %" SCNx64,&seed,&x,&y,&expected)==4);
        CHECK(x<16 && y<16 && btp_world_generate(&r->world,seed));
        for (unsigned row=0;row<64;++row) for (unsigned col=0;col<64;++col)
            sector[64*row+col]=(uint8_t)btp_generated_tile(&r->world,(int)(64*x+col),(int)(64*y+row));
        if (fingerprint(sector,sizeof sector)!=expected)
            fprintf(stderr,"seed %u sector %u,%u: %016" PRIx64 " vs %016" PRIx64 "\n",seed,x,y,fingerprint(sector,sizeof sector),expected);
        CHECK(fingerprint(sector,sizeof sector)==expected);++cases;
    }
    fclose(f);CHECK(cases==30);CHECK(btp_world_generate(&r->world,0x020304));
    f=fopen("tests/fixtures/city-edges-primary.txt","r");CHECK(f);cases=0;
    while (fgets(line,sizeof line,f)) {
        unsigned seed,id;uint64_t tiles_expected,descriptors_expected;
        CHECK(sscanf(line,"T %u %u %" SCNx64 " %" SCNx64,&seed,&id,&tiles_expected,&descriptors_expected)==4);
        CHECK(id>=1 && id<=13 && btp_world_generate(&r->world,seed));
        const BtpMap *town=id==1 ? &r->map : id==11 ? &r->destroyed : &r->local[id-1];
        const BtpMap *origin=id==11 ? &r->map : town;
        int ox=(origin->entrance_x[0]>>8)*64,oy=(origin->entrance_y[0]>>12)*64;
        BtpState city;btp_start(&city);city.story_flags[4]=(uint8_t)(id==11);
        uint8_t tiles[80*80],descriptors[100];unsigned n=0,d=0;
        for (int y=-8;y<town->height+8;++y) for (int x=-8;x<town->width+8;++x)
            tiles[n++]=(uint8_t)btp_world_tile(r,&city,ox+x,oy+y);
        for (int y=-1;y<town->height/8+1;++y) for (int x=-1;x<town->width/8+1;++x)
            descriptors[d++]=(uint8_t)btp_world_descriptor(r,&city,ox+8*x+4,oy+8*y+4);
        if (fingerprint(tiles,n)!=tiles_expected || fingerprint(descriptors,d)!=descriptors_expected)
            fprintf(stderr,"City seed=%u map=%u tiles=%016" PRIx64 "/%016" PRIx64 " descriptors=%016" PRIx64 "/%016" PRIx64 "\n",
                seed,id,fingerprint(tiles,n),tiles_expected,fingerprint(descriptors,d),descriptors_expected);
        CHECK(fingerprint(tiles,n)==tiles_expected && fingerprint(descriptors,d)==descriptors_expected);++cases;
    }
    fclose(f);CHECK(cases==39 && btp_world_generate(&r->world,0x020304));
    f=fopen("tests/fixtures/world-water-primary.txt","r");CHECK(f);cases=0;
    BtpWorldData terrain=r->world;BtpState depth;btp_start(&depth);
    while (fgets(line,sizeof line,f)) {
        unsigned x,y,descriptor,rejected;int dx,dy;
        CHECK(sscanf(line,"W %u %u %d %d %u %u",&x,&y,&dx,&dy,&descriptor,&rejected)==6);
        memset(r->world.heights,descriptor==15 ? 0 : descriptor==0 ? 32 : 16,sizeof r->world.heights);
        CHECK(btp_world_deep_crossing(r,&depth,1024+x,1024+y,dx,dy)==(int)rejected);++cases;
    }
    fclose(f);CHECK(cases==432);r->world=terrain;
    f=fopen("tests/fixtures/world-island-water-primary.txt","r");CHECK(f);cases=0;
    while (fgets(line,sizeof line,f)) {
        unsigned x,y,rejected;int dx,dy;
        CHECK(sscanf(line,"C %u %u %d %d %u",&x,&y,&dx,&dy,&rejected)==5);
        CHECK(btp_world_deep_crossing(r,&depth,x,y,dx,dy)==(int)rejected);++cases;
    }
    fclose(f);CHECK(cases==392);
    /* The leader's feet are visibly on MAP13 land while its cursor leaves
       the west edge. Underlying generated water must not block this step. */
    BtpState island;btp_start(&island);island.story_flags[4]=1;island.map_id=13;
    island.story_flags[36]=127;
    island.x_half=0;island.y_half=10;island.campaign.world_x=768;island.campaign.world_y=778;
    CHECK(btp_save_write("work/cache-island-start.btp",&island,r,&e));
    CHECK(btp_world_tile(r,&island,384,389)<85 && !btp_world_deep_crossing(r,&island,768,778,-1,0));
    btp_game_tick(&island,r,BTP_LEFT);
    CHECK(island.blocked==BTP_CLEAR && island.mode==BTP_EXPLORE && island.campaign.world_x==767);
    CHECK(btp_save_write("work/cache-island-edge.btp",&island,r,&e));BtpState island_copy;
    CHECK(btp_save_load("work/cache-island-edge.btp",&island_copy,r,&e));
    btp_game_tick(&island,r,BTP_RIGHT);btp_game_tick(&island_copy,r,BTP_RIGHT);
    CHECK(island.campaign.world_x==768 && island.map_id==13 && !island.blocked);
    uint8_t first[BTP_STATE_BYTES],second[BTP_STATE_BYTES];btp_state_encode(&island,first);btp_state_encode(&island_copy,second);
    CHECK(!memcmp(first,second,sizeof first) && remove("work/cache-island-edge.btp")==0);
    /* A real generated-water edge and its modal survive saving. */
    BtpState swimmer;btp_start(&swimmer);swimmer.story_flags[4]=1;swimmer.map_id=0;
    unsigned wet_x=0,wet_y=0;
    for (unsigned y=32;y<1800 && !wet_x;y+=16) for (unsigned x=32;x<1800;x+=16)
        if (!btp_world_location(r,&swimmer,(int)x/2,(int)y/2) && btp_world_deep_crossing(r,&swimmer,x,y,-1,0)) { wet_x=x;wet_y=y;break; }
    CHECK(wet_x);swimmer.x_half=swimmer.campaign.world_x=(uint16_t)wet_x;
    swimmer.y_half=swimmer.campaign.world_y=(uint16_t)wet_y;swimmer.story_flags[58]=1;
    btp_game_tick(&swimmer,r,BTP_LEFT);
    CHECK(swimmer.blocked==BTP_WATER && swimmer.mode==BTP_ACTIONS && swimmer.menu.notice==5 && swimmer.campaign.world_x==wet_x);
    CHECK(btp_save_write("work/water-dialog.btp",&swimmer,r,&e));BtpState water_copy;
    CHECK(btp_save_load("work/water-dialog.btp",&water_copy,r,&e));
    btp_game_tick(&water_copy,r,BTP_OPEN_MENU);CHECK(water_copy.mode==BTP_EXPLORE && water_copy.campaign.world_x==wet_x);
    CHECK(remove("work/water-dialog.btp")==0);
    /* Collision runs for every intermediate half-step, including diagonals.
       Give MAP2 a controlled roof strip so the boundary is unambiguous. */
    BtpMap map2=r->local[1];memset(r->local[1].tiles,64,4096);
    for (unsigned y=0;y<64;++y) r->local[1].tiles[y*64+10]=115;
    for (unsigned step=1;step<=4;step*=2) for (unsigned mounted=0;mounted<2;++mounted) {
        BtpState walk;btp_start(&walk);walk.story_flags[4]=walk.story_flags[58]=1;walk.map_id=2;
        walk.x_half=16;walk.y_half=64;walk.campaign.world_x=1296;walk.campaign.world_y=1088;
        walk.menu.steps=(uint8_t)step;btp_party_init(&walk);
        if (mounted) { memcpy(walk.campaign.mech,r->combat.loans[0],125);walk.party.mech_types[0]='L';walk.campaign.owned=walk.campaign.mounted=1;walk.party.people[0][12]=0; }
        BtpState singles=walk;singles.menu.steps=1;
        btp_game_tick(&walk,r,BTP_RIGHT);
        for (unsigned i=0;i<step;++i) btp_game_tick(&singles,r,BTP_RIGHT);
        CHECK(walk.campaign.world_x==singles.campaign.world_x && walk.campaign.world_y==singles.campaign.world_y);
        CHECK(walk.x_half<19 && btp_world_tile(r,&walk,(walk.campaign.world_x+1)/2,walk.campaign.world_y/2)<85);
    }
    memset(r->local[1].tiles,64,4096);
    memset(r->local[1].room_map,255,sizeof r->local[1].room_map);
    for (unsigned step=1;step<=4;step*=2) {
        BtpState walk;btp_start(&walk);walk.story_flags[4]=walk.story_flags[58]=1;walk.map_id=2;
        walk.x_half=32;walk.y_half=64;walk.campaign.world_x=1312;walk.campaign.world_y=1088;
        walk.menu.steps=(uint8_t)step;btp_party_init(&walk);
        for (unsigned i=0;i<4;++i) { memcpy(walk.party.people[i],walk.party.people[0],17);walk.party.people[i][0]=(uint8_t)i;walk.party.people[i][12]=8; }
        memcpy(walk.campaign.mech,r->combat.loans[0],125);memcpy(walk.party.mechs[0],r->combat.commando,125);
        walk.campaign.mech[121]=0;walk.party.mechs[0][121]=1;walk.party.mech_types[0]='L';walk.party.mech_types[1]='C';
        walk.party.people[0][12]=0;walk.party.people[1][12]=1;walk.campaign.owned=walk.campaign.mounted=1;
        unsigned last[3]={UINT32_MAX,UINT32_MAX,UINT32_MAX};
        for (unsigned key=0;key<5;++key) {
            btp_game_tick(&walk,r,BTP_RIGHT);
            for (unsigned i=1;i<4;++i) {
                if (walk.party.walk[i]==last[i-1]) fprintf(stderr,"Animation: steps=%u key=%u member=%u mode=%u pos=%u,%u gait=%u\n",step,key,i,walk.mode,walk.party.x[i],walk.party.y[i],walk.party.walk[i]);
                CHECK(walk.party.walk[i]!=last[i-1]);last[i-1]=walk.party.walk[i];
            }
        }
    }
    /* The leader is on foot below a roof. The first vehicle's desired
       formation crosses that roof, while the other vehicles and people have
       distinct footprints. Every member remains legal at each input and the
       blocked mech goes around the south edge instead of through the roof. */
    for (unsigned y=8;y<18;++y) for (unsigned x=10;x<16;++x) r->local[1].tiles[y*64+x]=115;
    for (unsigned step=1;step<=4;step*=2) {
        BtpState group;btp_start(&group);group.story_flags[4]=group.story_flags[58]=1;group.map_id=2;
        group.x_half=12;group.y_half=36;group.campaign.world_x=1292;group.campaign.world_y=1060;
        group.menu.steps=(uint8_t)step;btp_party_init(&group);
        for (unsigned i=1;i<8;++i) { memcpy(group.party.people[i],group.party.people[0],17);group.party.people[i][0]=(uint8_t)i; }
        for (unsigned i=0;i<3;++i) {
            uint8_t *mech=btp_party_mech(&group,i);memcpy(mech,r->combat.loans[0],125);
            mech[121]=(uint8_t)(i+1);group.party.mech_types[i]='L';group.party.people[i+1][12]=(uint8_t)i;
        }
        group.campaign.owned=1;btp_party_follow(&group,r,1292,1060);
        for (unsigned key=0;key<32u/step;++key) {
            btp_game_tick(&group,r,BTP_RIGHT);CHECK(group.mode==BTP_EXPLORE);
            for (unsigned i=0;i<8;++i) if (group.party.people[i][12]>=8)
                CHECK(btp_party_walkable(&group,r,group.party.x[i],group.party.y[i],0));
            for (unsigned i=0;i<3;++i) CHECK(btp_party_walkable(&group,r,group.party.mech_x[i],group.party.mech_y[i],1));
            uint8_t before[BTP_STATE_BYTES],after[BTP_STATE_BYTES];BtpState copy;
            btp_state_encode(&group,before);CHECK(btp_state_decode(before,sizeof before,btp_active_map(r,&group),NULL,&copy));
            btp_state_encode(&copy,after);CHECK(!memcmp(before,after,sizeof before));
        }
        CHECK(group.campaign.world_x==1324 && group.party.mech_x[0]>1311);
    }
    r->local[1]=map2;
    /* Captured original GAME3 sector selectors, including MAP11's return
       location. Their MTP high bits agree with the live table exactly. */
    static const unsigned towns[][3]={{8,2,9},{4,3,12},{11,4,8},{2,6,10},{6,6,13},{13,7,3},{10,8,2},{6,10,7},{9,11,4},{2,12,5},{12,12,11},{5,13,6}};
    BtpState traveler;btp_start(&traveler);traveler.story_flags[4]=1;
    for (unsigned i=0;i<12;++i) {
        unsigned x=towns[i][0]*64u,y=towns[i][1]*64u,id=towns[i][2];
        CHECK(btp_world_location(r,&traveler,(int)x,(int)y)==(int)id);
        const BtpMap *town=id==11 ? &r->destroyed : &r->local[id-1];
        for (unsigned row=0;row<town->height;++row) for (unsigned col=0;col<town->width;++col)
            CHECK(btp_world_tile(r,&traveler,(int)(x+col),(int)(y+row))==btp_map_tile(town,(int)col,(int)row));
    }
    uint8_t *raw;size_t n;CHECK(btp_read_file(argv[2],&raw,&n,&e));
    BtpWorldData untouched=r->world;
    CHECK(!btp_world_data_decode(raw,n-1,&r->world,&e) && !memcmp(&untouched,&r->world,sizeof untouched));
    const unsigned corrupt[]={0,4,8,12,16,80};
    for (unsigned i=0;i<sizeof corrupt/sizeof corrupt[0];++i) {
        unsigned at=corrupt[i];uint8_t old=raw[at];raw[at]=255;
        if (at==12) raw[15]=255;
        CHECK(!btp_world_data_decode(raw,n,&r->world,&e) && !memcmp(&untouched,&r->world,sizeof untouched));
        raw[at]=old;if (at==12) raw[15]=0;
    }
    free(raw);
    BtpState s;btp_start(&s);
    f=fopen("tests/fixtures/world-view-primary.txt","r");CHECK(f);cases=0;
    while (fgets(line,sizeof line,f)) {
        if (line[0]=='F') {
            unsigned x,y,mapper;uint64_t expected;CHECK(sscanf(line+1,"%u %u %u %" SCNx64,&x,&y,&mapper,&expected)==4);
            BtpState view=s;memset(view.explored,0,sizeof view.explored);view.story_flags[4]=1;view.story_flags[49]=(uint8_t)mapper;
            view.campaign.world_x=(uint16_t)x;view.campaign.world_y=(uint16_t)y;btp_world_reveal(&view);
            CHECK(fingerprint(view.explored,sizeof view.explored)==expected);++cases;
        } else if (line[0]=='T') {
            unsigned level,mask,expected;CHECK(sscanf(line+1,"%u %u %u",&level,&mask,&expected)==3);
            CHECK(btp_world_mini_index(level,mask)==expected);++cases;
        } else if (line[0]=='A') {
            unsigned x,y,direction;CHECK(sscanf(line+1,"%u %u %u",&x,&y,&direction)==3);
            CHECK(btp_world_device_direction(x,y)==direction);++cases;
        } else if (line[0]=='P') {
            char original[16],path[80];uint64_t expected,h=UINT64_C(14695981039346656037);
            CHECK(sscanf(line+1,"%15s %" SCNx64,original,&expected)==2);
            snprintf(path,sizeof path,"Original DOS/%s",original);BtpState view;
            CHECK(btp_save_load(path,&view,r,&e));
            btp_game_tick(&view,r,BTP_OPEN_MENU);btp_game_tick(&view,r,BTP_UP);btp_game_tick(&view,r,BTP_ACCEPT);
            CHECK(view.mode==BTP_ACTIONS && view.campaign.ui==BTP_MENU_MAP);
            uint32_t *frame=malloc(BTP_PIXELS*sizeof *frame);CHECK(frame);btp_render(r,&view,0,frame);
            /* Two source black pixels immediately left of the device glyph
               remain unexplained by the font blit. Compare the other 63,998
               pixels exactly, with these two explicitly masked to source. */
            frame[70u*320u+183u]=frame[71u*320u+183u]=0;
            for (unsigned pixel=0;pixel<BTP_PIXELS;++pixel) for (int shift=16;shift>=0;shift-=8)
                h=(h^(uint8_t)(frame[pixel]>>shift))*UINT64_C(1099511628211);
            CHECK(h==expected);free(frame);++cases;
        }
    }
    fclose(f);CHECK(cases==787);
    for (unsigned row=98;row<=103;++row) CHECK(s.explored[row*16u+12u]==31);
    for (unsigned y=0;y<64;++y) for (unsigned x=0;x<64;++x)
        CHECK(btp_world_tile(r,&s,(int)x+768,(int)y+768)==btp_map_tile(&r->map,(int)x,(int)y));
    CHECK(btp_world_tile(r,&s,-1,768)==255 && btp_world_tile(r,&s,1024,768)==255);
    CHECK(r->world.native && btp_world_tile(r,&s,703,768)<250 && btp_world_tile(r,&s,896,768)<250);
    uint32_t *a=malloc(BTP_PIXELS*sizeof *a),*b=malloc(BTP_PIXELS*sizeof *b);CHECK(a && b);
    /* A combat sector is a rules grid, not a black viewport boundary. Compare
       every right-panel terrain pixel with the same exploration world view
       at four corners and four sides, using real generated terrain. */
    const unsigned edge[8][2]={{0,0},{127,0},{0,127},{127,127},{0,64},{127,64},{64,0},{64,127}};
    uint8_t sprite_format=r->sprites.format;r->sprites.format=0;
    for (unsigned i=0;i<8;++i) {
        BtpState battle;btp_start(&battle);battle.story_flags[4]=1;battle.map_id=0;battle.mode=BTP_ENCOUNTER;
        battle.campaign.encounter=1;battle.campaign.battle_x=1152;battle.campaign.battle_y=1664;
        battle.combat.phase=BTP_COMBAT_ROUND;battle.combat.count=2;battle.combat.unit[0].record[0]=battle.combat.unit[1].record[0]=255;
        battle.combat.unit[0].x=(uint8_t)edge[i][0];battle.combat.unit[0].y=(uint8_t)edge[i][1];
        BtpState exploration=battle;exploration.mode=BTP_EXPLORE;exploration.campaign.encounter=0;exploration.combat=(BtpCombatState){0};
        exploration.x_half=(uint16_t)(1152+edge[i][0]);exploration.y_half=(uint16_t)(1664+edge[i][1]+2);
        btp_render(r,&battle,0,a);btp_render(r,&exploration,0,b);
        for (unsigned row=0;row<200;++row) CHECK(!memcmp(a+row*320+104,b+row*320+104,216*sizeof *a));
    }
    r->sprites.format=sprite_format;
    btp_render(r,&s,0,a);btp_render(r,&s,0,b);CHECK(!memcmp(a,b,BTP_PIXELS*sizeof *a));
    /* MAP1's border is deliberately closed during this early campaign. */
    for (unsigned pos=0;pos<64;++pos) {
        CHECK(btp_map_tile(&r->map,0,(int)pos)>=85);
        CHECK(btp_map_tile(&r->map,63,(int)pos)>=85);
        CHECK(btp_map_tile(&r->map,(int)pos,0)>=85);
        CHECK(btp_map_tile(&r->map,(int)pos,63)>=85);
    }
    uint8_t saved[BTP_STATE_BYTES];BtpState restored;
    s.tick=37;btp_world_preview(r,&s,a);btp_state_encode(&s,saved);
    CHECK(btp_state_decode(saved,sizeof saved,&r->map,&r->citadel,&restored));
    btp_world_preview(r,&restored,b);CHECK(!memcmp(a,b,BTP_PIXELS*sizeof *a));
    BtpState before=s;btp_world_preview(r,&s,a);CHECK(!memcmp(&before,&s,sizeof s));
    const char *slot="work/world-test.btp";
    CHECK(btp_save_write(slot,&s,r,&e));CHECK(btp_save_load(slot,&restored,r,&e));
    btp_world_preview(r,&restored,b);CHECK(!memcmp(a,b,BTP_PIXELS*sizeof *a));
    CHECK(remove(slot)==0);
    free(a);free(b);free(r);
    printf("PASS: %u world cache, original sector, MAP1 overlay, barrier and saved-clock assertions\n",checks);
    return 0;
}
