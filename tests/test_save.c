#include "data/save.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks;
#define CHECK(x) do { ++checks; if (!(x)) { fprintf(stderr,"FAIL %s:%d: %s\n",__FILE__,__LINE__,#x); exit(1); } } while (0)
static const char *slot = "btp-save-test.btp";
static void same(const BtpState *a, const BtpState *b)
{
    uint8_t one[BTP_STATE_BYTES], two[BTP_STATE_BYTES];
    btp_state_encode(a,one); btp_state_encode(b,two); CHECK(!memcmp(one,two,sizeof one));
}
static void put(const uint8_t *bytes, size_t n)
{
    FILE *f = fopen(slot,"wb"); CHECK(f != NULL);
    CHECK(fwrite(bytes,1,n,f) == n); CHECK(!fclose(f));
}
static size_t get(uint8_t *bytes, size_t cap)
{
    FILE *f = fopen(slot,"rb"); CHECK(f != NULL);
    size_t n = fread(bytes,1,cap,f); CHECK(!ferror(f)); CHECK(!fclose(f)); return n;
}
static void synthetic(BtpResources *r)
{
    r->map.width = r->map.height = 64;
    BtpState original, current; btp_start(&original); original.npc = (BtpNpcState){0};
    BtpError error;
    CHECK(btp_save_write(slot,&original,r,&error));
    btp_start(&current); current.credits = 7;
    CHECK(btp_save_load(slot,&current,r,&error)); same(&original,&current);
    uint8_t saved[16+BTP_STATE_BYTES+1], bad[sizeof saved], again[sizeof saved];
    size_t n = get(saved,sizeof saved); CHECK(n == 16+BTP_STATE_BYTES);
    CHECK(!memcmp(saved,"BTS1",4));
    const unsigned offsets[] = {0,4,8,12,16,28,16+356};
    for (unsigned i = 0; i < sizeof offsets/sizeof offsets[0]; ++i) {
        memcpy(bad,saved,n); bad[offsets[i]] ^= 1; put(bad,n);
        CHECK(!btp_save_load(slot,&current,r,&error)); same(&original,&current);
    }
    put(saved,n-1); CHECK(!btp_save_load(slot,&current,r,&error)); same(&original,&current);
    memcpy(bad,saved,n); bad[n] = 0; put(bad,n+1);
    CHECK(!btp_save_load(slot,&current,r,&error)); same(&original,&current);
    CHECK(!btp_save_load("btp-save-missing-directory/slot.btp",&current,r,&error)); same(&original,&current);
    put(saved,n);
    FILE *pending = fopen("btp-save-test.btp.tmp","wb"); CHECK(pending != NULL);
    CHECK(fwrite("KEEP",1,4,pending) == 4); CHECK(!fclose(pending));
    current.credits = 9; CHECK(!btp_save_write(slot,&current,r,&error));
    CHECK(get(again,sizeof again) == n && !memcmp(saved,again,n));
    pending = fopen("btp-save-test.btp.tmp","rb"); CHECK(pending != NULL);
    CHECK(fread(again,1,4,pending) == 4 && !memcmp(again,"KEEP",4)); CHECK(!fclose(pending));
    CHECK(!remove("btp-save-test.btp.tmp"));
    CHECK(btp_save_write(slot,&current,r,&error));
    BtpState loaded; CHECK(btp_save_load(slot,&loaded,r,&error)); same(&current,&loaded);
    current.bank.phase = 4; CHECK(!btp_save_write(slot,&current,r,&error));
    CHECK(btp_save_load(slot,&current,r,&error)); same(&current,&loaded);
    CHECK(!btp_save_write("btp-save-missing-directory/slot.btp",&current,r,&error));
    char long_path[4096]; memset(long_path,'x',sizeof long_path-1); long_path[sizeof long_path-1] = 0;
    CHECK(!btp_save_write(long_path,&current,r,&error));
    CHECK(!remove(slot));
}
static void roundtrip(const BtpState *s, const BtpResources *r)
{
    BtpError error; BtpState loaded;
    CHECK(btp_save_write(slot,s,r,&error)); CHECK(btp_save_load(slot,&loaded,r,&error)); same(s,&loaded);
    for (unsigned a = BTP_IDLE; a <= BTP_CLEAR_INPUT; ++a) {
        BtpState one = *s, two = loaded;
        btp_game_tick(&one,r,(BtpAction)a); btp_game_tick(&two,r,(BtpAction)a); same(&one,&two);
    }
}
static void corpus(const BtpResources *r)
{
    const char *names[] = {"reference-bank","reference-bank-rates","citadel-katrina","reference-shops"};
    unsigned snapshots = 0;
    for (unsigned i = 0; i < sizeof names/sizeof names[0]; ++i) {
        char path[256]; snprintf(path,sizeof path,"tests/fixtures/%s.actions",names[i]);
        FILE *f = fopen(path,"r"); CHECK(f != NULL);
        BtpState s; btp_start(&s); char line[64]; unsigned previous = 255;
        while (fgets(line,sizeof line,f)) {
            line[strcspn(line,"\r\n")] = 0; BtpAction a; CHECK(btp_action_parse(line,&a));
            btp_game_tick(&s,r,a);
            unsigned phase = s.mode+4u*s.script.status+32u*s.bank.phase;
            if (phase != previous || s.bank.phase == BTP_BANK_AMOUNT) {
                roundtrip(&s,r); ++snapshots; previous = phase;
            }
        }
        CHECK(!ferror(f)); CHECK(!fclose(f));
    }
    for (unsigned slot_id = 3; slot_id <= 4; ++slot_id) {
        BtpState s; btp_start_shop_conversation_checkpoint(&s,r,slot_id);
        btp_game_tick(&s,r,BTP_ACCEPT); roundtrip(&s,r);
        btp_game_tick(&s,r,BTP_ACCEPT); roundtrip(&s,r); snapshots += 2;
    }
    CHECK(!remove(slot));
    printf("Save files: %u authentic replay phase/input snapshots, every action continues identically.\n",snapshots);
}
int main(int argc, char **argv)
{
    BtpResources *r = calloc(1,sizeof *r); CHECK(r != NULL); synthetic(r);
    if (argc > 1) {
        BtpError error; CHECK(btp_resources_load(argv[1],r,&error));
        CHECK(btp_dialogue_load("work/talk-data.bin",&r->dialogue,&error)); corpus(r);
    }
    free(r); printf("PASS: %u save-file checks\n",checks); return 0;
}
