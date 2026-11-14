#include <stdio.h>
#include <string.h>
#include <windows.h>
#include "StormLib.h"
int main(int argc, char**argv){
  HANDLE h=NULL; if(!SFileOpenArchive(argv[1],0,MPQ_OPEN_READ_ONLY,&h)){printf("open fail %lu\n",GetLastError());return 1;}
  SFILE_FIND_DATA fd; HANDLE f=SFileFindFirstFile(h,"*",&fd,NULL);
  if(!f){printf("find fail\n");return 2;}
  do{
    if(strstr(fd.cFileName,"kin")||strstr(fd.cFileName,"KIN")||strstr(fd.cFileName,"onts")||strstr(fd.cFileName,"ONTS")||strstr(fd.cFileName,".ttf")||strstr(fd.cFileName,".TTF"))
      printf("%s\n", fd.cFileName);
  }while(SFileFindNextFile(f,&fd));
  SFileFindClose(f); SFileCloseArchive(h); return 0;
}
