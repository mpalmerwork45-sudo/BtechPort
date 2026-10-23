/* Independent synthetic BLD compiler tests; no original assets required. */
#include "data/chi_scripts.h"
#include "data/chi.h"
#include "core/script.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static BtpError error;
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"BLD compiler line %d: %s (%s)\n",__LINE__,#x,error.text);exit(1); } } while (0)
static BtpResources *resources;
static BtpChiScripts *scripts;
static const uint8_t baseline[]={255,170,187};
static int load(const char *body,const char *raw)
{
    btp_chi_scripts_free(scripts);scripts=calloc(1,sizeof *scripts);CHECK(scripts);
    memset(resources,0,sizeof *resources);
    BtpDigest hash,digest;uint8_t bytes[32];char hex[65];btp_digest_start(&hash);btp_digest_add(&hash,baseline,sizeof baseline);btp_digest_finish(&hash,bytes);
    for (unsigned i=0;i<32;++i) snprintf(hex+2*i,3,"%02x",bytes[i]);
    FILE *f=fopen("chi-scripts-test.json","wb");CHECK(f);
    fputs("{\"format\":\"btp-chi-scripts-v1\",\"schema_version\":1,\"programs\":[",f);
    for (unsigned slot=0;slot<26;++slot) {
        BtpBld *b=&resources->buildings[slot];b->length=sizeof baseline;memcpy(b->bytes,baseline,sizeof baseline);
        fprintf(f,"%s{\"id\":\"test:p%u\",\"name\":\"Synthetic\",\"resource\":\"%s\",\"building\":%u,\"baseline_sha256\":\"%s\",\"entry\":\"test:%s\",\"nodes\":[",
            slot ? "," : "",slot,btp_chi_resource_name(27+slot),slot,hex,!slot && *body ? "start" : "end");
        if (!slot) fputs(body,f);
        fprintf(f,"{\"id\":\"test:end\",\"op\":\"end\",\"origin\":0,\"original_size\":1},"
            "{\"id\":\"test:data\",\"op\":\"data\",\"origin\":1,\"original_size\":2,\"bytes\":\"%s\"}]}",!slot ? raw : "aabb");
    }
    fputs("]}",f);CHECK(!fclose(f));btp_digest_start(&digest);error.text[0]=0;
    int ok=btp_chi_scripts_load(".","chi-scripts-test.json",scripts,resources,&digest,&error);
    CHECK(!remove("chi-scripts-test.json"));return ok;
}
int main(void)
{
    resources=calloc(1,sizeof *resources);CHECK(resources);
    CHECK(load("","aabb"));CHECK(resources->training.length==3 && !memcmp(resources->training.bytes,baseline,3));
    const char *valid="{\"id\":\"test:start\",\"op\":\"set\",\"index\":0,\"value\":255},"
        "{\"id\":\"test:add\",\"op\":\"add\",\"index\":0,\"value\":1},"
        "{\"id\":\"test:condition\",\"op\":\"if\",\"index\":0,\"target\":\"test:wrong\"},"
        "{\"id\":\"test:text\",\"op\":\"text\",\"text\":\"Own dialogue\\r\\u000e\"},"
        "{\"id\":\"test:menu\",\"op\":\"menu\",\"menu\":24,\"targets\":[\"test:end\",\"test:wrong\"]},"
        "{\"id\":\"test:wrong\",\"op\":\"set\",\"index\":1,\"value\":9},";
    CHECK(load(valid,"aabb"));uint8_t story[BTP_STORY_BYTES]={0};BtpScriptState state;
    btp_script_start(&state,&resources->training,story);CHECK(state.status==BTP_SCRIPT_MENU && !story[0] && !story[1]);
    CHECK(state.text_length==14 && resources->training.bytes[state.text_offset+13]==14);
    CHECK(btp_script_choose(&state,&resources->training,1,story));CHECK(state.status==BTP_SCRIPT_END && story[1]==9);
    CHECK(btp_bld_offset(&resources->training,0)>0 && btp_bld_after(&resources->training,1)==resources->training.length-2u);
    const char *bad[]={
        "{\"id\":\"test:start\",\"op\":\"jump\",\"target\":\"test:missing\"},",
        "{\"id\":\"test:start\",\"op\":\"jump\",\"target\":\"test:data\"},",
        "{\"id\":\"test:start\",\"op\":\"jump\",\"target\":\"test:start\"},",
        "{\"id\":\"test:start\",\"op\":\"set\",\"index\":100,\"value\":0},",
        "{\"id\":\"test:start\",\"op\":\"native\",\"action\":12},",
        "{\"id\":\"test:start\",\"op\":\"menu\",\"menu\":24,\"targets\":[\"test:end\"]},",
        "{\"id\":\"test:start\",\"op\":\"call\",\"target\":\"test:start\"},",
        "{\"id\":\"test:start\",\"op\":\"text\",\"text\":\"bad\\u0000\"},",
        "{\"id\":\"test:start\",\"op\":\"text\"},"};
    for (unsigned i=0;i<sizeof bad/sizeof *bad;++i) { CHECK(!load(bad[i],"aabb"));CHECK(strstr(error.text,"test:start") || strstr(error.text,"native") || strstr(error.text,"escapes")); }
    CHECK(!load("","aabc"));CHECK(strstr(error.text,"byte-identical"));
    /* A changing conditional cycle is not statically assumed infinite. The
       native instruction budget faults visibly instead of hanging a tick. */
    CHECK(load("{\"id\":\"test:start\",\"op\":\"set\",\"index\":0,\"value\":1},"
        "{\"id\":\"test:loop\",\"op\":\"if\",\"index\":0,\"target\":\"test:loop\"},","aabb"));
    memset(story,0,sizeof story);btp_script_start(&state,&resources->training,story);
    CHECK(state.status==BTP_SCRIPT_ERROR && state.error==BTP_SCRIPT_BUDGET);
    btp_chi_scripts_free(scripts);free(resources);puts("Typed BLD compilation, labels, byte arithmetic, menu edits, original data and bounded failures pass.");return 0;
}
