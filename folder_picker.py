"""Native folder dialog, launched on demand by the local server."""
import json
import tkinter as tk
from tkinter import filedialog
root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
path = filedialog.askdirectory(title='ToolForge: Arbeitsordner auswählen', parent=root)
root.destroy()
print(json.dumps({'path': path}, ensure_ascii=True))
