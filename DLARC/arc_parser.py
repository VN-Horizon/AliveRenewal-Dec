import struct
from typing import List, Tuple, Optional

class ArcHeader:
    """ARC file header structure"""
    def __init__(self, signature: bytes, magic: int):
        self.signature = signature
        self.magic = magic
    
    @classmethod
    def from_bytes(cls, data: bytes, offset: int = 0) -> 'ArcHeader':
        """Parse ARC header from binary data"""
        signature = data[offset:offset+4]
        magic = struct.unpack('<I', data[offset+12:offset+16])[0]
        return cls(signature, magic)

class FileEntry:
    """File entry structure in ARC file"""
    def __init__(self, signature: bytes, magic: int, category: int, 
                 timestamp1: int, timestamp2: int, file_size: int, 
                 file_addr: int, file_name: str):
        self.signature = signature
        self.magic = magic
        self.category = category
        self.timestamp1 = timestamp1
        self.timestamp2 = timestamp2
        self.file_size = file_size
        self.file_addr = file_addr
        self.file_name = file_name

    def __str__(self):
        return f"FileEntry(magic={{0x{self.magic:08X}}}, category={{0x{self.category:08X}}}, file_size={{0x{self.file_size:08X}}}, file_addr={{0x{self.file_addr:08X}}}, file_name={self.file_name})"
    
    @classmethod
    def from_bytes(cls, data: bytes, offset: int) -> Tuple['FileEntry', int]:
        """Parse file entry from binary data, returns (FileEntry, next_offset)"""
        signature = data[offset:offset+4]
        
        magic = struct.unpack('<I', data[offset+8:offset+12])[0]
        category = struct.unpack('<I', data[offset+12:offset+16])[0]
        
        timestamp1 = struct.unpack('<Q', data[offset+16:offset+24])[0]
        timestamp2 = struct.unpack('<Q', data[offset+24:offset+32])[0]
        
        size_raw = data[offset+32:offset+36]
        addr_raw = data[offset+36:offset+40]
        
        file_size = int.from_bytes(size_raw, byteorder='little')
        file_addr = int.from_bytes(addr_raw, byteorder='little')
        
        name_start = offset + 40
        name_end = name_start
        while name_end < len(data) and data[name_end] != 0:
            name_end += 1
        
        file_name = data[name_start:name_end].decode('shift_jis', errors='ignore')
        
        next_offset = name_end + 2
        
        return cls(signature, magic, category, timestamp1, timestamp2, 
                  file_size, file_addr, file_name), next_offset
    
class DataBlock:
    """Data block structure in ARC file"""
    def __init__(self, signature: bytes, magic: int, data: bytes):
        self.signature = signature
        self.magic = magic
        self.data = data

    def __str__(self):
        return f"DataBlock()"
    
    @classmethod
    def from_bytes(cls, data: bytes, offset: int) -> Tuple['DataBlock', int]:
        """Parse data block from binary data, returns (DataBlock, next_offset)"""
        signature = data[offset:offset+4]
        magic = struct.unpack('<I', data[offset+8:offset+12])[0]
        data = data[offset+12:]
        return cls(signature, magic, data), offset + len(data)

class ArcFile:
    """Complete ARC file structure"""
    def __init__(self, header: ArcHeader, file_entries: List[FileEntry], data_blocks: List[DataBlock], raw_data: bytes):
        self.header = header
        self.file_entries = file_entries
        self.data_blocks = data_blocks
        self.raw_data = raw_data
    
    @classmethod
    def parse(cls, file_path: str) -> 'ArcFile':
        """Parse complete ARC file from disk"""
        with open(file_path, 'rb') as f:
            data = f.read()
        
        header = ArcHeader.from_bytes(data, 0)
        
        file_entries = []
        data_blocks = []
        offset = 16  
        while offset < len(data) - 4:
            if data[offset:offset+4] == b'DAT ':
                break
            
            if data[offset:offset+4] == b'DIR ':
                entry, next_offset = FileEntry.from_bytes(data, offset)
                file_entries.append(entry)
                print(entry)
                offset = next_offset - 1

                dataBlock = data[entry.file_addr-16:entry.file_addr + entry.file_size]
                print(dataBlock[0:4])

                if dataBlock[0:4] == b'DAT ':
                    block, next_offset = DataBlock.from_bytes(dataBlock, 0)
                    print(block)
                    data_blocks.append(block)
                else:
                    print("Warning: Data block not valid")
            else:
                offset += 1
        
        return cls(header, file_entries, data_blocks, data)
    
    def get_file_data(self, file_entry: FileEntry) -> Optional[bytes]:
        """Extract file data for a given file entry using file_addr and file_size"""
        if (file_entry.file_addr + file_entry.file_size <= len(self.raw_data)):
            return self.raw_data[file_entry.file_addr:file_entry.file_addr + file_entry.file_size]
        return None
    
    def list_files(self) -> List[Tuple[str, int, int]]:
        """List all files with name, size, and address"""
        return [(entry.file_name, entry.file_size, entry.file_addr) for entry in self.file_entries]

    def regenerate(self) -> bytes:
        """Regenerate the ARC file and return new binary data"""
        result = bytearray()
        
        result.extend(self.header.signature)
        result.extend(b'\x00' * 8)
        result.extend(struct.pack('<I', self.header.magic))
        
        for entry in self.file_entries:
            result.extend(b'DIR ')
            
            result.extend(b'\x00' * 4)
            
            result.extend(struct.pack('<I', entry.magic))
            result.extend(struct.pack('<I', entry.category))
            result.extend(struct.pack('<Q', entry.timestamp1))
            result.extend(struct.pack('<Q', entry.timestamp2))
            
            result.extend(struct.pack('<I', entry.file_size))
            result.extend(struct.pack('<I', entry.file_addr))
            
            result.extend(entry.file_name.encode('shift_jis'))
            result.extend(b'\x00')
        
        for block in self.data_blocks:
            result.extend(b'DAT ')
            
            result.extend(b'\x00' * 4)
            
            result.extend(struct.pack('<I', block.magic))
            
            result.extend(block.data)
        
        return bytes(result)
    
    def replace_file_data(self, file_entry: FileEntry, new_data: bytes) -> bool:
        """Replace file data and update addresses"""
        try:
            file_index = None
            for i, entry in enumerate(self.file_entries):
                if entry == file_entry:
                    file_index = i
                    break
            
            if file_index is None:
                return False
            
            size_difference = len(new_data) - file_entry.file_size
            
            file_entry.file_size = len(new_data)
            
            if file_index < len(self.data_blocks):
                self.data_blocks[file_index].data = new_data
            
            if size_difference != 0:
                self._shift_subsequent_files(file_index, size_difference)
            
            return True
            
        except Exception as e:
            print(f"Error replacing file data: {e}")
            return False
    
    def _shift_subsequent_files(self, start_index: int, size_difference: int):
        """Shift file addresses for files after the specified index"""
        if size_difference == 0:
            return
        
        for i in range(start_index + 1, len(self.file_entries)):
            self.file_entries[i].file_addr += size_difference
