#include "data/file.h"
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#include <windows.h>
#include <direct.h>
#include <wchar.h>
static wchar_t *wide(const char *text)
{
    int count=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,text,-1,NULL,0);
    if(!count) { errno=EINVAL;return NULL; }
    wchar_t *value=malloc((size_t)count*sizeof *value);
    if(!value) { errno=ENOMEM;return NULL; }
    if(!MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,text,-1,value,count)) { free(value);errno=EINVAL;return NULL; }
    return value;
}
#endif
FILE *btp_fopen(const char *path,const char *mode)
{
#ifdef _WIN32
    wchar_t *p=wide(path),*m=wide(mode);FILE *file=p && m ? _wfopen(p,m) : NULL;
    free(p);free(m);return file;
#else
    return fopen(path,mode);
#endif
}
int btp_file_remove(const char *path)
{
#ifdef _WIN32
    wchar_t *p=wide(path);int result=p ? _wremove(p) : -1;free(p);return result;
#else
    return remove(path);
#endif
}
int btp_file_rename(const char *from,const char *to)
{
#ifdef _WIN32
    wchar_t *a=wide(from),*b=wide(to);int result=a && b ? _wrename(a,b) : -1;free(a);free(b);return result;
#else
    return rename(from,to);
#endif
}
int btp_file_replace(const char *from,const char *to)
{
#ifdef _WIN32
    wchar_t *a=wide(from),*b=wide(to);int result=a && b && MoveFileExW(a,b,MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH) ? 0 : -1;
    free(a);free(b);return result;
#else
    return rename(from,to);
#endif
}
int btp_file_mkdir(const char *path)
{
#ifdef _WIN32
    wchar_t *p=wide(path);int result=p ? _wmkdir(p) : -1;free(p);return result;
#else
    return mkdir(path,0700);
#endif
}
int btp_file_entry(const char *path,const char *leaf)
{
#ifdef _WIN32
    wchar_t *p=wide(path),*l=wide(leaf);WIN32_FIND_DATAW info;int result=0;
    HANDLE found=p && l ? FindFirstFileW(p,&info) : INVALID_HANDLE_VALUE;
    if(found!=INVALID_HANDLE_VALUE) {
        if(!wcscmp(info.cFileName,l) && !(info.dwFileAttributes&(FILE_ATTRIBUTE_REPARSE_POINT|FILE_ATTRIBUTE_DEVICE)))
            result=info.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY ? 2 : 1;
        FindClose(found);
    }
    free(p);free(l);return result;
#else
    (void)path;(void)leaf;return 0; /* POSIX callers retain lstat/readdir. */
#endif
}
FILE *btp_file_create(const char *path)
{
#ifdef _WIN32
    wchar_t *p=wide(path);if(!p)return NULL;
    int fd=_wopen(p,_O_WRONLY|_O_CREAT|_O_EXCL|_O_BINARY,_S_IREAD|_S_IWRITE);free(p);
    FILE *f=fd<0 ? NULL : _fdopen(fd,"wb");
    if (fd>=0 && !f) { int saved=errno;(void)_close(fd);(void)btp_file_remove(path);errno=saved; }
    return f;
#else
    return fopen(path,"wbx");
#endif
}
