#ifndef BTP_DIGEST_H
#define BTP_DIGEST_H
#include <stdint.h>
#include <stddef.h>
/* SHA-256 identifies exact project input bytes; it is not a signature or an
   assertion that a package is trusted. */
typedef struct { uint32_t h[8];uint64_t bytes;unsigned used;uint8_t block[64]; } BtpDigest;
void btp_digest_start(BtpDigest *digest);
void btp_digest_add(BtpDigest *digest,const void *bytes,size_t length);
void btp_digest_finish(BtpDigest *digest,uint8_t result[32]);
#endif
