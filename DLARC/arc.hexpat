#include <std/mem.pat>

struct ArcHeader {
    char signature[4];
    padding[8];
    u32 magic;
};

struct FileEntry {
    char signature[4];    // "DIR "
    
    padding[4];
    u32 magic;
    u32 category;
    
    u64 timestamp1;
    u64 timestamp2;
    u32 idk;
    u8 fileSize[4] [[Comment("Size of the file in inverse bits order")]];
    u8 fileAddr[4] [[Comment("Address of the file in inverse bits order")]];
    char fileName[while($[$] != '\0')];
    padding[1];
};

struct DataHeader {
    char signature[4];    // "DAT "
};

// Full ARC File
struct ArcFile {
    ArcHeader header;
    
    // until we hit "DAT "
    FileEntry dirEntries[
        while(std::mem::find_string(0, "DAT ") > $)
    ];
    
    DataHeader dataHeader @ std::mem::find_string(0, "DAT ");
    char data[];
};

ArcFile arc @ 0;