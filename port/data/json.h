#ifndef BTP_JSON_H
#define BTP_JSON_H
#include <stddef.h>
#include <stdint.h>

/* Shared, bounded authoring reader. Strings are printable ASCII (the current
   game's font); integers are unsigned. No coercion or ignored object fields. */
typedef struct {
    char *key,*text;
    uint32_t number;
    unsigned parent,first,next,index;
    unsigned char type,used;
} BtpJsonNode;
typedef struct {
    char *bytes;
    BtpJsonNode *nodes;
    unsigned count,limit;
    uint8_t source_digest[32]; /* Exact snapshot, before in-place string decoding. */
    const char *file;
    char *error;
    unsigned native_text; /* Opt-in CHI text escapes; other formats remain strict. */
} BtpJson;
int btp_json_load(BtpJson *json,const char *path,char error[256]);
int btp_json_load_chi_text(BtpJson *json,const char *path,char error[256]);
/* Pixel libraries/world documents have an explicit larger bound; ordinary
   manifests and definitions retain their original one-megabyte contract. */
int btp_json_load_large(BtpJson *json,const char *path,char error[256]);
void btp_json_close(BtpJson *json);
unsigned btp_json_field(BtpJson *json,unsigned object,const char *key);
unsigned btp_json_optional(BtpJson *json,unsigned object,const char *key);
int btp_json_done(BtpJson *json,unsigned object);
int btp_json_error(BtpJson *json,unsigned node,const char *message);
int btp_json_string(BtpJson *json,unsigned node,char *out,size_t capacity);
int btp_json_uint(BtpJson *json,unsigned node,unsigned low,unsigned high,unsigned *out);
int btp_json_type(BtpJson *json,unsigned node,char type);
int btp_content_id(const char *value,int namespaced);
#endif
