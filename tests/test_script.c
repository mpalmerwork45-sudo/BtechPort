#include "core/script.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks;
#define CHECK(expr) do { ++checks; if (!(expr)) { \
    fprintf(stderr, "%s:%d: %s failed\n", __FILE__, __LINE__, #expr); exit(1); } } while (0)

static void malformed(void)
{
    BtpBld b = {0}; BtpScriptState s; BtpError e; uint8_t story[BTP_STORY_BYTES] = {0};
    uint8_t encoded[] = {1,0,(uint8_t)((0xff ^ 233) - 41)};
    CHECK(btp_bld_decode(encoded, sizeof encoded, &b, &e));
    CHECK(b.length == 1 && b.bytes[0] == 0xff);
    btp_script_start(&s, &b, story); CHECK(s.status == BTP_SCRIPT_END);
    CHECK(!btp_bld_decode(encoded, 2, &b, &e));
    encoded[0] = 2; CHECK(!btp_bld_decode(encoded, sizeof encoded, &b, &e));
    CHECK(!btp_bld_decode(NULL, sizeof encoded, &b, &e));
    CHECK(!btp_bld_decode(encoded, BTP_BLD_MAX + 3, &b, &e));
    b.length = BTP_BLD_MAX + 1;
    btp_script_start(&s, &b, story); CHECK(s.error == BTP_SCRIPT_TRUNCATED);
    b = (BtpBld){.length=1,.bytes={0xf5}};
    btp_script_start(&s, &b, story);
    CHECK(s.status == BTP_SCRIPT_ERROR && s.error == BTP_SCRIPT_TRUNCATED && s.last_opcode == 0xf5 && s.fault_pc == 0);
    b = (BtpBld){.length=3,.bytes={0xf5,0x0c,0xff}};
    btp_script_start(&s,&b,story); CHECK(s.status == BTP_SCRIPT_NATIVE && s.pc == 2);
    btp_script_resume(&s,&b,story); CHECK(s.status == BTP_SCRIPT_NATIVE);
    btp_script_native_return(&s,&b,story); CHECK(s.status == BTP_SCRIPT_END && s.pc == 3);
    b.bytes[1] = 13; btp_script_start(&s,&b,story); CHECK(s.error == BTP_SCRIPT_OPCODE && s.fault_pc == 0);
    b = (BtpBld){.length=4,.bytes={0xf2,0xf5,0x0c,0xff}};
    btp_script_start(&s,&b,story); CHECK(s.status == BTP_SCRIPT_NATIVE && s.pc == 3 && !s.pause_units);
    b = (BtpBld){.length=1,.bytes={0xfe}};
    b.bytes[0] = 0xfe; btp_script_start(&s, &b, story); CHECK(s.error == BTP_SCRIPT_TRUNCATED);
    b.bytes[0] = 0xfc; btp_script_start(&s, &b, story); CHECK(s.error == BTP_SCRIPT_TRUNCATED);
    b = (BtpBld){.length=3,.bytes={0xf8,3,0}};
    btp_script_start(&s, &b, story); CHECK(s.error == BTP_SCRIPT_TARGET);
    b.bytes[1] = 0; btp_script_start(&s, &b, story); CHECK(s.error == BTP_SCRIPT_BUDGET);
    b = (BtpBld){.length=2,.bytes={0xfa,1}};
    btp_script_start(&s, &b, story); CHECK(s.error == BTP_SCRIPT_SCENE);
    b.bytes[0] = 0xfe; btp_script_start(&s, &b, story); CHECK(s.error == BTP_SCRIPT_FONT);
    b = (BtpBld){.length=2,.bytes={0xf9,6}};
    btp_script_start(&s, &b, story); CHECK(s.error == BTP_SCRIPT_MENU_ID);
    b.bytes[1] = 8; btp_script_start(&s, &b, story); CHECK(s.error == BTP_SCRIPT_TRUNCATED);
    b = (BtpBld){.length=13,.bytes={0xf9,8,12,0,12,0,12,0,12,0,13,0,0xff}};
    btp_script_start(&s, &b, story); CHECK(s.error == BTP_SCRIPT_TARGET);
    b.bytes[10] = 12; btp_script_start(&s, &b, story); CHECK(s.status == BTP_SCRIPT_MENU);
    CHECK(!btp_script_choose(&s, &b, 5, story) && s.status == BTP_SCRIPT_MENU);
    CHECK(btp_script_choose(&s, &b, 4, story) && s.status == BTP_SCRIPT_END);
    CHECK(!btp_script_choose(&s, &b, 0, story));
    b = (BtpBld){.length=6,.bytes={0xfc,'a',0,0xfb,0xff,0}};
    btp_script_start(&s, &b, story);
    CHECK(s.status == BTP_SCRIPT_WAIT && s.pc == 4 && s.text_offset == 1 && s.text_length == 1);
    btp_script_resume(&s, &b, story); CHECK(s.status == BTP_SCRIPT_END);
}

static void citadel(const char *dir)
{
    char path[4096]; uint8_t *bytes; size_t n; BtpBld b; BtpScriptState s; BtpError e; uint8_t story[BTP_STORY_BYTES] = {0};
    snprintf(path, sizeof path, "%s/CITADEL.BLD", dir);
    CHECK(btp_read_file(path, &bytes, &n, &e));
    CHECK(btp_bld_decode(bytes, n, &b, &e)); free(bytes);
    CHECK(b.length == 4328);
    btp_script_start(&s, &b, story);
    CHECK(s.status == BTP_SCRIPT_MENU && s.pc == 0xea && s.menu_table == 0xe0 && s.menu_id == 8);
    CHECK(s.text_offset == 6 && s.text_length == 215 && s.font == 6 && s.scene == 0);
    CHECK(btp_script_choose(&s, &b, 1, story));
    const uint16_t starts[] = {1702,1920,2175,2489,2785,2987};
    const uint16_t lengths[] = {213,250,309,291,197,329};
    const uint16_t pcs[] = {0x77e,0x87d,0x9b7,0xadf,0xba9,0xcf7};
    for (unsigned i = 0; i < 6; ++i) {
        CHECK(s.status == BTP_SCRIPT_WAIT && s.pc == pcs[i]);
        CHECK(s.text_offset == starts[i] && s.text_length == lengths[i] && s.pause_units == 50);
        btp_script_resume(&s, &b, story);
    }
    CHECK(s.status == BTP_SCRIPT_MENU && s.selected == 1 && s.pc == 0xea);
    CHECK(btp_script_choose(&s, &b, 4, story) && s.status == BTP_SCRIPT_END && s.pc == 0x10e6);
    btp_script_start(&s, &b, story);
    CHECK(btp_script_choose(&s, &b, 0, story));
    CHECK(s.status == BTP_SCRIPT_WAIT && s.pc == 0x1aa && s.text_offset == 244 && s.text_length == 180);
    CHECK(story[6] == 0 && story[22] == 0);
    btp_script_resume(&s, &b, story);
    CHECK(s.status == BTP_SCRIPT_WAIT && s.pc == 0x349 && s.text_count == 3 && s.text_length == 278);
    CHECK(story[6] == 1 && story[7] == 0 && story[21] == 0 && story[22] == 255);
    uint8_t text[BTP_BLD_MAX + 1]; CHECK(btp_script_text(&s, &b, text, sizeof text));
    CHECK(!memcmp(text, b.bytes + 428, 80) && !memcmp(text + 80, b.bytes + 514, 122) &&
          !memcmp(text + 202, b.bytes + 756, 76) && text[278] == 0);
    btp_script_resume(&s, &b, story);
    CHECK(s.status == BTP_SCRIPT_MENU && s.selected == 0 && s.text_count == 1);
    CHECK(btp_script_choose(&s, &b, 0, story));
    CHECK(s.status == BTP_SCRIPT_WAIT && s.pc == 0x424 && s.text_offset == 849 && s.text_length == 208);
    CHECK(story[6] == 1 && story[22] == 255);
    btp_script_resume(&s, &b, story); CHECK(s.status == BTP_SCRIPT_MENU);
    btp_script_start(&s, &b, story);
    CHECK(btp_script_choose(&s, &b, 2, story) && s.status == BTP_SCRIPT_WAIT);
    btp_script_resume(&s, &b, story);
    CHECK(s.status == BTP_SCRIPT_NATIVE && s.native_action == 4 && s.pc == 0xf05);
    btp_script_native_return(&s,&b,story);
    CHECK(s.status == BTP_SCRIPT_MENU && s.menu_id == 9 && s.pc == 0xf0f);
    btp_script_start(&s, &b, story);
    CHECK(btp_script_choose(&s, &b, 3, story) && s.status == BTP_SCRIPT_NATIVE && s.pc == 0x10e2 &&
          story[13] == 1 && !s.text_count);
    btp_script_native_return(&s,&b,story);
    CHECK(s.status == BTP_SCRIPT_MENU && s.selected == 3 && s.pc == 0xea && story[13] == 1);
    puts("Citadel: Hall, Katrina, concatenated text, byte changes, repeat denial, Class and Talk suspension/return.");
}

static void state_and_text(void)
{
    BtpScriptState s; uint8_t story[BTP_STORY_BYTES] = {0}, text[16];
    BtpBld b = {.length=10,.bytes={0xf4,22,255,0xf1,6,255,0xf1,6,2,0xff}};
    story[7] = 73; btp_script_start(&s, &b, story);
    CHECK(s.status == BTP_SCRIPT_END && story[22] == 255 && story[6] == 1 && story[7] == 73);
    b = (BtpBld){.length=13,.bytes={0xf7,6,9,0,0xf4,0,1,0xff,0,0xf4,0,2,0xff}};
    story[6] = 0; btp_script_start(&s, &b, story); CHECK(story[0] == 1 && s.status == BTP_SCRIPT_END);
    story[6] = 2; btp_script_start(&s, &b, story); CHECK(story[0] == 2 && s.status == BTP_SCRIPT_END);
    b.bytes[2] = b.bytes[3] = 255;
    btp_script_start(&s, &b, story); CHECK(s.error == BTP_SCRIPT_TARGET);
    story[6] = 0; btp_script_start(&s, &b, story); CHECK(s.status == BTP_SCRIPT_END);
    b = (BtpBld){.length=11,.bytes={0xf3,6,8,0,9,0,10,0,0xff,0xfb,0xff}};
    for (unsigned i = 0; i < 3; ++i) {
        story[6] = (uint8_t)i; btp_script_start(&s, &b, story);
        CHECK(s.pc == 9+i && s.status == (i == 1 ? BTP_SCRIPT_WAIT : BTP_SCRIPT_END));
    }
    /* CBW matters: 254 selects the table word two entries before its base. */
    b = (BtpBld){.length=12,.bytes={0xf8,8,0,0xff,0,0,3,0,0xf3,6,3,0}};
    story[6] = 254; btp_script_start(&s, &b, story); CHECK(s.status == BTP_SCRIPT_END && s.pc == 4);
    story[6] = 128; btp_script_start(&s, &b, story); CHECK(s.error == BTP_SCRIPT_TARGET);
    const uint8_t ops[] = {0xf1,0xf3,0xf4,0xf7};
    const uint16_t sizes[] = {3,2,3,4};
    for (unsigned i = 0; i < 4; ++i) {
        b = (BtpBld){.length=sizes[i]}; b.bytes[0] = ops[i]; b.bytes[1] = BTP_STORY_BYTES;
        btp_script_start(&s, &b, story); CHECK(s.error == BTP_SCRIPT_STATE_INDEX && s.fault_pc == 0);
        for (uint16_t length = 1; length < sizes[i]; ++length) {
            b.length = length; btp_script_start(&s, &b, story); CHECK(s.error == BTP_SCRIPT_TRUNCATED);
        }
    }
    b = (BtpBld){.length=13,.bytes={0xfc,'A','b',0,0xfc,'c',0,0xfb,0xfd,0xfc,'d',0,0xff}};
    btp_script_start(&s, &b, story);
    CHECK(s.status == BTP_SCRIPT_WAIT && s.text_count == 2 && s.text_length == 3);
    CHECK(btp_script_text(&s, &b, text, sizeof text) && !strcmp((char *)text, "Abc"));
    CHECK(!btp_script_text(&s, &b, text, 3));
    btp_script_resume(&s, &b, story);
    CHECK(s.status == BTP_SCRIPT_END && s.text_count == 1 &&
          btp_script_text(&s, &b, text, sizeof text) && !strcmp((char *)text, "d"));
    s.text[0].offset = 9000; CHECK(!btp_script_text(&s, &b, text, sizeof text));
    b = (BtpBld){.length=6,.bytes={0xfc,'a',0,0xf8,0,0}};
    btp_script_start(&s, &b, story);
    CHECK(s.error == BTP_SCRIPT_TEXT_LIMIT && s.text_count == BTP_TEXT_SPANS);
    b = (BtpBld){.length=4,.bytes={0xf4,0,1,0xff}};
    btp_script_start(&s, &b, NULL); CHECK(s.error == BTP_SCRIPT_STATE_INDEX);
}
int main(int argc, char **argv)
{
    malformed(); state_and_text();
    if (argc == 2) citadel(argv[1]);
    printf("PASS: %u script checks\n", checks); return 0;
}
