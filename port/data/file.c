#include "data/file.h"
#include <errno.h>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#include <sys/stat.h>
#endif
FILE *btp_file_create(const char *path)
{
#ifdef _WIN32
    int fd=_open(path,_O_WRONLY|_O_CREAT|_O_EXCL|_O_BINARY,_S_IREAD|_S_IWRITE);
    FILE *f=fd<0 ? NULL : _fdopen(fd,"wb");
    if (fd>=0 && !f) { int saved=errno;(void)_close(fd);(void)remove(path);errno=saved; }
    return f;
#else
    return fopen(path,"wbx");
#endif
}
