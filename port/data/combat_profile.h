#ifndef BTP_COMBAT_PROFILE_H
#define BTP_COMBAT_PROFILE_H
#include <stdint.h>
/* Versioned authored rules, separate from the extracted DOS tables and roster.
   Zero fingerprint means an older pack with only the compatibility policy. */
typedef struct {
    uint32_t fingerprint;
    uint8_t scale, minimum, short_range, medium_range, long_range;
} BtpCombatProfile;
int btp_combat_profile_load(const char *roster_path,BtpCombatProfile *profile,char error[256]);
int btp_combat_profile_lrm(unsigned weapon);
#endif
