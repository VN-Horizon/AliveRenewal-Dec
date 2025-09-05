# DLARC Modder / Reader

Extract and edit .arc resources from the game.

```
ArcHeader:
  - 4-byte signature
  - 8-byte padding
  - 32-bit magic number

FileEntry (DIR):
  - 4-byte "DIR " signature
  - 4-byte padding
  - 32-bit magic
  - 32-bit category
  - 64-bit timestamp 1
  - 64-bit timestamp 2
  - 4-byte file size (little endian)
  - 4-byte file address (little endian)
  - Null-terminated filename
  - 1-byte padding

DataBlock (DAT):
  - 4-byte "DAT " signature
  - 4-byte padding
  - 64-bit magic
  - Raw file data
```
