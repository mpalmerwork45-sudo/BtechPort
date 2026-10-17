#ifndef BTP_FILE_H
#define BTP_FILE_H
#include <stdio.h>
/* Exclusive creation on both libc and MSVCRT. A failed export preserves an
   existing author's file even when another process creates it concurrently. */
FILE *btp_file_create(const char *path);
#endif
