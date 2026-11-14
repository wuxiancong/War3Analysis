// List/extract font files from a War3 MPQ via StormLib (ANSI build).
#include <stdio.h>
#include <string.h>
#include <windows.h>
#include "StormLib.h"

static void listFonts(HANDLE hMpq)
{
    SFILE_FIND_DATA fd;
    HANDLE hFind = SFileFindFirstFile(hMpq, "*", &fd, NULL);
    if (!hFind) {
        printf("SFileFindFirstFile failed: %lu\n", GetLastError());
        return;
    }
    int n = 0, fontHits = 0;
    do {
        ++n;
        const char *name = fd.cFileName;
        if (strstr(name, "ont") || strstr(name, "ONT") || strstr(name, "FRIZ") || strstr(name, "friz") ||
            strstr(name, ".ttf") || strstr(name, ".TTF") || strstr(name, ".ttc") || strstr(name, ".TTC")) {
            printf("  [%u] %s (%u bytes)\n", fd.dwFileSize, name, fd.dwFileSize);
            ++fontHits;
        }
    } while (SFileFindNextFile(hFind, &fd));
    SFileFindClose(hFind);
    printf("Listed %d files, font-like hits=%d\n", n, fontHits);
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        printf("Usage:\n");
        printf("  extract_war3_font list <mpq>\n");
        printf("  extract_war3_font extract <mpq> <out_ttf> [inner_path]\n");
        return 1;
    }

    const char *mode = argv[1];
    if (strcmp(mode, "list") == 0) {
        if (argc < 3) return 1;
        HANDLE hMpq = NULL;
        if (!SFileOpenArchive(argv[2], 0, MPQ_OPEN_READ_ONLY, &hMpq)) {
            printf("SFileOpenArchive failed: %lu\n", GetLastError());
            return 2;
        }
        listFonts(hMpq);
        SFileCloseArchive(hMpq);
        return 0;
    }

    if (strcmp(mode, "extract") != 0 || argc < 4) {
        printf("bad args\n");
        return 1;
    }

    const char *mpqPath = argv[2];
    const char *outPath = argv[3];
    const char *inner = (argc >= 5) ? argv[4] : "Fonts\\FRIZQT__.TTF";

    HANDLE hMpq = NULL;
    if (!SFileOpenArchive(mpqPath, 0, MPQ_OPEN_READ_ONLY, &hMpq)) {
        printf("SFileOpenArchive failed: %lu path=%s\n", GetLastError(), mpqPath);
        return 2;
    }

    if (!SFileHasFile(hMpq, inner)) {
        printf("HasFile(%s)=false, listing font-like entries:\n", inner);
        listFonts(hMpq);
        SFileCloseArchive(hMpq);
        return 3;
    }

    if (!SFileExtractFile(hMpq, inner, outPath, 0)) {
        printf("SFileExtractFile(%s) failed: %lu\n", inner, GetLastError());
        SFileCloseArchive(hMpq);
        return 4;
    }

    printf("Extracted OK %s -> %s\n", inner, outPath);
    SFileCloseArchive(hMpq);
    return 0;
}
