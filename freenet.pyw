import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import base64
import urllib.parse
from urllib.parse import urlparse, parse_qs
import subprocess
import os
import time
import requests
import socket
import random
import concurrent.futures
from tqdm import tqdm
import threading
import queue
import sys
from datetime import datetime
import platform
if platform.system() == "Windows":
    import winreg
import qrcode
import zipfile
import shutil
import io
from contextlib import contextmanager
from PIL import ImageTk, Image
from concurrent.futures import ThreadPoolExecutor, as_completed
if sys.platform == 'win32':
    from subprocess import CREATE_NO_WINDOW



def kill_xray_processes():
    """Kill any existing Xray processes (cross-platform)"""
    try:
        if sys.platform == 'win32':
            # Windows implementation
            import psutil
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'].lower() == 'xray.exe':
                        proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        else:
            # Linux/macOS implementation
            import signal
            import subprocess
            subprocess.run(['pkill', '-f', 'xray'], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL)
    except Exception as e:
        self.log(f"Error killing existing Xray processes: {str(e)}")


class VPNConfigGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("VPN Config Manager")
        self.root.geometry("600x600+620+20")

        # Define BASE_DIR at the beginning of __init__
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))

        
        # Configure dark theme
        self.setup_dark_theme()
        
        # Kill any existing Xray processes
        self.kill_existing_xray_processes()
        
        
        self.log_queue = queue.Queue()
        
        self.stop_event = threading.Event()
        self.thread_lock = threading.Lock()
        self.active_threads = []
        self.is_fetching = False
        
        #self.XRAY_CORE_URL = "https://github.com/XTLS/Xray-core/releases/latest/download/Xray-windows-64.zip"
        
        self.XRAY_CORE_URL = self._get_xray_core_url()
        
        self.XRAY_PATH = "xray.exe" if platform.system() == "Windows" else "xray"
        
        # Configuration - now using a dictionary of mirrors
        self.MIRRORS = {
            "barry-far": "https://raw.githubusercontent.com/barry-far/V2ray-Config/refs/heads/main/All_Configs_Sub.txt",
            "SoliSpirit": "https://raw.githubusercontent.com/SoliSpirit/v2ray-configs/refs/heads/main/all_configs.txt",
            #"mrvcoder": "https://raw.githubusercontent.com/mrvcoder/V2rayCollector/refs/heads/main/mixed_iran.txt",
            #"MatinGhanbari": "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/main/subscriptions/v2ray/all_sub.txt",
        }
        self.CONFIGS_URL = self.MIRRORS["barry-far"]  # Default mirror
        self.WORKING_CONFIGS_FILE = "working_configs.txt"
        self.BEST_CONFIGS_FILE = "best_configs.txt"
        self.TEMP_CONFIG_FILE = "temp_config.json"
        
        
        
        
        self.TEMP_FOLDER = os.path.join(self.BASE_DIR, "temp")
        self.TEMP_CONFIG_FILE = os.path.join(self.TEMP_FOLDER, "temp_config.json")
        
        
        self.XRAY_PATH = os.path.join(self.BASE_DIR, "xray.exe" if sys.platform == 'win32' else "xray")
        
        
        
        # For Linux/macOS, use: os.path.join(os.getcwd(), "xray")
        self.TEST_TIMEOUT = 10
        self.SOCKS_PORT = 1080
        self.PING_TEST_URL = "https://facebook.com"
        self.LATENCY_WORKERS = 20
        
        # Create temp folder if it doesn't exist
        if not os.path.exists(self.TEMP_FOLDER):
            os.makedirs(self.TEMP_FOLDER)
        
        
        
        # Variables
        self.best_configs = []
        self.selected_config = None
        self.connected_config = None  # Track the currently connected config
        self.xray_process = None
        self.is_connected = False
        
        self.total_configs = 0
        self.tested_configs = 0
        self.working_configs = 0
        
        self.setup_ui()
        self.setup_logging()
        
        
        # Load best configs if file exists
        if os.path.exists(self.BEST_CONFIGS_FILE):
            self.load_best_configs()
        
    def setup_dark_theme(self):
        """Configure dark theme colors"""
        self.root.tk_setPalette(background='#2d2d2d', foreground='#ffffff',
                              activeBackground='#3e3e3e', activeForeground='#ffffff')

        style = ttk.Style()
        style.theme_use('clam')

        # General widget styling
        style.configure('.', background='#2d2d2d', foreground='#ffffff')
        style.configure('TFrame', background='#2d2d2d')
        style.configure('TLabel', background='#2d2d2d', foreground='#ffffff')
        style.configure('TEntry', fieldbackground='#3e3e3e', foreground='#ffffff')
        style.configure('TScrollbar', background='#3e3e3e')
        
        # Treeview styling
        style.configure('Treeview', 
                       background='#3e3e3e', 
                       foreground='#ffffff', 
                       fieldbackground='#3e3e3e')
        style.configure('Treeview.Heading', 
                       background='#3e3e3e', 
                       foreground='#ffffff')  # Remove button-like appearance
        
        # Remove hover effect on headers
        style.map('Treeview.Heading', 
                  background=[('active', '#3e3e3e')],  # Same as normal background
                  foreground=[('active', '#ffffff')])  # Same as normal foreground
        
        style.map('Treeview', background=[('selected', '#4a6984')])
        style.configure('Vertical.TScrollbar', background='#3e3e3e')
        style.configure('Horizontal.TScrollbar', background='#3e3e3e')
        style.configure('TProgressbar', background='#4a6984', troughcolor='#3e3e3e')

        # Button styling - modified to remove focus highlight
        style.configure('TButton', 
                       background='#3e3e3e', 
                       foreground='#ffffff', 
                       relief='flat',
                       focuscolor='#3e3e3e',  # Same as background
                       focusthickness=0)       # Remove focus thickness
        
        style.map('TButton',
                  background=[('!active', '#3e3e3e'), ('pressed', '#3e3e3e')],
                  foreground=[('disabled', '#888888')])
        
        # Special style for stop button
        style.configure('Stop.TButton', 
                       background='Tomato', 
                       foreground='#ffffff',
                       focuscolor='Tomato',    # Same as background
                       focusthickness=0)      # Remove focus thickness
        
        style.map('Stop.TButton',
                  background=[('!active', 'Tomato'), ('pressed', 'Tomato')],
                  foreground=[('disabled', '#888888')])
        
        
        
    def setup_ui(self):
        # --- Top Fixed Frame ---
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill=tk.X, pady=(10, 5), padx=10)

        # Buttons    
        self.fetch_btn = ttk.Button(top_frame, text="Fetch & Test New Configs", command=self.fetch_and_test_configs, cursor='hand2')
        self.fetch_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.connect_btn = ttk.Button(top_frame, text="Connect", command=self.connect_config, state=tk.DISABLED, cursor='hand2')
        self.connect_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.disconnect_btn = ttk.Button(top_frame, text="Disconnect", command=self.click_disconnect_config_button, state=tk.DISABLED, cursor='hand2')
        self.disconnect_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        
        self.reload_btn = ttk.Button(top_frame, text="Reload Best Configs", command=self.reload_and_test_configs, cursor='hand2')
        self.reload_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Status label
        self.status_label = ttk.Label(top_frame, text="Disconnected", foreground="Tomato")
        self.status_label.pack(side=tk.RIGHT)
        
        

        
        
        
        

        

        # --- Paned Window ---
        main_pane = tk.PanedWindow(self.root, orient=tk.VERTICAL, sashwidth=8, bg="#2d2d2d")
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # --- Middle Treeview Frame ---
        self.middle_frame = ttk.Frame(main_pane)

        columns = ('Index', 'Latency', 'Protocol', 'Server', 'Port' ,'Config')
        self.tree = ttk.Treeview(self.middle_frame, columns=columns, show='headings', height=15)

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor='center', minwidth=50)  # Added minwidth parameter

        self.tree.column('Index', width=50, minwidth=50)
        self.tree.column('Latency', width=100, minwidth=100)
        self.tree.column('Protocol', width=80, minwidth=80)
        self.tree.column('Server', width=150, minwidth=150)
        self.tree.column('Port', width=80, minwidth=80)
        self.tree.column('Config', width=400, anchor='w', minwidth=150)

        tree_vscrollbar = ttk.Scrollbar(self.middle_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_vscrollbar.set)
        tree_hscrollbar = ttk.Scrollbar(self.middle_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(xscrollcommand=tree_hscrollbar.set)

        self.tree.grid(row=0, column=0, sticky='nsew')
        tree_vscrollbar.grid(row=0, column=1, sticky='ns')
        tree_hscrollbar.grid(row=1, column=0, sticky='ew')

        self.middle_frame.grid_rowconfigure(0, weight=1)
        self.middle_frame.grid_columnconfigure(0, weight=1)
        
        
        
        # Add context menu for treeview
        #self.tree_context_menu = tk.Menu(self.root, tearoff=0)
        #self.tree_context_menu.add_command(label="Generate QR Code", command=self.on_generate_qrcode_context)
        
        
        # Configure tree tags for connected config highlighting
        self.tree.tag_configure('connected', background='#2d5a2d', foreground='#90EE90')
        
        
        
        self.tree.bind('<Button-1>', self.on_tree_click)
        
        self.tree.bind("<Button-3>", self.on_right_click)
        
        # Bind double click event
        self.tree.bind('<Double-1>', self.on_config_select)
        
        
        
        # Bind Ctrl+V for pasting configs
        self.root.bind('<Control-v>', self.paste_configs)
        
        # Bind Ctrl+C for copying configs
        self.root.bind('<Control-c>', self.copy_selected_configs)
        
        
        # Bind DEL key for deleting configs
        self.root.bind('<Delete>', self.delete_selected_configs)
        
        # Bind Q/q for QR code generation
        self.root.bind('<q>', self.generate_qrcode)
        self.root.bind('<Q>', self.generate_qrcode)
        

        # --- Bottom Terminal Frame ---
        bottom_frame = ttk.LabelFrame(main_pane, text="Logs")
        bottom_frame.pack_propagate(False)

        counter_frame = ttk.Frame(bottom_frame)
        counter_frame.pack(fill=tk.X, padx=5, pady=(5, 0))

        self.tested_label = ttk.Label(counter_frame, text="Tested: 0")
        self.tested_label.pack(side=tk.LEFT, padx=(0, 10))

        self.total_label = ttk.Label(counter_frame, text="Total: 0")
        self.total_label.pack(side=tk.LEFT)
        
        self.working_label = ttk.Label(counter_frame, text="Working: 0")
        self.working_label.pack(side=tk.LEFT, padx=(10, 0))
        
        self.progress = ttk.Progressbar(counter_frame, mode='determinate')
        self.progress.pack(side=tk.RIGHT, padx=(10, 10), fill=tk.X, expand=True)

        self.terminal = scrolledtext.ScrolledText(bottom_frame, height=2, state=tk.DISABLED)
        self.terminal.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.terminal.configure(bg='#3e3e3e', fg='#ffffff', insertbackground='white')

        # --- Add to PanedWindow ---
        main_pane.add(self.middle_frame)
        main_pane.add(bottom_frame)
        
        
        # Configure pane constraints
        main_pane.paneconfigure(bottom_frame, minsize=50)  # Absolute minimum height
        main_pane.paneconfigure(self.middle_frame, minsize=200)  # Prevent complete collapse
        
        # Set initial sash position (adjust 300 to your preferred initial height)
        main_pane.sash_place(0, 0, 300)  # This makes bottom frame start taller
        
        
        # --- Menu Bar ---
        menubar = tk.Menu(self.root)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Options menu
        options_menu = tk.Menu(menubar, tearoff=0)
        options_menu.add_command(label="Update Xray Core", command=self.update_xray_core)
        options_menu.add_command(label="Update GeoFiles", command=self.update_geofiles)
        menubar.add_cascade(label="Options", menu=options_menu)
        
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Clear Terminal", command=self.clear_terminal)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        
        self.root.config(menu=menubar)
        
    
    
    
    def _get_xray_core_url(self):
        """
        Automatically detect the operating system and architecture
        and return the appropriate Xray core download URL
        """
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        # Base URL for Xray core releases
        base_url = "https://github.com/XTLS/Xray-core/releases/latest/download/"
        
        # Determine the correct filename based on OS and architecture
        if system == "windows":
            if machine in ["amd64", "x86_64"]:
                filename = "Xray-windows-64.zip"
            elif machine in ["i386", "i686", "x86"]:
                filename = "Xray-windows-32.zip"
            elif machine in ["arm64", "aarch64"]:
                filename = "Xray-windows-arm64-v8a.zip"
            elif machine.startswith("arm"):
                filename = "Xray-windows-arm32-v7a.zip"
            else:
                # Default to 64-bit for unknown architectures
                filename = "Xray-windows-64.zip"
                self.log(f"Unknown Windows architecture: {machine}, defaulting to 64-bit")
        
        elif system == "linux":
            if machine in ["amd64", "x86_64"]:
                filename = "Xray-linux-64.zip"
            elif machine in ["i386", "i686", "x86"]:
                filename = "Xray-linux-32.zip"
            elif machine in ["arm64", "aarch64"]:
                filename = "Xray-linux-arm64-v8a.zip"
            elif machine.startswith("arm"):
                # Check for specific ARM versions
                if "v7" in machine or "armv7" in machine:
                    filename = "Xray-linux-arm32-v7a.zip"
                elif "v6" in machine or "armv6" in machine:
                    filename = "Xray-linux-arm32-v6.zip"
                elif "v5" in machine or "armv5" in machine:
                    filename = "Xray-linux-arm32-v5.zip"
                else:
                    filename = "Xray-linux-arm32-v7a.zip"  # Default ARM
            elif machine in ["mips", "mips64"]:
                filename = "Xray-linux-mips64.zip"
            elif machine in ["mipsel", "mips64el"]:
                filename = "Xray-linux-mips64le.zip"
            elif machine in ["ppc64", "ppc64le"]:
                filename = "Xray-linux-ppc64le.zip"
            elif machine in ["riscv64"]:
                filename = "Xray-linux-riscv64.zip"
            elif machine in ["s390x"]:
                filename = "Xray-linux-s390x.zip"
            elif machine in ["loongarch64", "loong64"]:
                filename = "Xray-linux-loong64.zip"
            else:
                # Default to 64-bit for unknown architectures
                filename = "Xray-linux-64.zip"
                self.log(f"Unknown Linux architecture: {machine}, defaulting to 64-bit")
        
        elif system == "darwin":  # macOS
            if machine in ["arm64", "aarch64"]:
                filename = "Xray-macos-arm64-v8a.zip"
            elif machine in ["amd64", "x86_64"]:
                filename = "Xray-macos-64.zip"
            else:
                # Default to Intel 64-bit for unknown architectures
                filename = "Xray-macos-64.zip"
                self.log(f"Unknown macOS architecture: {machine}, defaulting to Intel 64-bit")
        
        elif system == "freebsd":
            if machine in ["amd64", "x86_64"]:
                filename = "Xray-freebsd-64.zip"
            elif machine in ["i386", "i686", "x86"]:
                filename = "Xray-freebsd-32.zip"
            elif machine in ["arm64", "aarch64"]:
                filename = "Xray-freebsd-arm64-v8a.zip"
            elif machine.startswith("arm"):
                filename = "Xray-freebsd-arm32-v7a.zip"
            else:
                filename = "Xray-freebsd-64.zip"
                self.log(f"Unknown FreeBSD architecture: {machine}, defaulting to 64-bit")
        
        elif system == "openbsd":
            if machine in ["amd64", "x86_64"]:
                filename = "Xray-openbsd-64.zip"
            elif machine in ["i386", "i686", "x86"]:
                filename = "Xray-openbsd-32.zip"
            elif machine in ["arm64", "aarch64"]:
                filename = "Xray-openbsd-arm64-v8a.zip"
            elif machine.startswith("arm"):
                filename = "Xray-openbsd-arm32-v7a.zip"
            else:
                filename = "Xray-openbsd-64.zip"
                self.log(f"Unknown OpenBSD architecture: {machine}, defaulting to 64-bit")
        
        else:
            # Unsupported OS, default to Linux 64-bit
            filename = "Xray-linux-64.zip"
            self.log(f"Unsupported OS: {system}, defaulting to Linux 64-bit")
        
        full_url = base_url + filename
        #self.log(f"Detected OS: {system}, Architecture: {machine}")
        #self.log(f"Selected Xray core URL: {full_url}")
        
        return full_url
    
    
    
    
    
    def get_system_info(self):
        """
        Get detailed system information for debugging
        """
        info = {
            "system": platform.system(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "architecture": platform.architecture(),
            "platform": platform.platform(),
            "python_version": sys.version,
            "selected_url": self.XRAY_CORE_URL
        }
        return info
    
    
    
    def log_system_info(self):
        """
        Log detailed system information
        """
        info = self.get_system_info()
        self.log("=== System Information ===")
        for key, value in info.items():
            self.log(f"{key}: {value}")
        self.log("=========================")
    
    
    def clear_terminal(self):
        """Clear the terminal output"""
        self.terminal.config(state=tk.NORMAL)
        self.terminal.delete('1.0', tk.END)
        self.terminal.config(state=tk.DISABLED)
        #self.log("Terminal cleared")
    
    
    def show_mirror_selection(self):
        """Show a popup window to select mirror and thread count"""
        self.mirror_window = tk.Toplevel(self.root)
        self.mirror_window.title("Select Mirror & Threads")
        self.mirror_window.geometry("300x200")  # Increased height for new control
        self.mirror_window.resizable(False, False)
        
        # Center the window
        window_width = 300
        window_height = 200
        screen_width = self.mirror_window.winfo_screenwidth()
        screen_height = self.mirror_window.winfo_screenheight()
        x = int((screen_width/2) - (window_width/2))
        y = int((screen_height/2) - (window_height/2))
        self.mirror_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Dark theme for the popup
        self.mirror_window.tk_setPalette(background='#2d2d2d', foreground='#ffffff',
                              activeBackground='#3e3e3e', activeForeground='#ffffff')
        
        # Create a custom style for the combobox
        style = ttk.Style()
        style.theme_use('clam')  # Use 'clam' theme as base
        
        # Configure combobox colors
        style.configure('TCombobox', 
                       fieldbackground='#3e3e3e',  # Background of the text field
                       background='#3e3e3e',       # Background of the dropdown
                       foreground='#ffffff',       # Text color
                       selectbackground='#4a6984', # Selection background
                       selectforeground='#ffffff', # Selection text color
                       bordercolor='#3e3e3e',     # Border color
                       lightcolor='#3e3e3e',      # Light part of the border
                       darkcolor='#3e3e3e')       # Dark part of the border
        
        # Configure the dropdown list
        style.map('TCombobox', 
                  fieldbackground=[('readonly', '#3e3e3e')],
                  selectbackground=[('readonly', '#4a6984')],
                  selectforeground=[('readonly', '#ffffff')],
                  background=[('readonly', '#3e3e3e')])
        
        # Mirror selection
        ttk.Label(self.mirror_window, text="Select a mirror:").pack(pady=(10, 0))

        self.mirror_combo = ttk.Combobox(
            self.mirror_window, 
            values=list(self.MIRRORS.keys()),
            state="readonly",
            style='TCombobox'
        )
        self.mirror_combo.current(0)
        self.mirror_combo.pack(pady=5, padx=20, fill=tk.X)
        
        # Thread count selection
        ttk.Label(self.mirror_window, text="Maximum cpu usage:").pack(pady=(10, 0))
        
        self.thread_combo = ttk.Combobox(
            self.mirror_window,
            values=["10", "20", "50", "100"],
            state="readonly",
            style='TCombobox'
        )
        self.thread_combo.set("100")  # Default to 100
        self.thread_combo.pack(pady=5, padx=20, fill=tk.X)
        
        # Apply dark background to the dropdown lists
        self.mirror_window.option_add('*TCombobox*Listbox.background', '#3e3e3e')
        self.mirror_window.option_add('*TCombobox*Listbox.foreground', '#ffffff')
        self.mirror_window.option_add('*TCombobox*Listbox.selectBackground', '#4a6984')
        self.mirror_window.option_add('*TCombobox*Listbox.selectForeground', '#ffffff')
        
        # Frame for buttons
        button_frame = ttk.Frame(self.mirror_window)
        button_frame.pack(pady=10)
        
        # OK button
        ttk.Button(
            button_frame, 
            text="OK", 
            command=self.on_mirror_selected
        ).pack(side=tk.LEFT, padx=5)
        
        # Cancel button
        ttk.Button(
            button_frame, 
            text="Cancel", 
            command=self.cancel_mirror_selection
        ).pack(side=tk.LEFT, padx=5)
        
        # Handle window close (X button)
        self.mirror_window.protocol("WM_DELETE_WINDOW", self.cancel_mirror_selection)
        
        # Make the window modal
        self.mirror_window.grab_set()
        self.mirror_window.transient(self.root)
        self.mirror_window.wait_window(self.mirror_window)
    
    def cancel_mirror_selection(self):
        """Handle cancel or window close without selection"""
        if hasattr(self, 'mirror_window') and self.mirror_window:
            self.mirror_window.destroy()
        
        # Reset the button state
        self.fetch_btn.config(
            text="Fetch & Test New Configs",
            style='TButton',
            state=tk.NORMAL
        )
        self.is_fetching = False

    
    
    
    
    def on_mirror_selected(self):
        """Handle mirror and thread count selection"""
        selected_mirror = self.mirror_combo.get()
        selected_threads = self.thread_combo.get()
        
        if selected_mirror in self.MIRRORS:
            self.CONFIGS_URL = self.MIRRORS[selected_mirror]
            try:
                self.LATENCY_WORKERS = int(selected_threads)
            except ValueError:
                self.LATENCY_WORKERS = 100  # Default if conversion fails
                
            self.log(f"Selected mirror: {selected_mirror}, Threads: {self.LATENCY_WORKERS}")
            self.mirror_window.destroy()
            self._start_fetch_and_test()
        else:
            # If somehow no valid selection, treat as cancel
            self.cancel_mirror_selection()
    
    
    
    
    
    def _start_fetch_and_test(self):
        """Start the actual fetch and test process after mirror selection"""
        # Start fetching
        self.is_fetching = True
        self.fetch_btn.config(text="Stop Fetching Configs", style='Stop.TButton')
        self.log("Starting config fetch and test...")
        
        # Clear any previous stop state
        self.stop_event.clear()
        
        thread = threading.Thread(target=self._fetch_and_test_worker, daemon=True)
        thread.start()
    

    def on_right_click(self, event):
        """Handle right-click event on treeview"""
        item = self.tree.identify_row(event.y)
        if item:
            # Select the item that was right-clicked
            self.tree.selection_set(item)
            self.on_config_highlight(event)  # Update selection
            
            # Show context menu
            try:
                #self.tree_context_menu.tk_popup(event.x_root, event.y_root)
                self.generate_qrcode()
            except :
                pass
            finally:
                #self.tree_context_menu.grab_release()
                pass
    
    
    
    
    
    def load_best_configs(self):
        """Load best configs from file if it exists and test them"""
        try:
            # Change button to stop state
            self.root.after(0, lambda: self.reload_btn.config(
                text="Stop Loading Configs",
                style='Stop.TButton',
                state=tk.NORMAL
            ))
            
            if os.path.exists(self.BEST_CONFIGS_FILE):
                # Store original configs from file to preserve them
                self.original_configs_backup = []
                with open(self.BEST_CONFIGS_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            self.original_configs_backup.append(line)
                
                # Only clear if we're not in the middle of a test
                if not self.stop_event.is_set():
                    self.best_configs = []
                    for item in self.tree.get_children():
                        self.tree.delete(item)
                
                # Use a set to avoid duplicates while reading
                seen = set()
                config_uris = []
                for line in self.original_configs_backup:
                    if self.stop_event.is_set():
                        break
                        
                    if line and line not in seen:
                        seen.add(line)
                        config_uris.append(line)
                
                # Check if file is empty or has no valid configs
                if not config_uris:
                    self.root.after(0, lambda: self.reload_btn.config(
                        text="Reload Best Configs",
                        style='TButton',
                        state=tk.NORMAL
                    ))
                    self.log("No configs found in best_configs.txt")
                    return
                
                if not self.stop_event.is_set():
                    # Initialize with default infinite latency (will be updated when tested)
                    # Only add new configs, don't overwrite existing ones
                    existing_uris = {uri for uri, _ in self.best_configs}
                    new_configs = [(uri, float('inf')) for uri in config_uris if uri not in existing_uris]
                    self.best_configs.extend(new_configs)
                    
                    self.total_configs = len(config_uris)
                    self.tested_configs = 0  # Reset to 0 since we need to test them again
                    self.working_configs = len([c for c in self.best_configs if c[1] != float('inf')])
                    self.update_counters()
                    self.root.after(0, lambda: self.progress.config(maximum=len(config_uris), value=0))
                    self.log(f"Loaded {len(config_uris)} configs from {self.BEST_CONFIGS_FILE}")
                    
                    # Start testing the loaded configs in a separate thread
                    thread = threading.Thread(target=self._test_pasted_configs_worker, args=(config_uris,), daemon=True)
                    with self.thread_lock:
                        self.active_threads.append(thread)
                    thread.start()

        except Exception as e:  # Added proper except block
            self.log(f"Error loading best configs: {str(e)}")
            # Reset button if error occurs
            self.root.after(0, lambda: self.reload_btn.config(
                text="Reload Best Configs",
                style='TButton',
                state=tk.NORMAL
            ))
            self.stop_event.clear()
    
    
    
    
    
    def reload_and_test_configs(self):
        """Reload and test configs from best_configs.txt"""
        if self.reload_btn.cget('text') == "Stop Loading Configs":
            self.stop_reloading()
            return
            
        self.reload_btn.config(
            text="Stop Loading Configs",
            style='Stop.TButton',
            state=tk.NORMAL
        )
        self.log("Reloading and testing configs from best_configs.txt...")
        
        # Don't clear best_configs or treeview here - let load_best_configs handle it
        # Load and test configs from file
        self.load_best_configs()
    
    
    
    def delete_selected_configs(self, event=None):
        """Delete selected configs by reading from file, filtering, and saving back"""
        selected_items = self.tree.selection()
        if not selected_items:
            return

        # Get URIs of selected items
        selected_uris = [self.tree.item(item)['values'][5] for item in selected_items]  # Assuming URI is in column 5
        
        try:
            # Read all configs from file
            with open(self.BEST_CONFIGS_FILE, 'r', encoding='utf-8') as f:
                all_configs = [line.strip() for line in f if line.strip()]

            # Filter out selected URIs
            remaining_configs = []
            deleted_count = 0
            
            for config in all_configs:
                if config not in selected_uris:
                    remaining_configs.append(config)
                else:
                    deleted_count += 1

            # Write remaining configs back to file
            with open(self.BEST_CONFIGS_FILE, 'w', encoding='utf-8') as f:
                f.write('\n'.join(remaining_configs))

            # Reload the configs to update both the data and UI
            self.best_configs = []  # Clear current configs
            self.load_best_configs()  # This will reload from file and update the treeview

            
            self.log(f"Deleted {deleted_count} config(s)")

        except Exception as e:
            self.log(f"Error deleting configs: {str(e)}")


    def save_best_configs(self):
        """Save current best configs to file"""
        try:
            with open(self.BEST_CONFIGS_FILE, 'w', encoding='utf-8') as f:
                for config_uri, _ in self.best_configs:  # Only save the URI part
                    f.write(f"{config_uri}\n")
        except Exception as e:
            self.log(f"Error saving best configs: {str(e)}")
    
    
    
    
    def kill_existing_xray_processes(self):
        """Kill any existing Xray processes (cross-platform)"""
        try:
            if sys.platform == 'win32':
                # Windows implementation
                import psutil
                for proc in psutil.process_iter(['name']):
                    try:
                        if proc.info['name'].lower() == 'xray.exe':
                            proc.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            else:
                # Linux/macOS implementation
                import signal
                import subprocess
                subprocess.run(['pkill', '-f', 'xray'], 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL)
        except Exception as e:
            self.log(f"Error killing existing Xray processes: {str(e)}")
            
            
    
    def generate_qrcode(self, event=None):
        """Generate QR code for selected config and display it"""
        selected_items = self.tree.selection()
        if not selected_items:
            return
            
        item = selected_items[0]
        index = int(self.tree.item(item)['values'][0]) - 1
        
        if 0 <= index < len(self.best_configs):
            config_uri = self.best_configs[index][0]
            
            # Create QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(config_uri)
            qr.make(fit=True)
            
            # Keep the original PIL image for resizing
            self.original_img = qr.make_image(fill_color="black", back_color="white")
            
            # Create and show QR code window
            qr_window = tk.Toplevel(self.root)
            qr_window.title("Config QR Code")
            qr_window.geometry("600x620+20+20")
            
            # Convert PIL image to Tkinter PhotoImage
            self.tk_image = ImageTk.PhotoImage(self.original_img)
            
            self.label = ttk.Label(qr_window, image=self.tk_image)
            self.label.image = self.tk_image  # Keep a reference
            self.label.pack(pady=10)
            
            # Set smaller default zoom for VMess configs
            if config_uri.startswith("vmess://"):
                # VMess configs are longer, so use smaller default zoom
                self.zoom_level = 0.7  # 70% of original size
                # Resize the image
                width, height = self.original_img.size
                new_size = (int(width * self.zoom_level), int(height * self.zoom_level))
                resized_img = self.original_img.resize(new_size, Image.Resampling.LANCZOS)
                
                # Update the displayed image
                self.tk_image = ImageTk.PhotoImage(resized_img)
                self.label.configure(image=self.tk_image)
                self.label.image = self.tk_image  # Keep a reference
            else:
                # Other config types can use normal size
                self.zoom_level = 1.0
            
            # Bind mouse wheel event for zooming
            qr_window.bind("<Control-MouseWheel>", self.zoom_qrcode)
            self.label.bind("<Control-MouseWheel>", self.zoom_qrcode)
            
            # Add config preview
            config_preview = ttk.Label(
                qr_window, 
                text=config_uri[:40] + "..." if len(config_uri) > 40 else config_uri,
                wraplength=280
            )
            config_preview.pack(pady=5, padx=10)
            
            # Add close button
            close_btn = ttk.Button(qr_window, text="Close", command=qr_window.destroy)
            close_btn.pack(pady=5)

    def zoom_qrcode(self, event):
        """Handle zooming of QR code with Ctrl + mouse wheel"""
        # Determine zoom direction
        if event.delta > 0:
            self.zoom_level *= 1.1  # Zoom in
        else:
            self.zoom_level *= 0.9  # Zoom out
        
        # Limit zoom levels (optional)
        self.zoom_level = max(0.1, min(self.zoom_level, 5.0))
        
        # Resize the image
        width, height = self.original_img.size
        new_size = (int(width * self.zoom_level), int(height * self.zoom_level))
        resized_img = self.original_img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Update the displayed image
        self.tk_image = ImageTk.PhotoImage(resized_img)
        self.label.configure(image=self.tk_image)
        self.label.image = self.tk_image  # Keep a reference
    
        
    def paste_configs(self, event=None):
        try:
            clipboard = self.root.clipboard_get()
            if clipboard.strip():
                configs = [line.strip() for line in clipboard.splitlines() if line.strip()]
                if configs:
                    self.log(f"Pasted {len(configs)} config(s) from clipboard")
                    self._test_pasted_configs(configs)
        except tk.TclError:
            pass
            
    def _test_pasted_configs(self, configs):
        self.fetch_btn.config(state=tk.DISABLED)
        self.log("Testing pasted configs...")
        
        thread = threading.Thread(target=self._test_pasted_configs_worker, args=(configs,), daemon=True)
        thread.start()
        
    
    
    
    def _test_pasted_configs_worker(self, configs):
        """
        Test configs and preserve original configs from file
        Args:
            configs: List of configs to test
        """
        try:
            self.total_configs = len(configs)
            self.tested_configs = 0
            self.working_configs = 0
            self.root.after(0, self.update_counters)
            
            self.root.after(0, lambda: self.progress.config(maximum=len(configs), value=0))
            
            best_configs = []
            all_tested_configs = []  # Store all tested configs
            
            # Load existing configs from file to preserve them
            existing_configs = set()
            if os.path.exists(self.BEST_CONFIGS_FILE):
                try:
                    with open(self.BEST_CONFIGS_FILE, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                existing_configs.add(line)
                except Exception as e:
                    self.log(f"Error reading existing configs: {str(e)}")
            
            # Keep track of configs we've successfully saved to file
            # Start with existing configs from file
            saved_configs = existing_configs.copy()
            
            # Also add backup configs if available
            if hasattr(self, 'original_configs_backup') and self.original_configs_backup:
                saved_configs.update(self.original_configs_backup)
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.LATENCY_WORKERS) as executor:
                futures = {executor.submit(self.measure_latency, config): config for config in configs}
                for future in concurrent.futures.as_completed(futures):
                    if self.stop_event.is_set():
                        # Cancel all pending futures
                        for f in futures:
                            f.cancel()
                        break
                        
                    result = future.result()
                    self.tested_configs += 1
                    all_tested_configs.append(result)  # Store all results
                    
                    # Add this config to our saved set (whether working or not)
                    saved_configs.add(result[0])
                    
                    if result[1] != float('inf'):
                        # Check if this config is already in best_configs (from current testing session)
                        existing_index = next((i for i, (uri, _) in enumerate(best_configs) if uri == result[0]), None)
                        
                        if existing_index is not None:
                            # Update existing entry if new latency is better
                            if result[1] < best_configs[existing_index][1]:
                                best_configs[existing_index] = result
                                self.log(f"Updated config latency: {result[1]:.2f}ms")
                        else:
                            # Add new working config
                            best_configs.append(result)
                            self.working_configs += 1
                            self.log(f"Working config found: {result[1]:.2f}ms")
                            
                            # Update the treeview with this new working config
                            self.best_configs = sorted(best_configs, key=lambda x: x[1])
                            self.root.after(0, self.update_treeview)
                    
                    # Incrementally save configs to file to prevent loss on stop
                    # This ensures that even if stopped, we don't lose progress
                    try:
                        with open(self.BEST_CONFIGS_FILE, 'w', encoding='utf-8') as f:
                            for config_uri in sorted(saved_configs):
                                f.write(f"{config_uri}\n")
                    except Exception as save_error:
                        self.log(f"Error saving progress: {str(save_error)}")
                    
                    # Update progress and counters
                    self.root.after(0, lambda: self.progress.config(value=self.tested_configs))
                    self.root.after(0, self.update_counters)
            
            # Final processing - only if not stopped
            if not self.stop_event.is_set() and len(all_tested_configs) > 0:
                # Load existing working configs from self.best_configs (from previous sessions)
                # and merge with newly found working configs
                existing_working_configs = []
                if hasattr(self, 'best_configs') and self.best_configs:
                    existing_working_configs = [config for config in self.best_configs if config[1] != float('inf')]
                
                # Combine existing working configs with newly found ones
                all_working_configs = existing_working_configs.copy()
                
                # Add new working configs, avoiding duplicates
                for new_config in best_configs:
                    if new_config[1] != float('inf'):
                        # Check if this config already exists in our working configs
                        existing_index = next((i for i, (uri, _) in enumerate(all_working_configs) if uri == new_config[0]), None)
                        if existing_index is not None:
                            # Update if new latency is better
                            if new_config[1] < all_working_configs[existing_index][1]:
                                all_working_configs[existing_index] = new_config
                        else:
                            # Add new working config
                            all_working_configs.append(new_config)
                
                # Update the main best_configs list with all working configs
                self.best_configs = all_working_configs
                
                # Sort by latency
                self.best_configs.sort(key=lambda x: x[1])
                
                # Final save - all configs have already been saved incrementally
                self.root.after(0, self.update_treeview)
                self.log(f"Testing complete! Found {len([c for c in best_configs if c[1] != float('inf')])} new working configs")
                self.log(f"Total working configs: {len(self.best_configs)}")
                
        except Exception as e:
            self.log(f"Error in testing pasted configs: {str(e)}")
            # On error, try to preserve what we have
            try:
                # Read current file state
                current_configs = set()
                if os.path.exists(self.BEST_CONFIGS_FILE):
                    with open(self.BEST_CONFIGS_FILE, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                current_configs.add(line)
                
                # Add original configs if available
                if hasattr(self, 'original_configs_backup') and self.original_configs_backup:
                    current_configs.update(self.original_configs_backup)
                
                # Save combined configs
                with open(self.BEST_CONFIGS_FILE, 'w', encoding='utf-8') as f:
                    for config_uri in sorted(current_configs):
                        f.write(f"{config_uri}\n")
                self.log("Error occurred - configs preserved")
            except Exception as restore_error:
                self.log(f"Failed to preserve configs: {str(restore_error)}")
                
        finally:
            # Clean up
            with self.thread_lock:
                if threading.current_thread() in self.active_threads:
                    self.active_threads.remove(threading.current_thread())
                    
            # Reset the reload button
            self.root.after(0, lambda: self.reload_btn.config(
                text="Reload Best Configs",
                style='TButton',
                state=tk.NORMAL
            ))
            self.root.after(0, lambda: self.fetch_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.progress.config(value=0))
    
    
    
    
    
    
    
    
    def stop_reloading(self):
        """Stop the reload operation without clearing existing configs"""
        self.stop_event.set()
        
        # Wait for active threads to finish (with timeout)
        with self.thread_lock:
            for thread in self.active_threads[:]:  # Create a copy of the list
                if thread.is_alive():
                    thread.join(timeout=2.0)  # Wait up to 2 seconds for thread to finish
                    if thread.is_alive():  # If still alive after timeout
                        self.log(f"Thread {thread.name} didn't stop gracefully")
        
        # Clear the active threads list
        with self.thread_lock:
            self.active_threads.clear()
        
        # Preserve all configs that are currently in the file
        # Read current state of the file (which may have been updated during testing)
        current_configs = set()
        if os.path.exists(self.BEST_CONFIGS_FILE):
            try:
                with open(self.BEST_CONFIGS_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            current_configs.add(line)
            except Exception as e:
                self.log(f"Error reading current configs: {str(e)}")
        
        # Add original configs from backup if they exist
        if hasattr(self, 'original_configs_backup') and self.original_configs_backup:
            current_configs.update(self.original_configs_backup)
        
        # Add any configs from the current best_configs list
        for config_uri, _ in self.best_configs:
            current_configs.add(config_uri)
        
        # Write back all configs to preserve them
        if current_configs:
            try:
                with open(self.BEST_CONFIGS_FILE, 'w', encoding='utf-8') as f:
                    for config_uri in sorted(current_configs):  # Sort for consistent format
                        f.write(f"{config_uri}\n")
                self.log("Stopped loading - all configs preserved in file")
            except Exception as e:
                self.log(f"Error preserving configs: {str(e)}")
        
        # Only reset the progress bar and button state, don't clear configs
        self.root.after(0, lambda: self.progress.config(value=0))
        self.root.after(0, lambda: self.reload_btn.config(
            text="Reload Best Configs",
            style='TButton',
            state=tk.NORMAL
        ))
        
        # Don't reset these counters:
        # self.tested_configs = 0
        # self.working_configs = 0
        # self.total_configs = 0
        
        self.root.after(0, self.update_counters)
        
        self.stop_event.clear()  # Clear the stop event for future operations






    
    def copy_selected_configs(self, event=None):
        selected_items = self.tree.selection()
        if not selected_items:
            return
            
        configs = []
        for item in selected_items:
            index = int(self.tree.item(item)['values'][0]) - 1
            if 0 <= index < len(self.best_configs):
                configs.append(self.best_configs[index][0])
                
        if configs:
            self.root.clipboard_clear()
            self.root.clipboard_append('\n'.join(configs))
            self.log(f"Copied {len(configs)} config(s) to clipboard")
            
    def update_counters(self):
        self.tested_label.config(text=f"Tested: {self.tested_configs}")
        self.total_label.config(text=f"Total: {self.total_configs}")
        self.working_label.config(text=f"Working: {self.working_configs}")
        
    def setup_logging(self):
        # Start log processing thread
        self.log_thread = threading.Thread(target=self.process_logs, daemon=True)
        self.log_thread.start()
        
    def log(self, message):
        """Add a log message to the queue"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_queue.put(f"[{timestamp}] {message}")
        
    def process_logs(self):
        """Process log messages from the queue"""
        while True:
            try:
                message = self.log_queue.get(timeout=0.1)
                self.root.after(0, self.update_terminal, message)
            except queue.Empty:
                continue
                
    def update_terminal(self, message):
        """Update the terminal with a new message"""
        self.terminal.config(state=tk.NORMAL)
        self.terminal.insert(tk.END, message + "\n")
        self.terminal.see(tk.END)
        self.terminal.config(state=tk.DISABLED)
        
    def parse_config_info(self, config_uri):
        """Extract basic info from config URI"""
        try:
            if config_uri.startswith("vmess://"):
                base64_str = config_uri[8:]
                padded = base64_str + '=' * (4 - len(base64_str) % 4)
                decoded = base64.urlsafe_b64decode(padded).decode('utf-8')
                vmess_config = json.loads(decoded)
                return "vmess", vmess_config.get("add", "unknown"), vmess_config.get("port", "unknown")
            elif config_uri.startswith("vless://"):
                parsed = urllib.parse.urlparse(config_uri)
                return "vless", parsed.hostname or "unknown", parsed.port or "unknown"
            elif config_uri.startswith("ss://"):
                # Handle Shadowsocks configs
                parts = config_uri[5:].split("#", 1)
                encoded_part = parts[0]
                
                if "@" in encoded_part:
                    # New style SS URI: ss://method:password@server:port
                    userinfo, server_part = encoded_part.split("@", 1)
                    server, port = server_part.split(":", 1) if ":" in server_part else (server_part, "unknown")
                else:
                    # Old style SS URI: ss://base64(method:password)@server:port
                    try:
                        decoded = base64.b64decode(encoded_part + '=' * (-len(encoded_part) % 4)).decode('utf-8')
                        if "@" in decoded:
                            userinfo, server_part = decoded.split("@", 1)
                            server, port = server_part.split(":", 1) if ":" in server_part else (server_part, "unknown")
                        else:
                            # Just method:password without server
                            server, port = "unknown", "unknown"
                    except:
                        server, port = "unknown", "unknown"
                
                return "shadowsocks", server, port
            elif config_uri.startswith("trojan://"):
                parsed = urllib.parse.urlparse(config_uri)
                return "trojan", parsed.hostname or "unknown", parsed.port or "unknown"
        except:
            pass
        return "unknown", "unknown", "unknown"
    
    
    
    def clear_temp_folder(self):
        """Clear all files in the temp folder"""
        try:
            for filename in os.listdir(self.TEMP_FOLDER):
                file_path = os.path.join(self.TEMP_FOLDER, filename)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    self.log(f"Failed to delete {file_path}: {e}")
        except Exception as e:
            self.log(f"Error clearing temp folder: {e}")
            
            
    
    
    def stop_fetching(self):
        """Stop all fetching and testing operations"""
        self.is_fetching = False
        self.fetch_btn.config(text="Fetch & Test New Configs", style='TButton')  # Revert to normal style
        self.log("Stopping all operations...")
        
        
        self.stop_event.set()
        
        # Kill all Xray processes
        self.kill_existing_xray_processes()
        
        # Clear temp folder
        self.clear_temp_folder()
        
        # Wait for threads to finish (with timeout)
        with self.thread_lock:
            for thread in self.active_threads[:]:  # Create a copy of the list
                if thread.is_alive():
                    thread.join(timeout=2.0)  # Shorter timeout
                    if thread.is_alive():  # If still alive after timeout
                        self.log(f"Thread {thread.name} didn't stop gracefully")
        
        # Clear the active threads list
        with self.thread_lock:
            self.active_threads.clear()
        
        self.stop_event.clear()
        self.log("All operations stopped")
        self.fetch_btn.config(state=tk.NORMAL)
        self.reload_btn.config(state=tk.NORMAL)
        self.progress.config(value=0)
    
    
    
    
    def fetch_and_test_configs(self):
    
        kill_xray_processes()
        """Toggle between fetching and stopping"""
        if not self.is_fetching:
            # Start fetching
            
            #self.is_fetching = True
            #self.fetch_btn.config(text="Stop Fetching Configs", style='Stop.TButton')  # Changed style
            #self.log("Starting config fetch and test...")
            
            # Clear any previous stop state
            self.stop_event.clear()
            
            self.show_mirror_selection()
            
            #thread = threading.Thread(target=self._fetch_and_test_worker, daemon=True)
            #thread.start()
        else:
            # Stop fetching
            self.stop_fetching()
        
    
    
    
    def _fetch_and_test_worker(self):
        """Worker thread for fetching and testing configs"""
        try:
            # Register this thread
            with self.thread_lock:
                self.active_threads.append(threading.current_thread())
            
            # First load ALL existing configs from file
            existing_working_configs = []
            if os.path.exists(self.BEST_CONFIGS_FILE):
                with open(self.BEST_CONFIGS_FILE, 'r', encoding='utf-8') as f:
                    existing_working_configs = [line.strip() for line in f if line.strip()]
            
            # Fetch configs
            self.log("Fetching configs from GitHub...")
            configs = self.fetch_configs()
            if not configs or self.stop_event.is_set():
                self.log("Operation stopped or no configs found")
                return
                
            self.total_configs = len(configs)
            self.tested_configs = 0
            self.working_configs = 0
            self.root.after(0, self.update_counters)
            
            self.log(f"Found {len(configs)} configs to test")
            
            # Update progress bar
            self.root.after(0, lambda: self.progress.config(maximum=len(configs), value=0))
            
            # Test configs for latency
            self.log("Testing configs for latency...")
            new_working_configs = []
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.LATENCY_WORKERS) as executor:
                futures = {executor.submit(self.measure_latency, config): config for config in configs}
                for future in concurrent.futures.as_completed(futures):
                    if self.stop_event.is_set():
                        # Cancel all pending futures
                        for f in futures:
                            f.cancel()
                        break
                        
                    result = future.result()
                    self.tested_configs += 1
                    
                    if result[1] != float('inf'):
                        config_uri = result[0]
                        # Check if config is not already in new_working_configs
                        if not any(x[0] == config_uri for x in new_working_configs):
                            new_working_configs.append(result)
                            self.working_configs += 1
                            self.log(f"Working config found: {result[1]:.2f}ms")
                            
                            # Update treeview with the new config
                            self.best_configs = sorted(new_working_configs, key=lambda x: x[1])
                            self.root.after(0, self.update_treeview)
                        
                    # Update progress and counters
                    self.root.after(0, lambda: self.progress.config(value=self.tested_configs))
                    self.root.after(0, self.update_counters)
            
            # Combine old and new working configs (remove duplicates)
            all_working_uris = set(existing_working_configs)
            all_working_uris.update([uri for uri, _ in new_working_configs])
            
            # Save ALL working configs to file (both old and new)
            with open(self.BEST_CONFIGS_FILE, 'w', encoding='utf-8') as f:
                f.write('\n'.join(all_working_uris))
                
            # Final sort and update
            self.best_configs = sorted(new_working_configs, key=lambda x: x[1])
            
            # Save working configs (for debugging)
            with open(self.WORKING_CONFIGS_FILE, "w", encoding='utf-8') as f:
                f.write("\n".join([uri for uri, _ in self.best_configs]))
                
            self.root.after(0, self.update_treeview)
            self.log(f"Testing complete! Found {len(new_working_configs)} new working configs")
            
        except Exception as e:
            if not self.stop_event.is_set():
                self.log(f"Error in fetch and test: {str(e)}")
        finally:
            # Clean up
            with self.thread_lock:
                if threading.current_thread() in self.active_threads:
                    self.active_threads.remove(threading.current_thread())
                    
            if not self.stop_event.is_set():
                self.root.after(0, lambda: self.fetch_btn.config(
                    text="Fetch & Test New Configs",
                    state=tk.NORMAL,
                    style='TButton'
                ))
                self.root.after(0, lambda: self.reload_btn.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.progress.config(value=0))
                self.is_fetching = False
            
    def update_treeview(self):
        """Update the treeview with best configs"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Add best configs (limit to prevent crashes)
        max_configs = min(100, len(self.best_configs))  # Limit to 100 configs
        for i, (config_uri, latency) in enumerate(self.best_configs[:max_configs]):
            protocol, server, port = self.parse_config_info(config_uri)
            config_preview = config_uri
            
            # Check if this is the connected config
            tags = ()
            if self.connected_config and config_uri == self.connected_config:
                tags = ('connected',)
            
            self.tree.insert('', 'end', values=(
                i + 1,
                f"{latency:.2f}",
                protocol,
                server,
                port,
                config_preview
            ), tags=tags)
            
        #self.log(f"Updated treeview with {max_configs} best configs")
        
    
    
    
    def on_tree_click(self, event):
        self.tree.after_idle(lambda: self.on_config_highlight(event))
    
    def on_config_highlight(self, event):
        """Handle single-click on treeview item"""
        selection = self.tree.selection()
        
        
        if selection:
            item = self.tree.item(selection[0])
            index = int(item['values'][0]) - 1
            
            if 0 <= index < len(self.best_configs):
                self.selected_config = self.best_configs[index][0]
                self.log(f"Selected config: {self.selected_config[:60]}...")
                
                # Update connection status based on current state
                self.connect_btn.config(state=tk.NORMAL)
                self.update_connection_status(self.is_connected)
                
    
    def on_config_select(self, event):
        """Handle double-click on treeview item"""
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            index = int(item['values'][0]) - 1
            
            if 0 <= index < len(self.best_configs):
                self.selected_config = self.best_configs[index][0]
                self.log(f"Selected config: {self.selected_config[:60]}...")
                #self.connect_btn.config(state=tk.NORMAL)
                self.connect_config()
                
    
    def connect_config(self):
    
        kill_xray_processes()
        """Connect to the selected config"""
        self.update_connection_status(True)
        
        self.status_label.config(text="Connecting....", foreground="white")
        
        
        if not self.selected_config:
            messagebox.showwarning("Warning", "Please select a config first")
            return
            
        if self.is_connected:
            self.log("Already connected. Disconnecting first...")
            self.disconnect_config()
        
        
        self.set_proxy("127.0.0.1","1080")
        
        self.log("Attempting to connect...")
        
        # Set the connected config before starting the thread
        self.connected_config = self.selected_config
        self.update_treeview()  # Refresh to show the connected config
    
    
        thread = threading.Thread(target=self._connect_worker, daemon=True)
        thread.start()
        
    def _connect_worker(self):
        """Worker thread for connecting"""
        try:
            config = self.parse_protocol(self.selected_config)
            
            with open(self.TEMP_CONFIG_FILE, "w", encoding='utf-8') as f:
                json.dump(config, f)
                
            self.log("Starting Xray process...")
            
            # Modified to run without console window
            startupinfo = None
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            
            self.xray_process = subprocess.Popen(
                [self.XRAY_PATH, "run", "-config", self.TEMP_CONFIG_FILE],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
                startupinfo=startupinfo
            )
            
            # Wait a bit for initialization
            time.sleep(2)
            
            # Check if process is still running
            if self.xray_process.poll() is None:
                self.is_connected = True
                self.root.after(0, self.update_connection_status, True)
                self.log("Connected successfully!")
                
                # Start monitoring thread
                monitor_thread = threading.Thread(target=self._monitor_xray, daemon=True)
                monitor_thread.start()
            else:
                stderr_output = self.xray_process.stderr.read()
                self.log(f"Failed to start Xray: {stderr_output}")
                self.xray_process = None
                
        except Exception as e:
            self.log(f"Connection error: {str(e)}")
            
    def _monitor_xray(self):
        """Monitor Xray process output"""
        if self.xray_process:
            for line in iter(self.xray_process.stdout.readline, ''):
                if line:
                    self.log(f"Xray: {line.strip()}")
                if self.xray_process.poll() is not None:
                    break
                    
    
    
    def update_connection_status(self, connected):
        """Update connection status in GUI"""
        if connected:
            self.status_label.config(text="Connected", foreground="SpringGreen")
            self.connect_btn.config(state=tk.DISABLED)
            self.disconnect_btn.config(state=tk.NORMAL)
        else:
            self.status_label.config(text="Disconnected", foreground="Tomato")
            self.connect_btn.config(state=tk.NORMAL if self.selected_config else tk.DISABLED)
            self.disconnect_btn.config(state=tk.DISABLED)
    
    
    
    
    def disconnect_config(self, click_button=False):
        """Disconnect from current config"""
        if not self.is_connected:
            messagebox.showinfo("Info", "Not connected")
            return
        
        
        self.unset_proxy()
        
        self.log("Disconnecting...")
        
        if self.xray_process:
            try:
                self.xray_process.terminate()
                self.xray_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.xray_process.kill()
            except Exception as e:
                self.log(f"Error terminating process: {str(e)}")
            finally:
                self.xray_process = None
                
        self.is_connected = False
        self.connected_config = None  # Clear the connected config
        if click_button :
            self.update_connection_status(False)
        else :
            self.status_label.config(text="Connecting....", foreground="white")
        
        
        # Clean up temp file
        try:
            if os.path.exists(self.TEMP_CONFIG_FILE):
                os.remove(self.TEMP_CONFIG_FILE)
        except:
            pass
            
        self.update_treeview()  # Refresh to remove the connected highlight
        self.log("Disconnected")
        
    
    
    def click_disconnect_config_button(self) :
        self.update_connection_status(False)
        self.disconnect_config(True)
    
    
    
    def set_proxy(self, proxy_server, port):
        """Set system proxy settings (cross-platform)"""
        try:
            if sys.platform == 'win32':
                # Windows implementation
                import winreg
                key = winreg.HKEY_CURRENT_USER
                subkey = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
                access = winreg.KEY_WRITE

                with winreg.OpenKey(key, subkey, 0, access) as internet_settings_key:
                    winreg.SetValueEx(internet_settings_key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
                    winreg.SetValueEx(internet_settings_key, "ProxyServer", 0, winreg.REG_SZ, f"{proxy_server}:{port}")
                    # Enable "Bypass proxy server for local addresses"
                    winreg.SetValueEx(internet_settings_key, "ProxyOverride", 0, winreg.REG_SZ, "<local>")
            
            elif sys.platform == 'darwin':
                # macOS implementation
                networks = subprocess.check_output(["networksetup", "-listallnetworkservices"]).decode('utf-8')
                for service in networks.split('\n')[1:]:  # Skip first line
                    if service.strip():
                        subprocess.run([
                            "networksetup", "-setwebproxy", service.strip(), 
                            proxy_server, str(port)
                        ])
                        subprocess.run([
                            "networksetup", "-setsecurewebproxy", service.strip(), 
                            proxy_server, str(port)
                        ])
                        subprocess.run([
                            "networksetup", "-setsocksfirewallproxy", service.strip(), 
                            proxy_server, str(port)
                        ])
            
            elif sys.platform == 'linux':
                # Linux implementation (GNOME)
                try:
                    subprocess.run([
                        "gsettings", "set", "org.gnome.system.proxy", 
                        "mode", "manual"
                    ])
                    subprocess.run([
                        "gsettings", "set", "org.gnome.system.proxy.socks", 
                        "host", proxy_server
                    ])
                    subprocess.run([
                        "gsettings", "set", "org.gnome.system.proxy.socks", 
                        "port", str(port)
                    ])
                except:
                    self.log("Could not set proxy automatically on Linux. Please set it manually.")
        except Exception as e:
            self.log(f"Error setting proxy: {str(e)}")

        
        
        
    def unset_proxy(self):
        """Unset system proxy settings (cross-platform)"""
        try:
            if sys.platform == 'win32':
                # Windows implementation
                import winreg
                key = winreg.HKEY_CURRENT_USER
                subkey = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
                access = winreg.KEY_WRITE

                with winreg.OpenKey(key, subkey, 0, access) as internet_settings_key:
                    winreg.SetValueEx(internet_settings_key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
                    try:
                        winreg.DeleteValue(internet_settings_key, "ProxyServer")
                    except FileNotFoundError:
                        pass  # Value doesn't exist, that's fine
                    try:
                        winreg.DeleteValue(internet_settings_key, "ProxyOverride")
                    except FileNotFoundError:
                        pass  # Value doesn't exist, that's fine

            elif sys.platform == 'darwin':
                # macOS implementation
                networks = subprocess.check_output(["networksetup", "-listallnetworkservices"]).decode('utf-8')
                for service in networks.split('\n')[1:]:  # Skip first line
                    if service.strip():
                        subprocess.run([
                            "networksetup", "-setwebproxystate", service.strip(), "off"
                        ])
                        subprocess.run([
                            "networksetup", "-setsecurewebproxystate", service.strip(), "off"
                        ])
                        subprocess.run([
                            "networksetup", "-setsocksfirewallproxystate", service.strip(), "off"
                        ])
            
            elif sys.platform == 'linux':
                # Linux implementation (GNOME)
                try:
                    subprocess.run([
                        "gsettings", "set", "org.gnome.system.proxy", 
                        "mode", "none"
                    ])
                except:
                    self.log("Could not unset proxy automatically on Linux. Please unset it manually.")
        except Exception as e:
            self.log(f"Error unsetting proxy: {str(e)}")
    
    
    
    
    # Include all the parsing methods from original script
    def vmess_to_json(self, vmess_url):
        if not vmess_url.startswith("vmess://"):
            raise ValueError("Invalid VMess URL format")
        
        base64_str = vmess_url[8:]
        padded = base64_str + '=' * (4 - len(base64_str) % 4)
        decoded_bytes = base64.urlsafe_b64decode(padded)
        decoded_str = decoded_bytes.decode('utf-8')
        vmess_config = json.loads(decoded_str)
        
        xray_config = {
            "inbounds": [{
                "port": self.SOCKS_PORT,
                "listen": "127.0.0.1",
                "protocol": "socks",
                "settings": {"udp": True}
            }],
            "outbounds": [{
                "protocol": "vmess",
                "settings": {
                    "vnext": [{
                        "address": vmess_config["add"],
                        "port": int(vmess_config["port"]),
                        "users": [{
                            "id": vmess_config["id"],
                            "alterId": int(vmess_config.get("aid", 0)),
                            "security": vmess_config.get("scy", "auto")
                        }]
                    }]
                },
                "streamSettings": {
                    "network": vmess_config.get("net", "tcp"),
                    "security": vmess_config.get("tls", ""),
                    "tcpSettings": {
                        "header": {
                            "type": vmess_config.get("type", "none"),
                            "request": {
                                "path": [vmess_config.get("path", "/")],
                                "headers": {
                                    "Host": [vmess_config.get("host", "")]
                                }
                            }
                        }
                    } if vmess_config.get("net") == "tcp" and vmess_config.get("type") == "http" else None
                }
            }]
        }
        
        if not xray_config["outbounds"][0]["streamSettings"]["security"]:
            del xray_config["outbounds"][0]["streamSettings"]["security"]
        if not xray_config["outbounds"][0]["streamSettings"].get("tcpSettings"):
            xray_config["outbounds"][0]["streamSettings"].pop("tcpSettings", None)
        
        return xray_config

    def parse_vless(self, uri):
        parsed = urllib.parse.urlparse(uri)
        config = {
            "inbounds": [{
                "port": self.SOCKS_PORT,
                "listen": "127.0.0.1",
                "protocol": "socks",
                "settings": {"udp": True}
            }],
            "outbounds": [{
                "protocol": "vless",
                "settings": {
                    "vnext": [{
                        "address": parsed.hostname,
                        "port": parsed.port,
                        "users": [{
                            "id": parsed.username,
                            "encryption": parse_qs(parsed.query).get("encryption", ["none"])[0]
                        }]
                    }]
                },
                "streamSettings": {
                    "network": parse_qs(parsed.query).get("type", ["tcp"])[0],
                    "security": parse_qs(parsed.query).get("security", ["none"])[0]
                }
            }]
        }
        return config

    def parse_shadowsocks(self, uri):
        if not uri.startswith("ss://"):
            raise ValueError("Invalid Shadowsocks URI")
        
        parts = uri[5:].split("#", 1)
        encoded_part = parts[0]
        remark = urllib.parse.unquote(parts[1]) if len(parts) > 1 else "Imported Shadowsocks"

        if "@" in encoded_part:
            userinfo, server_part = encoded_part.split("@", 1)
        else:
            decoded = base64.b64decode(encoded_part + '=' * (-len(encoded_part) % 4)).decode('utf-8')
            if "@" in decoded:
                userinfo, server_part = decoded.split("@", 1)
            else:
                userinfo = decoded
                server_part = ""

        if ":" in server_part:
            server, port = server_part.rsplit(":", 1)
            port = int(port)
        else:
            server = server_part
            port = 443

        try:
            decoded_userinfo = base64.b64decode(userinfo + '=' * (-len(userinfo) % 4)).decode('utf-8')
        except:
            decoded_userinfo = base64.b64decode(encoded_part + '=' * (-len(encoded_part) % 4)).decode('utf-8')
            if "@" in decoded_userinfo:
                userinfo_part, server_part = decoded_userinfo.split("@", 1)
                if ":" in server_part:
                    server, port = server_part.rsplit(":", 1)
                    port = int(port)
                decoded_userinfo = userinfo_part

        if ":" not in decoded_userinfo:
            raise ValueError("Invalid Shadowsocks URI")
        
        method, password = decoded_userinfo.split(":", 1)

        config = {
            "inbounds": [{
                "port": self.SOCKS_PORT,
                "listen": "127.0.0.1",
                "protocol": "socks",
                "settings": {"udp": True}
            }],
            "outbounds": [
                {
                    "protocol": "shadowsocks",
                    "settings": {
                        "servers": [{
                            "address": server,
                            "port": port,
                            "method": method,
                            "password": password
                        }]
                    },
                    "tag": "proxy"
                },
                {
                    "protocol": "freedom",
                    "tag": "direct"
                }
            ],
            "routing": {
                "domainStrategy": "IPOnDemand",
                "rules": [{
                    "type": "field",
                    "ip": ["geoip:private"],
                    "outboundTag": "direct"
                }]
            },
            "geoip": {
                "path": "geoip.dat",
                "code": "geoip.dat"
            },
            "geosite": {
                "path": "dlc.dat",
                "code": "dlc.dat"
            }
        }
        
        return config

    def parse_trojan(self, uri):
        if not uri.startswith("trojan://"):
            raise ValueError("Invalid Trojan URI")
        
        parsed = urllib.parse.urlparse(uri)
        password = parsed.username
        server = parsed.hostname
        port = parsed.port
        query = parse_qs(parsed.query)
        remark = urllib.parse.unquote(parsed.fragment) if parsed.fragment else "Imported Trojan"
        
        # Extract query parameters with defaults
        network = query.get("type", ["tcp"])[0]
        security = "tls"  # Trojan always uses TLS
        sni = query.get("sni", [""])[0]
        host = query.get("host", [""])[0]
        path = query.get("path", [""])[0]
        header_type = query.get("headerType", ["none"])[0]

        # Configure streamSettings based on network type
        stream_settings = {
            "network": network,
            "security": security,
            "tlsSettings": {
                "serverName": sni,
                "allowInsecure": False  # Always enforce TLS security
            }
        }

        # Add transport-specific settings
        if network == "tcp":
            stream_settings["tcpSettings"] = {
                "header": {
                    "type": header_type,
                    "request": {
                        "headers": {
                            "Host": [host] if host else []
                        }
                    }
                }
            }
        elif network == "ws":
            stream_settings["wsSettings"] = {
                "path": path,
                "headers": {
                    "Host": host
                }
            }
        elif network == "grpc":
            stream_settings["grpcSettings"] = {
                "serviceName": path
            }
        
        config = {
            "inbounds": [{
                "port": self.SOCKS_PORT,
                "listen": "127.0.0.1",
                "protocol": "socks",
                "settings": {
                    "udp": True,
                    "auth": "noauth"
                }
            }],
            "outbounds": [
                {
                    "protocol": "trojan",
                    "settings": {
                        "servers": [{
                            "address": server,
                            "port": port,
                            "password": password,
                            "email": remark  # Optional: Use remark as email identifier
                        }]
                    },
                    "streamSettings": stream_settings,
                    "tag": "proxy"
                },
                {
                    "protocol": "freedom",
                    "tag": "direct"
                }
            ],
            "routing": {
                "domainStrategy": "IPOnDemand",
                "rules": [
                    {
                        "type": "field",
                        "ip": ["geoip:private"],
                        "outboundTag": "direct"
                    },
                    {
                        "type": "field",
                        "domain": ["geosite:category-ads-all"],
                        "outboundTag": "block"
                    }
                ]
            },
            "geoip": {
                "path": "geoip.dat",
                "code": "geoip.dat"
            },
            "geosite": {
                "path": "geosite.dat",
                "code": "geosite.dat"
            }
        }
        
        return config

    def parse_protocol(self, uri):
        if uri.startswith("vmess://"):
            return self.vmess_to_json(uri)
        elif uri.startswith("vless://"):
            return self.parse_vless(uri)
        elif uri.startswith("ss://"):
            return self.parse_shadowsocks(uri)
        elif uri.startswith("trojan://"):
            return self.parse_trojan(uri)
        raise ValueError("Unsupported protocol")

    def is_port_available(self, port):
        """Check if a port is available"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return True
            except:
                return False

    def get_available_port(self):
        """Get a random available port"""
        for _ in range(10):
            port = random.randint(49152, 65535)
            if self.is_port_available(port):
                return port
        return 1080

    def measure_latency(self, config_uri):
        if self.stop_event.is_set():
            return (config_uri, float('inf'))
            
        try:
            socks_port = self.get_available_port()
            
            if socks_port is None:
                socks_port = 1080 + random.randint(1, 100)
            
            config = self.parse_protocol(config_uri)
            config['inbounds'][0]['port'] = socks_port
            
            
            # Add DNS settings to the config
            #config['dns'] = {
            #    "servers": [
            #        "8.8.8.8",  # Google DNS
            #        "1.1.1.1",  # Cloudflare DNS
            #        "185.51.200.2",
            #        "178.22.122.100",
            #        "localhost"
            #    ]
            #}
            
            rand_suffix = random.randint(100000, 999999)
            temp_config_file = os.path.join(self.TEMP_FOLDER, f"temp_config_{rand_suffix}.json")
            
            with open(temp_config_file, "w", encoding='utf-8') as f:
                json.dump(config, f)
                
            startupinfo = None
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            
            xray_process = subprocess.Popen(
                [self.XRAY_PATH, "run", "-config", temp_config_file],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
                startupinfo=startupinfo
            )
            
            # Check stop event before proceeding
            if self.stop_event.is_set():
                xray_process.terminate()
                try:
                    os.remove(temp_config_file)
                except:
                    pass
                return (config_uri, float('inf'))
                
            time.sleep(0.1)
            
            proxies = {
                'http': f'socks5://127.0.0.1:{socks_port}',
                'https': f'socks5://127.0.0.1:{socks_port}'
            }
            
            latency = float('inf')
            try:
                start_time = time.perf_counter()
                response = requests.get(
                    self.PING_TEST_URL,
                    proxies=proxies,
                    timeout=10,
                    headers={
                        'Cache-Control': 'no-cache',
                        'Connection': 'close'
                    }
                )
                if response.status_code == 200:
                    latency = (time.perf_counter() - start_time) * 1000
            except requests.RequestException:
                pass
            finally:
                xray_process.terminate()
                try:
                    xray_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    xray_process.kill()
                
                try:
                    os.remove(temp_config_file)
                except:
                    pass
                
                time.sleep(0.1)
            
            return (config_uri, latency)
        
        except Exception as e:
            return (config_uri, float('inf'))

    
    
    
    def update_xray_core(self):
        """Update Xray core executable"""
        self.log("Starting Xray core update...")
        self.log_system_info()  # Log system info before updating
        thread = threading.Thread(target=self._update_xray_core_worker, daemon=True)
        thread.start()

    def _update_xray_core_worker(self):
        """Worker thread for updating Xray core"""
        try:
            # Kill any running Xray processes
            self.kill_existing_xray_processes()
            
            self.log("Downloading latest Xray core...")
            self.log(f"Using URL: {self.XRAY_CORE_URL}")
            
            response = requests.get(self.XRAY_CORE_URL, stream=True)
            response.raise_for_status()
            
            # Get the total file size from headers
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            # Save the downloaded zip file
            zip_path = os.path.join(self.TEMP_FOLDER, "xray_update.zip")
            
            # Create temp folder if it doesn't exist
            os.makedirs(self.TEMP_FOLDER, exist_ok=True)
            
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:  # filter out keep-alive new chunks
                        f.write(chunk)
                        downloaded += len(chunk)
                        # Calculate progress percentage
                        progress = (downloaded / total_size) * 100 if total_size > 0 else 0
                        # Update log with progress
                        self.log(f"Download progress: {progress:.1f}% ({downloaded}/{total_size} bytes)")
            
            self.log("Extracting Xray core...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Get total number of files for progress tracking
                file_list = zip_ref.namelist()
                total_files = len(file_list)
                extracted_files = 0
                
                # Determine the correct executable name based on OS
                executable_name = "xray.exe" if platform.system() == "Windows" else "xray"
                
                for file in file_list:
                    zip_ref.extract(file, self.TEMP_FOLDER)
                    extracted_files += 1
                    progress = (extracted_files / total_files) * 100
                    self.log(f"Extraction progress: {progress:.1f}% ({extracted_files}/{total_files} files)")
                    
                    # Check if this is the xray executable file
                    if file.lower().endswith(executable_name.lower()) or file.lower() == executable_name.lower():
                        # Move it to the main directory
                        extracted_path = os.path.join(self.TEMP_FOLDER, file)
                        shutil.move(extracted_path, self.XRAY_PATH)
                        
                        # Make executable on Unix-like systems
                        if platform.system() != "Windows":
                            os.chmod(self.XRAY_PATH, 0o755)
            
            self.log("Xray core updated successfully!")
            messagebox.showinfo("Success", "Xray core updated successfully!")
            
        except Exception as e:
            self.log(f"Error updating Xray core: {str(e)}")
            messagebox.showerror("Error", f"Failed to update Xray core: {str(e)}")
        finally:
            # Clean up
            try:
                os.remove(zip_path)
            except:
                pass
    
    
    
    
    
    def update_geofiles(self):
        """Update GeoFiles (geoip.dat and geosite.dat) using multi-threading for each file"""
        self.log("Starting GeoFiles update with multi-threading...")
        thread = threading.Thread(target=self._update_geofiles_worker, daemon=True)
        thread.start()

    def _download_file_segmented(self, url, filename, file_description, num_segments=4):
        """Download a file using multiple segments for faster download"""
        try:
            self.log(f"Starting multi-threaded download of {file_description}...")
            
            # Get file size first
            head_response = requests.head(url)
            head_response.raise_for_status()
            total_size = int(head_response.headers.get('content-length', 0))
            
            if total_size == 0:
                # Fall back to normal download if size is unknown
                return self._download_file_normal(url, filename, file_description)
            
            self.log(f"{file_description}: File size {total_size} bytes, downloading with {num_segments} threads...")
            
            # Calculate segment size
            segment_size = total_size // num_segments
            segments = []
            
            # Create segments
            for i in range(num_segments):
                start = i * segment_size
                end = start + segment_size - 1 if i < num_segments - 1 else total_size - 1
                segments.append((start, end))
            
            # Download segments concurrently
            segment_files = []
            segment_progress = [0] * num_segments
            
            with ThreadPoolExecutor(max_workers=num_segments) as executor:
                future_to_segment = {
                    executor.submit(self._download_segment, url, start, end, f"{filename}.part{i}", i, segment_progress): i
                    for i, (start, end) in enumerate(segments)
                }
                
                # Monitor progress
                completed_segments = 0
                while completed_segments < num_segments:
                    time.sleep(0.5)  # Update every 500ms
                    total_progress = sum(segment_progress) / num_segments
                    self.log(f"{file_description}: Overall progress {total_progress:.1f}%")
                    
                    for future in list(future_to_segment.keys()):
                        if future.done():
                            segment_index = future_to_segment[future]
                            try:
                                success, part_filename = future.result()
                                if success:
                                    segment_files.append((segment_index, part_filename))
                                    self.log(f"{file_description}: Thread {segment_index + 1} completed")
                                else:
                                    raise Exception(f"Failed to download segment {segment_index}")
                            except Exception as e:
                                self.log(f"Error in thread {segment_index}: {str(e)}")
                                # Clean up and fall back to normal download
                                for _, part_file in segment_files:
                                    try:
                                        os.remove(part_file)
                                    except:
                                        pass
                                return self._download_file_normal(url, filename, file_description)
                            
                            del future_to_segment[future]
                            completed_segments += 1
            
            # Combine segments
            segment_files.sort(key=lambda x: x[0])  # Sort by segment index
            self.log(f"{file_description}: Combining segments...")
            with open(filename, 'wb') as outfile:
                for _, part_filename in segment_files:
                    with open(part_filename, 'rb') as infile:
                        outfile.write(infile.read())
                    os.remove(part_filename)  # Clean up part file
            
            self.log(f"{file_description} multi-threaded download complete!")
            return True, f"{file_description} downloaded successfully"
            
        except Exception as e:
            self.log(f"Multi-threaded download failed for {file_description}, error: {str(e)}")
            # Fall back to normal download
            return self._download_file_normal(url, filename, file_description)

    def _download_segment(self, url, start, end, filename, segment_index, progress_array):
        """Download a specific segment of a file with progress tracking"""
        try:
            headers = {'Range': f'bytes={start}-{end}'}
            response = requests.get(url, headers=headers, stream=True)
            response.raise_for_status()
            
            segment_size = end - start + 1
            downloaded = 0
            
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        # Update progress for this segment
                        progress_array[segment_index] = (downloaded / segment_size) * 100
            
            return True, filename
        except Exception as e:
            return False, str(e)

    def _download_file_normal(self, url, filename, file_description):
        """Fallback method for normal single-threaded download"""
        try:
            self.log(f"Starting normal download of {file_description}...")
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            chunk_size = 8192
            
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        progress = (downloaded / total_size) * 100 if total_size > 0 else 0
                        self.log(f"{file_description}: {progress:.1f}% ({downloaded}/{total_size} bytes)")
            
            self.log(f"{file_description} download complete!")
            return True, f"{file_description} downloaded successfully"
            
        except Exception as e:
            return False, f"Error downloading {file_description}: {str(e)}"

    
    
    
    def _download_file(self, url, filename, file_description):
        """Download a single file with progress tracking"""
        try:
            self.log(f"Starting download of {file_description}...")
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            chunk_size = 8192
            
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:  # filter out keep-alive new chunks
                        f.write(chunk)
                        downloaded += len(chunk)
                        progress = (downloaded / total_size) * 100
                        self.log(f"{file_description}: {progress:.1f}% ({downloaded}/{total_size} bytes)")
            
            self.log(f"{file_description} download complete!")
            return True, f"{file_description} downloaded successfully"
            
        except Exception as e:
            return False, f"Error downloading {file_description}: {str(e)}"
    
    
    
    
    def _update_geofiles_worker(self):
        """Worker thread for updating GeoFiles using multi-threading for each file"""
        try:
            # URLs for GeoFiles
            geoip_url = "https://github.com/v2fly/geoip/releases/latest/download/geoip.dat"
            geosite_url = "https://github.com/v2fly/domain-list-community/releases/latest/download/dlc.dat"
            
            # Download geoip.dat with multi-threading
            self.log("=== Starting geoip.dat download ===")
            success1, message1 = self._download_file_segmented(geoip_url, "geoip.dat", "geoip.dat", num_segments=4)
            
            if success1:
                self.log(f"✓ {message1}")
            else:
                self.log(f"✗ {message1}")
                raise Exception(f"Failed to download geoip.dat: {message1}")
            
            # Download dlc.dat with multi-threading
            self.log("=== Starting dlc.dat download ===")
            success2, message2 = self._download_file_segmented(geosite_url, "dlc.dat", "dlc.dat", num_segments=4)
            
            if success2:
                self.log(f"✓ {message2}")
            else:
                self.log(f"✗ {message2}")
                raise Exception(f"Failed to download dlc.dat: {message2}")
            
            self.log("=== All GeoFiles downloads completed successfully! ===")
            messagebox.showinfo("Success", "GeoFiles updated successfully!")
            
        except Exception as e:
            self.log(f"Error updating GeoFiles: {str(e)}")
            self.log("")
            self.log("You can manually download the required files:")
            self.log("1. GeoIP file: https://github.com/v2fly/geoip/releases/latest/download/geoip.dat")
            self.log("2. Geosite file: https://github.com/v2fly/domain-list-community/releases/latest/download/dlc.dat")
            self.log("")
            self.log("Instructions:")
            self.log("1. Download both files using the links above")
            self.log("2. Place them in the same directory as this program")
            self.log("3. Make sure they are named exactly:")
            self.log("   - geoip.dat")
            self.log("   - dlc.dat")
            self.log("4. Restart the program if needed")

    def update_all_concurrently(self):
        """Update both Xray core and GeoFiles concurrently"""
        self.log("Starting concurrent update of Xray core and GeoFiles...")
        
        # Create threads for both updates
        xray_thread = threading.Thread(target=self._update_xray_core_worker, daemon=True)
        geofiles_thread = threading.Thread(target=self._update_geofiles_worker, daemon=True)
        
        # Start both threads
        xray_thread.start()
        geofiles_thread.start()
        
        # Optionally wait for both to complete (if you need to know when they're done)
        # xray_thread.join()
        # geofiles_thread.join()
        
        self.log("All updates started concurrently!")

    
    
    
    
    # Enhanced version with download segmentation for even faster downloads
    def _download_file_segmented(self, url, filename, file_description, num_segments=4):
        """Download a file using multiple segments for faster download"""
        try:
            self.log(f"Starting segmented download of {file_description}...")
            
            # Get file size first
            head_response = requests.head(url)
            head_response.raise_for_status()
            total_size = int(head_response.headers.get('content-length', 0))
            
            if total_size == 0:
                # Fall back to normal download if size is unknown
                return self._download_file(url, filename, file_description)
            
            # Calculate segment size
            segment_size = total_size // num_segments
            segments = []
            
            # Create segments
            for i in range(num_segments):
                start = i * segment_size
                end = start + segment_size - 1 if i < num_segments - 1 else total_size - 1
                segments.append((start, end))
            
            # Download segments concurrently
            segment_files = []
            with ThreadPoolExecutor(max_workers=num_segments) as executor:
                future_to_segment = {
                    executor.submit(self._download_segment, url, start, end, f"{filename}.part{i}"): i
                    for i, (start, end) in enumerate(segments)
                }
                
                for future in as_completed(future_to_segment):
                    segment_index = future_to_segment[future]
                    try:
                        success, part_filename = future.result()
                        if success:
                            segment_files.append((segment_index, part_filename))
                            self.log(f"{file_description}: Segment {segment_index + 1}/{num_segments} complete")
                        else:
                            raise Exception(f"Failed to download segment {segment_index}")
                    except Exception as e:
                        self.log(f"Error downloading segment {segment_index}: {str(e)}")
                        return False, f"Error downloading {file_description}: {str(e)}"
            
            # Combine segments
            segment_files.sort(key=lambda x: x[0])  # Sort by segment index
            with open(filename, 'wb') as outfile:
                for _, part_filename in segment_files:
                    with open(part_filename, 'rb') as infile:
                        outfile.write(infile.read())
                    os.remove(part_filename)  # Clean up part file
            
            self.log(f"{file_description} segmented download complete!")
            return True, f"{file_description} downloaded successfully"
            
        except Exception as e:
            return False, f"Error downloading {file_description}: {str(e)}"

    def _download_segment(self, url, start, end, filename):
        """Download a specific segment of a file"""
        try:
            headers = {'Range': f'bytes={start}-{end}'}
            response = requests.get(url, headers=headers, stream=True)
            response.raise_for_status()
            
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            return True, filename
        except Exception as e:
            return False, str(e)
    
    
    
    def fetch_configs(self):
        max_retries = 3
        retry_delay = 2  # seconds
        
        # Different approaches to try
        strategies = [
            ("System default", None),
            ("Google DNS", self._try_with_google_dns),
            ("Cloudflare DNS", self._try_with_cloudflare_dns),
            ("Direct IP", self._try_with_direct_ip),
        ]
        
        for strategy_name, strategy_func in strategies:
            self.log(f"Trying strategy: {strategy_name}")
            
            for attempt in range(max_retries):
                try:
                    if strategy_func:
                        response = strategy_func()
                    else:
                        response = requests.get(self.CONFIGS_URL, timeout=10)
                    
                    response.raise_for_status()
                    response.encoding = 'utf-8'
                    configs = [line.strip() for line in response.text.splitlines() if line.strip()]
                    self.log(f"Successfully fetched configs using: {strategy_name}")
                    return configs[::-1]
                    
                except requests.exceptions.Timeout:
                    if attempt < max_retries - 1:
                        self.log(f"Timeout, retrying in {retry_delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
                        continue
                    self.log(f"Max retries reached with {strategy_name}")
                    break
                except Exception as e:
                    self.log(f"Error with {strategy_name}: {str(e)}")
                    break
        
        self.log("All strategies failed")
        return []

    def _try_with_google_dns(self):
        """Try request with Google DNS via system DNS change"""
        return self._try_with_custom_dns(['8.8.8.8', '8.8.4.4'])

    def _try_with_cloudflare_dns(self):
        """Try request with Cloudflare DNS via system DNS change"""
        return self._try_with_custom_dns(['1.1.1.1', '1.0.0.1'])

    def _try_with_custom_dns(self, dns_servers):
        """Try request with custom DNS servers"""
        # Create a custom session with DNS override
        session = requests.Session()
        
        # Try to resolve hostname manually using custom DNS
        try:
            hostname = self.CONFIGS_URL.split('//')[1].split('/')[0]
            ip = self._resolve_hostname(hostname, dns_servers[0])
            
            # Replace hostname with IP in URL
            url_with_ip = self.CONFIGS_URL.replace(hostname, ip)
            
            # Add Host header to maintain virtual hosting
            headers = {'Host': hostname}
            
            return session.get(url_with_ip, headers=headers, timeout=10)
        except:
            # Fallback to normal request
            return session.get(self.CONFIGS_URL, timeout=10)

    def _resolve_hostname(self, hostname, dns_server):
        """Resolve hostname using specific DNS server"""
        try:
            import dns.resolver
            resolver = dns.resolver.Resolver()
            resolver.nameservers = [dns_server]
            result = resolver.resolve(hostname, 'A')
            return str(result[0])
        except:
            # Fallback to system tools
            return self._resolve_with_system_tools(hostname, dns_server)

    def _resolve_with_system_tools(self, hostname, dns_server):
        """Resolve hostname using system tools as fallback"""
        try:
            if platform.system() == "Windows":
                result = subprocess.run(['nslookup', hostname, dns_server], 
                                      capture_output=True, text=True, timeout=5)
                # Parse nslookup output
                for line in result.stdout.split('\n'):
                    if 'Address:' in line and dns_server not in line:
                        return line.split(':')[1].strip()
            else:
                result = subprocess.run(['dig', f'@{dns_server}', hostname, '+short'], 
                                      capture_output=True, text=True, timeout=5)
                ip = result.stdout.strip().split('\n')[0]
                if ip and not ip.startswith(';'):
                    return ip
        except:
            pass
        
        # Final fallback - use socket with default DNS
        return socket.gethostbyname(hostname)

    def _try_with_direct_ip(self):
        """Try connecting to GitHub's IP directly"""
        github_ips = [
            '140.82.112.3',  # Common GitHub IP
            '140.82.114.3',  # Alternative GitHub IP
            '140.82.113.3',  # Another GitHub IP
            '140.82.121.4' 
        ]
        
        hostname = self.CONFIGS_URL.split('//')[1].split('/')[0]
        
        for ip in github_ips:
            try:
                url_with_ip = self.CONFIGS_URL.replace(hostname, ip)
                headers = {'Host': hostname}
                response = requests.get(url_with_ip, headers=headers, timeout=10)
                return response
            except:
                continue
        
        raise Exception("All direct IP attempts failed")

def main():
    # Kill any existing Xray processes
    kill_xray_processes()
    
    # Create root window
    root = tk.Tk()
    
    # Set window title with platform info
    platform_name = platform.system()
    if platform_name == "Darwin":
        platform_name = "macOS"
    root.title(f"VPN Config Manager ({platform_name})")
    
    # Create and run application
    app = VPNConfigGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
