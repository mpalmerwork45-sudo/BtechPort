/* Windows' narrow CRT argv uses the user's legacy code page. Decode the OS
   command line explicitly so the engine and Python tools share UTF-8 paths. */
#ifdef main
#undef main
#endif
#include <windows.h>
#include <shellapi.h>
#include <stdio.h>
#include <stdlib.h>
int btp_utf8_main(int argc,char **argv);
int main(void)
{
    int argc=0;wchar_t **wide=CommandLineToArgvW(GetCommandLineW(),&argc);
    if(!wide)return 1;
    char **argv=calloc((size_t)argc+1,sizeof *argv);int result=1;
    if(!argv) { LocalFree(wide);return 1; }
    for(int i=0;i<argc;++i) {
        int count=WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,wide[i],-1,NULL,0,NULL,NULL);
        if(!count || !(argv[i]=malloc((size_t)count)) || !WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,wide[i],-1,argv[i],count,NULL,NULL))goto done;
    }
    result=btp_utf8_main(argc,argv);
done:
    for(int i=0;i<argc;++i)free(argv[i]);
    free(argv);LocalFree(wide);return result;
}
