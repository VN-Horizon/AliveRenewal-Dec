import os
import shutil
from typing import List, Tuple, Optional
from arc_parser import ArcFile, FileEntry, DataBlock

class ArcExtractor:
    """Handles extraction of files from ARC archives"""
    
    def __init__(self, arc_file: ArcFile):
        self.arc_file = arc_file
    
    def extract_file(self, file_entry: FileEntry, output_path: str) -> bool:
        """Extract a single file from the ARC archive"""
        try:
            file_data = self.arc_file.get_file_data(file_entry)
            if file_data is None:
                return False
            
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            with open(output_path, 'wb') as f:
                f.write(file_data)
            
            return True
        except Exception as e:
            print(f"Error extracting {file_entry.file_name}: {e}")
            return False
    
    def extract_all_files(self, output_dir: str) -> Tuple[int, int]:
        """Extract all files from the ARC archive"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        success_count = 0
        total_count = len(self.arc_file.file_entries)
        
        for file_entry in self.arc_file.file_entries:
            output_path = os.path.join(output_dir, file_entry.file_name)
            
            if self.extract_file(file_entry, output_path):
                success_count += 1
        
        return success_count, total_count
    
    def extract_selected_files(self, selected_files: List[FileEntry], output_dir: str) -> Tuple[int, int]:
        """Extract selected files from the ARC archive"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        success_count = 0
        total_count = len(selected_files)
        
        for file_entry in selected_files:
            output_path = os.path.join(output_dir, file_entry.file_name)
            
            if self.extract_file(file_entry, output_path):
                success_count += 1
        
        return success_count, total_count
    
    def get_file_info(self) -> List[Tuple[str, str, str]]:
        """Get detailed information about all files"""
        file_info = []
        for entry in self.arc_file.file_entries:
            if entry.file_size < 1024:
                size_str = f"{entry.file_size} B"
            elif entry.file_size < 1024 * 1024:
                size_str = f"{entry.file_size / 1024:.1f} KB"
            else:
                size_str = f"{entry.file_size / (1024 * 1024):.1f} MB"
            
            addr_hex = f"0x{entry.file_addr:08X}"
            
            file_info.append((
                entry.file_name,
                addr_hex,
                size_str
            ))
        
        return file_info
    
    def regenerate_arc_file(self, output_path: str) -> bool:
        """Regenerate the ARC file and save it to the specified path"""
        try:
            new_data = self.arc_file.regenerate()
            
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            with open(output_path, 'wb') as f:
                f.write(new_data)
            
            return True
        except Exception as e:
            print(f"Error regenerating ARC file: {e}")
            return False

    def replace_file(self, file_entry: FileEntry, new_file_path: str) -> bool:
        """Replace a file in the ARC file with a new file"""
        try:
            with open(new_file_path, 'rb') as f:
                new_file_data = f.read()
            
            success = self.arc_file.replace_file_data(file_entry, new_file_data)
            
            if success:
                print(f"Successfully replaced file: {file_entry.file_name}")
                print(f"New size: {file_entry.file_size} bytes")
                return True
            else:
                print(f"Failed to replace file: {file_entry.file_name}")
                return False
                
        except Exception as e:
            print(f"Error replacing file {file_entry.file_name}: {e}")
            return False
