#ifndef BTP_FILE_H
#define BTP_FILE_H
#include <stdio.h>
/* Engine paths are UTF-8, including command-line paths on Windows. Package
   relative names retain their stricter portable-ASCII contract. */
FILE *btp_fopen(const char *path,const char *mode);
int btp_file_remove(const char *path);
int btp_file_rename(const char *from,const char *to);
int btp_file_replace(const char *from,const char *to);
int btp_file_mkdir(const char *path);
/* Exact basename match, regular file=1/directory=2; no reparse entries. */
int btp_file_entry(const char *path,const char *leaf);
/* Exclusive creation on both libc and MSVCRT. A failed export preserves an
   existing author's file even when another process creates it concurrently. */
FILE *btp_file_create(const char *path);
#endif
