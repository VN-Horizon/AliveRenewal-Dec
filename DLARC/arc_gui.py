import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
from typing import List, Optional
from arc_parser import ArcFile, FileEntry
from file_extractor import ArcExtractor

class ArcUnpackerGUI:
    """Main GUI for the ARC Unpacker application"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("DLARC")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        
        self.arc_file: Optional[ArcFile] = None
        self.extractor: Optional[ArcExtractor] = None
        self.selected_files: List[FileEntry] = []
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        ttk.Label(main_frame, text="ARC File:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        file_frame = ttk.Frame(main_frame)
        file_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(0, weight=1)
        
        self.file_path_var = tk.StringVar()
        self.file_entry = ttk.Entry(file_frame, textvariable=self.file_path_var, state="readonly")
        self.file_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        ttk.Button(file_frame, text="Browse", command=self.browse_file).grid(row=0, column=1)
        
        list_frame = ttk.LabelFrame(main_frame, text="Files in Archive", padding="5")
        list_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        columns = ("Name", "Address", "Formatted Size")
        self.file_tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="extended")
        
        self.file_tree.heading("Name", text="File Name")
        self.file_tree.heading("Address", text="Address")
        self.file_tree.heading("Formatted Size", text="Size")
        
        self.file_tree.column("Name", width=300, minwidth=200)
        self.file_tree.column("Address", width=100, minwidth=80)
        self.file_tree.column("Formatted Size", width=100, minwidth=80)
        
        tree_scroll_y = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.file_tree.yview)
        tree_scroll_x = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.file_tree.xview)
        self.file_tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        
        self.file_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_scroll_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        tree_scroll_x.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        self.file_tree.bind('<<TreeviewSelect>>', self.on_file_selection)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=(10, 0))
        
        ttk.Button(button_frame, text="Select All", command=self.select_all_files).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Clear Selection", command=self.clear_selection).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Extract Selected", command=self.extract_selected).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Extract All", command=self.extract_all).pack(side=tk.LEFT, padx=(0, 5))
        
        self.replace_button = ttk.Button(button_frame, text="Replace File", command=self.replace_file, state="disabled")
        self.replace_button.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(button_frame, text="Regenerate", command=self.regenerate).pack(side=tk.LEFT, padx=(0, 5))
        
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
    
    def browse_file(self):
        """Open file dialog to select ARC file"""
        file_path = filedialog.askopenfilename(
            title="Select ARC File",
            filetypes=[("ARC files", "*.arc"), ("All files", "*.*")]
        )
        
        if file_path:
            self.load_arc_file(file_path)
    
    def load_arc_file(self, file_path: str):
        """Load and parse ARC file"""
        try:
            self.status_var.set("Loading ARC file...")
            self.root.update()
            
            self.arc_file = ArcFile.parse(file_path)
            self.extractor = ArcExtractor(self.arc_file)
            
            self.file_path_var.set(file_path)
            
            self.populate_file_list()
            
            self.status_var.set(f"Loaded {len(self.arc_file.file_entries)} files")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load ARC file:\n{str(e)}")
            self.status_var.set("Error loading file")
    
    def populate_file_list(self):
        """Populate the file list treeview"""
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        file_info = self.extractor.get_file_info()
        
        for name, addr, formatted_size in file_info:
            self.file_tree.insert("", tk.END, values=(name, addr, formatted_size))
    
    def on_file_selection(self, event):
        """Handle file selection in treeview"""
        selection = self.file_tree.selection()
        self.selected_files = []
        
        for item in selection:
            values = self.file_tree.item(item, "values")
            file_name = values[0]
            
            for entry in self.arc_file.file_entries:
                if entry.file_name == file_name:
                    self.selected_files.append(entry)
                    break
        
        if self.selected_files:
            total_size = sum(f.file_size for f in self.selected_files)
            if total_size < 1024:
                size_str = f"{total_size} B"
            elif total_size < 1024 * 1024:
                size_str = f"{total_size / 1024:.1f} KB"
            else:
                size_str = f"{total_size / (1024 * 1024):.1f} MB"
            
            self.status_var.set(f"Selected {len(self.selected_files)} files ({size_str})")
        else:
            self.status_var.set("No files selected")
        
        if len(self.selected_files) == 1:
            self.replace_button.config(state="normal")
        else:
            self.replace_button.config(state="disabled")
    
    def select_all_files(self):
        """Select all files in the list"""
        for item in self.file_tree.get_children():
            self.file_tree.selection_add(item)
        self.replace_button.config(state="disabled")
    
    def clear_selection(self):
        """Clear file selection"""
        self.file_tree.selection_remove(self.file_tree.selection())
        self.replace_button.config(state="disabled")
    
    def extract_selected(self):
        """Extract selected files"""
        if not self.selected_files:
            messagebox.showwarning("Warning", "No files selected for extraction")
            return
        
        self.extract_files(self.selected_files, "Extracting selected files...")
    
    def extract_all(self):
        """Extract all files"""
        if not self.arc_file:
            messagebox.showwarning("Warning", "No ARC file loaded")
            return
        
        self.extract_files(self.arc_file.file_entries, "Extracting all files...")
    
    def extract_files(self, files: List[FileEntry], status_message: str):
        """Extract specified files"""
        output_dir = filedialog.askdirectory(title="Select Output Directory")
        if not output_dir:
            return
        
        def extract_thread():
            try:
                self.status_var.set(status_message)
                self.progress_var.set(0)
                
                success_count, total_count = self.extractor.extract_selected_files(files, output_dir)
                
                self.progress_var.set(100)
                
                if success_count == total_count:
                    messagebox.showinfo("Success", f"Successfully extracted {success_count} files to:\n{output_dir}")
                    self.status_var.set(f"Extracted {success_count} files successfully")
                else:
                    messagebox.showwarning("Partial Success", 
                                        f"Extracted {success_count} out of {total_count} files to:\n{output_dir}")
                    self.status_var.set(f"Extracted {success_count}/{total_count} files")
                
            except Exception as e:
                messagebox.showerror("Error", f"Extraction failed:\n{str(e)}")
                self.status_var.set("Extraction failed")
            finally:
                self.progress_var.set(0)
        
        thread = threading.Thread(target=extract_thread, daemon=True)
        thread.start()

    def replace_file(self):
        """Replace a file in the ARC file"""
        if not self.arc_file:
            messagebox.showwarning("Warning", "No ARC file loaded")
            return
        
        if len(self.selected_files) != 1:
            messagebox.showwarning("Warning", "Please select exactly one file to replace")
            return
        
        selected_file = self.selected_files[0]
        
        file_path = filedialog.askopenfilename(title="Select File to Replace")
        if not file_path:
            return
        
        try:
            self.status_var.set("Replacing file...")
            self.progress_var.set(50)
            
            success = self.extractor.replace_file(selected_file, file_path)
            
            if success:
                messagebox.showinfo("Success", f"File '{selected_file.file_name}' replaced successfully")
                self.status_var.set("File replaced successfully")
                
                self.populate_file_list()
            else:
                messagebox.showerror("Error", "Failed to replace file")
                self.status_var.set("File replacement failed")
                
        except Exception as e:
            messagebox.showerror("Error", f"File replacement failed:\n{str(e)}")
            self.status_var.set("File replacement failed")
        finally:
            self.progress_var.set(0)
        
    def regenerate(self):
        """Regenerate the ARC file"""
        if not self.arc_file:
            messagebox.showwarning("Warning", "No ARC file loaded")
            return
        
        output_path = filedialog.asksaveasfilename(
            title="Save Regenerated ARC File",
            defaultextension=".arc",
            filetypes=[("ARC files", "*.arc"), ("All files", "*.*")]
        )
        
        if not output_path:
            return
        
        def regenerate_thread():
            try:
                self.status_var.set("Regenerating ARC file...")
                self.progress_var.set(50)
                
                success = self.extractor.regenerate_arc_file(output_path)
                
                self.progress_var.set(100)
                
                if success:
                    messagebox.showinfo("Success", f"ARC file regenerated successfully:\n{output_path}")
                    self.status_var.set("ARC file regenerated successfully")
                else:
                    messagebox.showerror("Error", "Failed to regenerate ARC file")
                    self.status_var.set("Regeneration failed")
                
            except Exception as e:
                messagebox.showerror("Error", f"Regeneration failed:\n{str(e)}")
                self.status_var.set("Regeneration failed")
            finally:
                self.progress_var.set(0)
        
        thread = threading.Thread(target=regenerate_thread, daemon=True)
        thread.start()