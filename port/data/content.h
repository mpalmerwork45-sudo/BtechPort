#ifndef BTP_CONTENT_H
#define BTP_CONTENT_H
#include "data/resources.h"

typedef enum {
    BTP_CONTENT_NONE,
    BTP_CONTENT_ORIGINAL_DOS_103,
    BTP_CONTENT_UPDATED,
    BTP_CONTENT_PROJECT
} BtpContentProfile;

/* Paths are borrowed only while loading. Keep original cache inputs explicit:
   a future package reader must not silently fall back to the DOS executable. */
typedef struct {
    const char *directory, *dialogue, *combat, *world;
} BtpOriginalContentPaths;

/* Initialize to {0}. This context owns its heap resources; do not copy it.
   Gameplay borrows resources while the context lives. Profile identity belongs
   to loaded content, not the original serialized BtpState or GAME records. */
typedef struct {
    BtpContentProfile profile;
    BtpResources *resources;
} BtpContent;

/* Failure preserves an existing context. Success replaces it and invalidates
   old resource pointers: load before starting a session, not during a battle. */
int btp_content_load_original(BtpContent *content,
    const BtpOriginalContentPaths *paths, BtpError *error);
void btp_content_close(BtpContent *content);
int btp_content_select(BtpContent *content,BtpContentProfile profile,
    const char *roster_path,BtpError *error);
int btp_content_load_project(BtpContent *content,const char *directory,
    const BtpOriginalContentPaths *dependency,BtpError *error);
#endif
