#!/usr/bin/env python3

import tkinter as tk
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from arc_gui import ArcUnpackerGUI

def main():
    try:
        root = tk.Tk()
        ArcUnpackerGUI(root)
        root.mainloop()
        
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
