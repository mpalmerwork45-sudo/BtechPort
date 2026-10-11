#include "core/script.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks;
#define CHECK(expr) do { ++checks; if (!(expr)) { \
    fprintf(stderr, "%s:%d: %s failed\n", __FILE__, __LINE__, #expr); exit(1); } } while (0)

static void malformed(void)
{
    BtpBld b = {0}; BtpScriptState s; BtpError e;
    uint8_t encoded[] = {1,0,(uint8_t)((0xff ^ 233) - 41)};
    CHECK(btp_bld_decode(encoded, sizeof encoded, &b, &e));
    CHECK(b.length == 1 && b.bytes[0] == 0xff);
    btp_script_start(&s, &b); CHECK(s.status == BTP_SCRIPT_END);
    CHECK(!btp_bld_decode(encoded, 2, &b, &e));
    encoded[0] = 2; CHECK(!btp_bld_decode(encoded, sizeof encoded, &b, &e));
    CHECK(!btp_bld_decode(NULL, sizeof encoded, &b, &e));
    CHECK(!btp_bld_decode(encoded, BTP_BLD_MAX + 3, &b, &e));
    b.length = BTP_BLD_MAX + 1;
    btp_script_start(&s, &b); CHECK(s.error == BTP_SCRIPT_TRUNCATED);
    b = (BtpBld){.length=1,.bytes={0xf5}};
    btp_script_start(&s, &b);
    CHECK(s.status == BTP_SCRIPT_ERROR && s.error == BTP_SCRIPT_OPCODE && s.last_opcode == 0xf5 && s.fault_pc == 0);
    b.bytes[0] = 0xfe; btp_script_start(&s, &b); CHECK(s.error == BTP_SCRIPT_TRUNCATED);
    b.bytes[0] = 0xfc; btp_script_start(&s, &b); CHECK(s.error == BTP_SCRIPT_TRUNCATED);
    b = (BtpBld){.length=3,.bytes={0xf8,3,0}};
    btp_script_start(&s, &b); CHECK(s.error == BTP_SCRIPT_TARGET);
    b.bytes[1] = 0; btp_script_start(&s, &b); CHECK(s.error == BTP_SCRIPT_BUDGET);
    b = (BtpBld){.length=2,.bytes={0xfa,1}};
    btp_script_start(&s, &b); CHECK(s.error == BTP_SCRIPT_SCENE);
    b.bytes[0] = 0xfe; btp_script_start(&s, &b); CHECK(s.error == BTP_SCRIPT_FONT);
    b = (BtpBld){.length=2,.bytes={0xf9,7}};
    btp_script_start(&s, &b); CHECK(s.error == BTP_SCRIPT_MENU_ID);
    b.bytes[1] = 8; btp_script_start(&s, &b); CHECK(s.error == BTP_SCRIPT_TRUNCATED);
    b = (BtpBld){.length=13,.bytes={0xf9,8,12,0,12,0,12,0,12,0,13,0,0xff}};
    btp_script_start(&s, &b); CHECK(s.error == BTP_SCRIPT_TARGET);
    b.bytes[10] = 12; btp_script_start(&s, &b); CHECK(s.status == BTP_SCRIPT_MENU);
    CHECK(!btp_script_choose(&s, &b, 5) && s.status == BTP_SCRIPT_MENU);
    CHECK(btp_script_choose(&s, &b, 4) && s.status == BTP_SCRIPT_END);
    CHECK(!btp_script_choose(&s, &b, 0));
    b = (BtpBld){.length=6,.bytes={0xfc,'a',0,0xfb,0xff,0}};
    btp_script_start(&s, &b);
    CHECK(s.status == BTP_SCRIPT_WAIT && s.pc == 4 && s.text_offset == 1 && s.text_length == 1);
    btp_script_resume(&s, &b); CHECK(s.status == BTP_SCRIPT_END);
}

static void citadel(const char *dir)
{
    char path[4096]; uint8_t *bytes; size_t n; BtpBld b; BtpScriptState s; BtpError e;
    snprintf(path, sizeof path, "%s/CITADEL.BLD", dir);
    CHECK(btp_read_file(path, &bytes, &n, &e));
    CHECK(btp_bld_decode(bytes, n, &b, &e)); free(bytes);
    CHECK(b.length == 4328);
    btp_script_start(&s, &b);
    CHECK(s.status == BTP_SCRIPT_MENU && s.pc == 0xea && s.menu_table == 0xe0 && s.menu_id == 8);
    CHECK(s.text_offset == 6 && s.text_length == 215 && s.font == 6 && s.scene == 0);
    CHECK(btp_script_choose(&s, &b, 1));
    const uint16_t starts[] = {1702,1920,2175,2489,2785,2987};
    const uint16_t lengths[] = {213,250,309,291,197,329};
    const uint16_t pcs[] = {0x77e,0x87d,0x9b7,0xadf,0xba9,0xcf7};
    for (unsigned i = 0; i < 6; ++i) {
        CHECK(s.status == BTP_SCRIPT_WAIT && s.pc == pcs[i]);
        CHECK(s.text_offset == starts[i] && s.text_length == lengths[i] && s.pause_units == 50);
        btp_script_resume(&s, &b);
    }
    CHECK(s.status == BTP_SCRIPT_MENU && s.selected == 1 && s.pc == 0xea);
    CHECK(btp_script_choose(&s, &b, 4) && s.status == BTP_SCRIPT_END && s.pc == 0x10e6);
    btp_script_start(&s, &b);
    CHECK(!btp_script_choose(&s, &b, 0) && s.error == BTP_SCRIPT_OPCODE && s.last_opcode == 0xf3 && s.fault_pc == 0xeb);
    btp_script_start(&s, &b);
    CHECK(!btp_script_choose(&s, &b, 2) && s.error == BTP_SCRIPT_OPCODE && s.last_opcode == 0xf7);
    btp_script_start(&s, &b);
    CHECK(!btp_script_choose(&s, &b, 3) && s.error == BTP_SCRIPT_OPCODE && s.last_opcode == 0xf4);
    puts("Citadel: authentic menu, six Hall texts, retained selection, exit, explicit unsupported branches.");
}
int main(int argc, char **argv)
{
    malformed();
    if (argc == 2) citadel(argv[1]);
    printf("PASS: %u script checks\n", checks); return 0;
}
