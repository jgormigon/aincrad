from tkinter import *
from tkinter import ttk
from tkinter import filedialog
import threading
import win32gui
import hashlib
import secrets
import keyboard
import src.tesseract_config  # Configure Tesseract before importing bot_logic
from src.bot_logic import run_bot, default_config, bot_stop_event

# Modern color scheme - removed blue accent, using purple/teal instead
COLORS = {
    'bg': '#1e1e1e',  # Dark background
    'fg': '#ffffff',  # White text
    'accent': '#6a1b9a',  # Deep purple accent (replaces blue)
    'accent_light': '#9c27b0',  # Lighter purple
    'success': '#00c853',  # Green
    'danger': '#d32f2f',  # Red
    'warning': '#ff9800',  # Orange
    'frame_bg': '#2d2d2d',  # Slightly lighter frame
    'entry_bg': '#3d3d3d',  # Entry background
    'button_hover': '#4a148c',  # Darker purple for hover
    'border': '#404040',  # Subtle border color
}

def get_all_windows():
    """Get all visible window titles"""
    windows = []
    
    def enum_handler(hwnd, ctx):
        if win32gui.IsWindowVisible(hwnd):
            window_title = win32gui.GetWindowText(hwnd)
            if window_title:  # Only include windows with titles
                windows.append(window_title)
    
    win32gui.EnumWindows(enum_handler, None)
    return sorted(set(windows))  # Remove duplicates and sort

# Note: Tkinter doesn't natively support rounded corners easily
# We'll use subtle borders and better styling to create a softer appearance

class HotkeyCaptureEntry:
    """A widget that captures hotkeys when clicked"""
    def __init__(self, parent, textvariable, width=15, **kwargs):
        self.textvariable = textvariable
        self.capturing = False
        self.entry = Entry(parent, textvariable=textvariable, width=width,
                          bg=COLORS['entry_bg'], fg=COLORS['fg'],
                          insertbackground=COLORS['fg'],
                          font=("Arial", 9), relief=FLAT, state='readonly',
                          cursor="hand2", readonlybackground=COLORS['entry_bg'],
                          highlightthickness=1, highlightbackground=COLORS['border'],
                          highlightcolor=COLORS['accent'], **kwargs)
        self.entry.bind('<Button-1>', self.start_capture)
        self.entry.bind('<FocusIn>', lambda e: self.start_capture(e) if not self.capturing else None)
        
    def pack(self, **kwargs):
        return self.entry.pack(**kwargs)
    
    def start_capture(self, event):
        """Start capturing hotkey input"""
        if self.capturing:
            return
        self.capturing = True
        self.entry.config(state='normal')
        self.entry.delete(0, END)
        self.entry.insert(0, "Press any key...")
        self.entry.config(fg=COLORS['warning'])
        self.entry.focus_set()
        
        # Bind to key events - use root level binding to catch all keys
        self.entry.master.bind_all('<KeyPress>', self.capture_key)
        self.entry.bind('<FocusOut>', self.stop_capture)
        
    def capture_key(self, event):
        """Capture the pressed key combination"""
        if not self.capturing:
            return
        
        modifiers = []
        if event.state & 0x4:  # Control
            modifiers.append('ctrl')
        if event.state & 0x1:  # Shift
            modifiers.append('shift')
        if event.state & 0x20000:  # Alt
            modifiers.append('alt')
        
        # Get the key name
        key_name = event.keysym.lower()
        
        # Skip modifier keys alone
        if key_name in ['control_l', 'control_r', 'shift_l', 'shift_r', 'alt_l', 'alt_r', 'meta_l', 'meta_r']:
            return
        
        # Format the hotkey string
        if modifiers:
            hotkey_str = '+'.join(modifiers) + '+' + key_name
        else:
            hotkey_str = key_name
        
        # Update the textvariable
        self.textvariable.set(hotkey_str)
        self.entry.config(fg=COLORS['fg'])
        self.entry.config(state='readonly')
        self.capturing = False
        
        # Unbind events
        self.entry.master.unbind_all('<KeyPress>')
        self.entry.unbind('<FocusOut>')
        
        # Update hotkeys
        if hasattr(self, 'update_callback'):
            self.update_callback()
    
    def stop_capture(self, event):
        """Stop capturing if focus is lost"""
        if self.capturing:
            self.entry.config(state='readonly')
            self.entry.config(fg=COLORS['fg'])
            self.capturing = False
            try:
                self.entry.master.unbind_all('<KeyPress>')
            except:
                pass
            self.entry.unbind('<FocusOut>')

class BotGUI:
    def __init__(self, root):
        self.root = root
        # Generate a random hash code for window title to avoid detection
        random_bytes = secrets.token_bytes(16)
        hash_code = hashlib.sha256(random_bytes).hexdigest()[:12].upper()
        self.root.title(f"{hash_code}")
        self.root.geometry('700x800')
        
        # Apply modern dark theme
        self.root.configure(bg=COLORS['bg'])
        
        # Configuration variables
        self.config = default_config.copy()
        self.bot_running = False
        self.selected_window = StringVar(value="Maplestory")
        
        # Hotkey variables
        self.start_hotkey = StringVar(value="f1")
        self.stop_hotkey = StringVar(value="f2")
        self.hotkey_handlers = {}  # Store hotkey handlers
        
        self.create_widgets()
        self.setup_hotkeys()
        
    def setup_hotkeys(self):
        """Setup hotkey listeners"""
        try:
            # Register start hotkey
            keyboard.add_hotkey(self.start_hotkey.get().lower(), self.start_bot)
            # Register stop hotkey
            keyboard.add_hotkey(self.stop_hotkey.get().lower(), self.stop_bot)
        except Exception as e:
            print(f"Error setting up hotkeys: {e}")
    
    def update_hotkeys(self):
        """Update hotkey bindings"""
        try:
            # Remove old hotkeys
            keyboard.unhook_all_hotkeys()
            # Register new hotkeys
            keyboard.add_hotkey(self.start_hotkey.get().lower(), self.start_bot)
            keyboard.add_hotkey(self.stop_hotkey.get().lower(), self.stop_bot)
        except Exception as e:
            print(f"Error updating hotkeys: {e}")
    
    def create_widgets(self):
        # Header frame with title
        header_frame = Frame(self.root, bg=COLORS['bg'])
        header_frame.pack(fill=X, padx=10, pady=(10, 5))
        
        title_label = Label(header_frame, text="Aincrad", 
                          font=("Arial", 18, "bold"), bg=COLORS['bg'], fg=COLORS['accent'])
        title_label.pack()
        
        # Container frame for Window Selection and Cube Type (same row)
        top_frame = Frame(self.root, bg=COLORS['bg'])
        top_frame.pack(fill=X, padx=10, pady=5)
        
        # Window Selection and Cube Type Section (before tabs)
        self.create_window_selection(top_frame)
        self.create_cube_type_selection(top_frame)
        
        # Create notebook for tabs with modern style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TNotebook', background=COLORS['bg'], borderwidth=0)
        style.configure('TNotebook.Tab', background=COLORS['frame_bg'], foreground=COLORS['fg'],
                       padding=[20, 10], borderwidth=0)
        style.map('TNotebook.Tab', background=[('selected', COLORS['accent'])],
                 foreground=[('selected', COLORS['fg'])])
        
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        # Main Configuration Tab (consolidated)
        main_frame = Frame(notebook, bg=COLORS['bg'])
        notebook.add(main_frame, text="Bot Configuration")
        self.create_main_tab(main_frame)
        
        # Settings Tab
        settings_frame = Frame(notebook, bg=COLORS['bg'])
        notebook.add(settings_frame, text="Settings")
        self.create_settings_tab(settings_frame)
        
        # Control Buttons
        self.create_control_buttons()
    
    def create_window_selection(self, parent):
        """Create window selection dropdown with modern styling"""
        window_frame = LabelFrame(parent, text="Window Selection", padx=10, pady=10,
                                 bg=COLORS['frame_bg'], fg=COLORS['fg'], 
                                 font=("Arial", 9, "bold"), relief=FLAT, bd=1)
        window_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 5))
        
        Label(window_frame, text="Select Target Window:", bg=COLORS['frame_bg'], 
             fg=COLORS['fg'], font=("Arial", 9)).pack(anchor=W, pady=(0, 5))
        
        # Frame for dropdown and refresh button
        dropdown_frame = Frame(window_frame, bg=COLORS['frame_bg'])
        dropdown_frame.pack(fill=X)
        
        # Get available windows
        try:
            available_windows = get_all_windows()
            if not available_windows:
                available_windows = ["Maplestory"]  # Fallback
        except Exception as e:
            print(f"Error getting windows: {e}")
            available_windows = ["Maplestory"]  # Fallback
        
        # Always default to "Maplestory" if it exists, otherwise add it to the list and use it
        if "Maplestory" in available_windows:
            self.selected_window.set("Maplestory")
        else:
            # Add Maplestory to the list and set it as default
            available_windows.insert(0, "Maplestory")
            self.selected_window.set("Maplestory")
        
        # Dropdown
        self.window_dropdown = ttk.Combobox(dropdown_frame, textvariable=self.selected_window, 
                                           values=available_windows, state="readonly", width=35)
        self.window_dropdown.pack(side=LEFT, padx=(0, 5))
        
        # Refresh button with modern styling
        refresh_button = Button(dropdown_frame, text="Refresh", command=self.refresh_windows, 
                               width=10, bg=COLORS['accent'], fg=COLORS['fg'],
                               activebackground=COLORS['button_hover'], 
                               activeforeground=COLORS['fg'],
                               font=("Arial", 9), relief=FLAT, cursor="hand2",
                               bd=0, highlightthickness=0, padx=8, pady=2)
        refresh_button.pack(side=LEFT)
        
        # Status label for window selection
        self.window_status = Label(window_frame, text="", fg=COLORS['success'], 
                                  bg=COLORS['frame_bg'], font=("Arial", 8))
        self.window_status.pack(anchor=W, pady=(5, 0))
        
        # Show initial status
        if available_windows:
            self.window_status.config(text=f"Found {len(available_windows)} window(s)", fg=COLORS['success'])
    
    def create_cube_type_selection(self, parent):
        """Create cube type selection section with modern styling"""
        cube_type_frame = LabelFrame(parent, text="Cube Type", padx=10, pady=10,
                                    bg=COLORS['frame_bg'], fg=COLORS['fg'],
                                    font=("Arial", 9, "bold"), relief=FLAT, bd=1)
        cube_type_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=(5, 0))
        
        self.cube_type = StringVar(value=self.config.get("cube_type", "Glowing"))
        cube_type_label = Label(cube_type_frame, text="Select Cube Type:", 
                               bg=COLORS['frame_bg'], fg=COLORS['fg'], font=("Arial", 9))
        cube_type_label.pack(anchor=W, pady=(0, 5))
        
        cube_type_glowing = Radiobutton(cube_type_frame, text="Glowing Cube", 
                                        variable=self.cube_type, value="Glowing",
                                        bg=COLORS['frame_bg'], fg=COLORS['fg'],
                                        selectcolor=COLORS['accent'], 
                                        activebackground=COLORS['frame_bg'],
                                        activeforeground=COLORS['fg'],
                                        font=("Arial", 9))
        cube_type_glowing.pack(anchor=W)
        
        cube_type_bright = Radiobutton(cube_type_frame, text="Bright Cube", 
                                      variable=self.cube_type, value="Bright",
                                      bg=COLORS['frame_bg'], fg=COLORS['fg'],
                                      selectcolor=COLORS['accent'],
                                      activebackground=COLORS['frame_bg'],
                                      activeforeground=COLORS['fg'],
                                      font=("Arial", 9))
        cube_type_bright.pack(anchor=W)
    
    def refresh_windows(self):
        """Refresh the list of available windows"""
        try:
            available_windows = get_all_windows()
            if not available_windows:
                available_windows = ["Maplestory"]
            
            # Always include "Maplestory" in the list if it's not there
            if "Maplestory" not in available_windows:
                available_windows.insert(0, "Maplestory")
            
            self.window_dropdown['values'] = available_windows
            # Default to Maplestory
            self.selected_window.set("Maplestory")
            
            self.window_status.config(text=f"Found {len(available_windows)} window(s)", fg=COLORS['success'])
        except Exception as e:
            self.window_status.config(text=f"Error refreshing windows: {str(e)}", fg=COLORS['danger'])
    
    def create_scrollable_frame(self, parent):
        """Create a scrollable frame with canvas and scrollbar"""
        # Create a frame to hold canvas and scrollbar
        container = Frame(parent, bg=COLORS['bg'])
        container.pack(fill="both", expand=True)
        
        # Create canvas and scrollbar
        canvas = Canvas(container, bg=COLORS['bg'], highlightthickness=0)
        scrollbar = Scrollbar(container, orient="vertical", command=canvas.yview,
                            bg=COLORS['frame_bg'], troughcolor=COLORS['bg'],
                            activebackground=COLORS['accent'])
        scrollable_frame = Frame(canvas, bg=COLORS['bg'])
        
        # Configure scrollable frame
        def configure_scroll_region(event=None):
            canvas.update_idletasks()
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        scrollable_frame.bind("<Configure>", configure_scroll_region)
        
        # Create window in canvas for scrollable frame
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        # Configure canvas
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Update scroll region when canvas size changes
        def configure_canvas_width(event):
            canvas_width = event.width
            canvas.itemconfig(canvas_window, width=canvas_width)
        
        canvas.bind('<Configure>', configure_canvas_width)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel to canvas and scrollable frame
        def on_mousewheel(event):
            if hasattr(event, 'delta'):
                if event.delta > 0:
                    canvas.yview_scroll(-1, "units")
                elif event.delta < 0:
                    canvas.yview_scroll(1, "units")
            elif hasattr(event, 'num'):
                if event.num == 4:
                    canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    canvas.yview_scroll(1, "units")
            return "break"
        
        def bind_mousewheel_recursive(widget):
            if isinstance(widget, Text):
                return
            widget.bind("<MouseWheel>", on_mousewheel)
            widget.bind("<Button-4>", on_mousewheel)
            widget.bind("<Button-5>", on_mousewheel)
            for child in widget.winfo_children():
                bind_mousewheel_recursive(child)
        
        bind_mousewheel_recursive(canvas)
        bind_mousewheel_recursive(scrollable_frame)
        bind_mousewheel_recursive(container)
        
        scrollable_frame._canvas = canvas
        scrollable_frame._bind_mousewheel = lambda: bind_mousewheel_recursive(scrollable_frame)
        
        return scrollable_frame
    
    def create_main_tab(self, parent):
        """Create consolidated main tab with stat threshold and roll checks"""
        scrollable_frame = self.create_scrollable_frame(parent)
        
        # Stat threshold section
        threshold_frame = LabelFrame(scrollable_frame, text="Stat Threshold Settings", 
                                    padx=10, pady=10, bg=COLORS['frame_bg'], 
                                    fg=COLORS['fg'], font=("Arial", 10, "bold"),
                                    relief=FLAT, bd=1)
        threshold_frame.pack(fill=X, padx=10, pady=5)
        
        self.stop_at_threshold = BooleanVar(value=self.config["stopAtStatThreshold"])
        threshold_check = Checkbutton(threshold_frame, text="Enable Stat Threshold Checking", 
                                     variable=self.stop_at_threshold,
                                     bg=COLORS['frame_bg'], fg=COLORS['fg'],
                                     selectcolor=COLORS['accent'],
                                     activebackground=COLORS['frame_bg'],
                                     activeforeground=COLORS['fg'],
                                     font=("Arial", 9))
        threshold_check.pack(anchor=W)
        
        threshold_label = Label(threshold_frame, text="Stat Threshold Value:", 
                               bg=COLORS['frame_bg'], fg=COLORS['fg'], font=("Arial", 9))
        threshold_label.pack(anchor=W, pady=(10, 0))
        
        self.threshold_value = IntVar(value=self.config["statThreshold"])
        threshold_entry = Entry(threshold_frame, textvariable=self.threshold_value, width=10,
                               bg=COLORS['entry_bg'], fg=COLORS['fg'],
                               insertbackground=COLORS['fg'],
                               font=("Arial", 9), relief=FLAT, bd=0, highlightthickness=1,
                               highlightbackground=COLORS['border'], highlightcolor=COLORS['accent'])
        threshold_entry.pack(anchor=W)
        
        # Stat type checkboxes
        stat_types_frame = LabelFrame(scrollable_frame, text="Stat Types to Check", 
                                     padx=10, pady=10, bg=COLORS['frame_bg'], 
                                     fg=COLORS['fg'], font=("Arial", 10, "bold"),
                                     relief=FLAT, bd=1)
        stat_types_frame.pack(fill=X, padx=10, pady=5)
        
        self.str_check = BooleanVar(value=self.config["STRcheck"])
        self.dex_check = BooleanVar(value=self.config["DEXcheck"])
        self.int_check = BooleanVar(value=self.config["INTcheck"])
        self.luk_check = BooleanVar(value=self.config["LUKcheck"])
        self.all_check = BooleanVar(value=self.config["ALLcheck"])
        self.att_check = BooleanVar(value=self.config.get("ATTcheck", False))
        self.matt_check = BooleanVar(value=self.config.get("MATTcheck", False))
        
        # Two columns for stat checkboxes
        stats_left = Frame(stat_types_frame, bg=COLORS['frame_bg'])
        stats_left.pack(side=LEFT, fill=BOTH, expand=True, padx=5)
        stats_right = Frame(stat_types_frame, bg=COLORS['frame_bg'])
        stats_right.pack(side=LEFT, fill=BOTH, expand=True, padx=5)
        
        Checkbutton(stats_left, text="STR", variable=self.str_check,
                   bg=COLORS['frame_bg'], fg=COLORS['fg'],
                   selectcolor=COLORS['accent'],
                   activebackground=COLORS['frame_bg'],
                   activeforeground=COLORS['fg'],
                   font=("Arial", 9)).pack(anchor=W)
        Checkbutton(stats_left, text="DEX", variable=self.dex_check,
                   bg=COLORS['frame_bg'], fg=COLORS['fg'],
                   selectcolor=COLORS['accent'],
                   activebackground=COLORS['frame_bg'],
                   activeforeground=COLORS['fg'],
                   font=("Arial", 9)).pack(anchor=W)
        Checkbutton(stats_left, text="INT", variable=self.int_check,
                   bg=COLORS['frame_bg'], fg=COLORS['fg'],
                   selectcolor=COLORS['accent'],
                   activebackground=COLORS['frame_bg'],
                   activeforeground=COLORS['fg'],
                   font=("Arial", 9)).pack(anchor=W)
        Checkbutton(stats_left, text="LUK", variable=self.luk_check,
                   bg=COLORS['frame_bg'], fg=COLORS['fg'],
                   selectcolor=COLORS['accent'],
                   activebackground=COLORS['frame_bg'],
                   activeforeground=COLORS['fg'],
                   font=("Arial", 9)).pack(anchor=W)
        
        Checkbutton(stats_right, text="ALL Stats", variable=self.all_check,
                   bg=COLORS['frame_bg'], fg=COLORS['fg'],
                   selectcolor=COLORS['accent'],
                   activebackground=COLORS['frame_bg'],
                   activeforeground=COLORS['fg'],
                   font=("Arial", 9)).pack(anchor=W)
        Checkbutton(stats_right, text="Attack Power (ATT)", variable=self.att_check,
                   bg=COLORS['frame_bg'], fg=COLORS['fg'],
                   selectcolor=COLORS['accent'],
                   activebackground=COLORS['frame_bg'],
                   activeforeground=COLORS['fg'],
                   font=("Arial", 9)).pack(anchor=W)
        Checkbutton(stats_right, text="Magic ATT (MATT)", variable=self.matt_check,
                   bg=COLORS['frame_bg'], fg=COLORS['fg'],
                   selectcolor=COLORS['accent'],
                   activebackground=COLORS['frame_bg'],
                   activeforeground=COLORS['fg'],
                   font=("Arial", 9)).pack(anchor=W)
        
        # Flexible Roll Check section
        flex_frame = LabelFrame(scrollable_frame, text="Flexible Roll Check", 
                               padx=10, pady=10, bg=COLORS['frame_bg'], 
                               fg=COLORS['fg'], font=("Arial", 10, "bold"),
                               relief=FLAT, bd=1)
        flex_frame.pack(fill=X, padx=10, pady=5)
        
        # Enable checkbox
        flex_config = self.config.get("flexible_roll_check", {"enabled": False, "stat_types": [], "required_count": 2})
        self.flex_check_enabled = BooleanVar(value=flex_config.get("enabled", False))
        Checkbutton(flex_frame, text="Enable Flexible Roll Check", variable=self.flex_check_enabled,
                   bg=COLORS['frame_bg'], fg=COLORS['fg'],
                   selectcolor=COLORS['accent'],
                   activebackground=COLORS['frame_bg'],
                   activeforeground=COLORS['fg'],
                   font=("Arial", 10, "bold")).pack(anchor=W, pady=(0, 10))
        
        # Stat type checkboxes
        stat_types_frame_flex = LabelFrame(flex_frame, text="Select Stat Types", 
                                          padx=10, pady=10, bg=COLORS['frame_bg'], 
                                          fg=COLORS['fg'], font=("Arial", 9),
                                          relief=FLAT, bd=1)
        stat_types_frame_flex.pack(fill=X, padx=5, pady=5)
        
        self.flex_stat_bd = BooleanVar(value="BD" in flex_config.get("stat_types", []))
        self.flex_stat_att = BooleanVar(value="ATT" in flex_config.get("stat_types", []))
        self.flex_stat_matt = BooleanVar(value="MATT" in flex_config.get("stat_types", []))
        self.flex_stat_ied = BooleanVar(value="IED" in flex_config.get("stat_types", []))
        self.flex_stat_cd = BooleanVar(value="CD" in flex_config.get("stat_types", []))
        self.flex_stat_ia = BooleanVar(value="IA" in flex_config.get("stat_types", []))
        self.flex_stat_meso = BooleanVar(value="MESO" in flex_config.get("stat_types", []))
        self.flex_stat_sc = BooleanVar(value="SC" in flex_config.get("stat_types", []))
        
        # Two columns for stat checkboxes
        stats_left_flex = Frame(stat_types_frame_flex, bg=COLORS['frame_bg'])
        stats_left_flex.pack(side=LEFT, fill=BOTH, expand=True, padx=5)
        stats_right_flex = Frame(stat_types_frame_flex, bg=COLORS['frame_bg'])
        stats_right_flex.pack(side=LEFT, fill=BOTH, expand=True, padx=5)
        
        Checkbutton(stats_left_flex, text="Boss Damage (BD)", variable=self.flex_stat_bd,
                   bg=COLORS['frame_bg'], fg=COLORS['fg'],
                   selectcolor=COLORS['accent'],
                   activebackground=COLORS['frame_bg'],
                   activeforeground=COLORS['fg'],
                   font=("Arial", 9)).pack(anchor=W)
        Checkbutton(stats_left_flex, text="Attack Power (ATT)", variable=self.flex_stat_att,
                   bg=COLORS['frame_bg'], fg=COLORS['fg'],
                   selectcolor=COLORS['accent'],
                   activebackground=COLORS['frame_bg'],
                   activeforeground=COLORS['fg'],
                   font=("Arial", 9)).pack(anchor=W)
        Checkbutton(stats_left_flex, text="Magic ATT (MATT)", variable=self.flex_stat_matt,
                   bg=COLORS['frame_bg'], fg=COLORS['fg'],
                   selectcolor=COLORS['accent'],
                   activebackground=COLORS['frame_bg'],
                   activeforeground=COLORS['fg'],
                   font=("Arial", 9)).pack(anchor=W)
        Checkbutton(stats_left_flex, text="Ignore Defense (IED)", variable=self.flex_stat_ied,
                   bg=COLORS['frame_bg'], fg=COLORS['fg'],
                   selectcolor=COLORS['accent'],
                   activebackground=COLORS['frame_bg'],
                   activeforeground=COLORS['fg'],
                   font=("Arial", 9)).pack(anchor=W)
        
        Checkbutton(stats_right_flex, text="Critical Damage (CD)", variable=self.flex_stat_cd,
                   bg=COLORS['frame_bg'], fg=COLORS['fg'],
                   selectcolor=COLORS['accent'],
                   activebackground=COLORS['frame_bg'],
                   activeforeground=COLORS['fg'],
                   font=("Arial", 9)).pack(anchor=W)
        Checkbutton(stats_right_flex, text="Item Drop Rate (IA)", variable=self.flex_stat_ia,
                   bg=COLORS['frame_bg'], fg=COLORS['fg'],
                   selectcolor=COLORS['accent'],
                   activebackground=COLORS['frame_bg'],
                   activeforeground=COLORS['fg'],
                   font=("Arial", 9)).pack(anchor=W)
        Checkbutton(stats_right_flex, text="Meso Obtained (MESO)", variable=self.flex_stat_meso,
                   bg=COLORS['frame_bg'], fg=COLORS['fg'],
                   selectcolor=COLORS['accent'],
                   activebackground=COLORS['frame_bg'],
                   activeforeground=COLORS['fg'],
                   font=("Arial", 9)).pack(anchor=W)
        Checkbutton(stats_right_flex, text="Skill Cooldowns -1/-2 sec (SC)", variable=self.flex_stat_sc,
                   bg=COLORS['frame_bg'], fg=COLORS['fg'],
                   selectcolor=COLORS['accent'],
                   activebackground=COLORS['frame_bg'],
                   activeforeground=COLORS['fg'],
                   font=("Arial", 9)).pack(anchor=W)
        
        # Required count selector
        count_frame = LabelFrame(flex_frame, text="Required Matching Lines", 
                               padx=10, pady=10, bg=COLORS['frame_bg'], 
                               fg=COLORS['fg'], font=("Arial", 9),
                               relief=FLAT, bd=1)
        count_frame.pack(fill=X, padx=5, pady=5)
        
        Label(count_frame, text="Stop when this many lines match:", 
             bg=COLORS['frame_bg'], fg=COLORS['fg'], font=("Arial", 9)).pack(anchor=W, pady=(0, 5))
        self.flex_required_count = StringVar(value=str(flex_config.get("required_count", 2)))
        count_dropdown = ttk.Combobox(count_frame, textvariable=self.flex_required_count, 
                                     values=["1", "2", "3"], state="readonly", width=5)
        count_dropdown.pack(anchor=W)
        
        # Info label
        info_label = Label(flex_frame, text="Example: Select MATT + BD, count=3 → stops if 3 lines match MATT or BD", 
                          font=("Arial", 8), fg=COLORS['warning'], bg=COLORS['frame_bg'], wraplength=500)
        info_label.pack(anchor=W, padx=5, pady=5)
        
        # Re-bind mousewheel after all widgets are added
        if hasattr(scrollable_frame, '_bind_mousewheel'):
            scrollable_frame._bind_mousewheel()
    
    def create_settings_tab(self, parent):
        """Create settings tab with OCR Results and hotkey configuration"""
        scrollable_frame = self.create_scrollable_frame(parent)
        
        # OCR Results Display
        ocr_frame = LabelFrame(scrollable_frame, text="OCR Results", padx=10, pady=10,
                              bg=COLORS['frame_bg'], fg=COLORS['fg'], 
                              font=("Arial", 10, "bold"), relief=FLAT, bd=1)
        ocr_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)
        
        # Text widget with scrollbar for OCR results
        ocr_text_frame = Frame(ocr_frame, bg=COLORS['frame_bg'])
        ocr_text_frame.pack(fill=BOTH, expand=True)
        
        self.ocr_results_text = Text(ocr_text_frame, height=12, wrap=WORD, state=DISABLED, 
                                    font=("Courier", 9), bg=COLORS['entry_bg'], 
                                    fg=COLORS['fg'], insertbackground=COLORS['fg'],
                                    relief=FLAT, bd=0, highlightthickness=1,
                                    highlightbackground=COLORS['border'])
        ocr_scrollbar = Scrollbar(ocr_text_frame, orient=VERTICAL, 
                                 command=self.ocr_results_text.yview,
                                 bg=COLORS['frame_bg'], troughcolor=COLORS['bg'],
                                 activebackground=COLORS['accent'])
        self.ocr_results_text.config(yscrollcommand=ocr_scrollbar.set)
        
        self.ocr_results_text.pack(side=LEFT, fill=BOTH, expand=True)
        ocr_scrollbar.pack(side=RIGHT, fill=Y)
        
        # Clear button for OCR results
        clear_button = Button(ocr_frame, text="Clear Results", command=self.clear_ocr_results,
                            bg=COLORS['accent'], fg=COLORS['fg'],
                            activebackground=COLORS['button_hover'],
                            activeforeground=COLORS['fg'],
                            font=("Arial", 9), relief=FLAT, cursor="hand2",
                            bd=0, highlightthickness=0, padx=10, pady=3)
        clear_button.pack(pady=(5, 0))
        
        # Hotkey Configuration
        hotkey_frame = LabelFrame(scrollable_frame, text="Hotkey Configuration", 
                                 padx=10, pady=10, bg=COLORS['frame_bg'], 
                                 fg=COLORS['fg'], font=("Arial", 10, "bold"),
                                 relief=FLAT, bd=1)
        hotkey_frame.pack(fill=X, padx=10, pady=5)
        
        # Start bot hotkey
        start_hotkey_frame = Frame(hotkey_frame, bg=COLORS['frame_bg'])
        start_hotkey_frame.pack(fill=X, pady=5)
        
        Label(start_hotkey_frame, text="Start Bot Hotkey:", bg=COLORS['frame_bg'], 
             fg=COLORS['fg'], font=("Arial", 9), width=20).pack(side=LEFT)
        
        # Use HotkeyCaptureEntry for click-to-capture
        self.start_hotkey_capture = HotkeyCaptureEntry(start_hotkey_frame, self.start_hotkey, width=15)
        self.start_hotkey_capture.update_callback = self.update_hotkeys
        self.start_hotkey_capture.pack(side=LEFT, padx=5)
        
        Label(start_hotkey_frame, text="(Click to capture)", bg=COLORS['frame_bg'], 
             fg=COLORS['warning'], font=("Arial", 8)).pack(side=LEFT, padx=5)
        
        # Stop bot hotkey
        stop_hotkey_frame = Frame(hotkey_frame, bg=COLORS['frame_bg'])
        stop_hotkey_frame.pack(fill=X, pady=5)
        
        Label(stop_hotkey_frame, text="Stop Bot Hotkey:", bg=COLORS['frame_bg'], 
             fg=COLORS['fg'], font=("Arial", 9), width=20).pack(side=LEFT)
        
        # Use HotkeyCaptureEntry for click-to-capture
        self.stop_hotkey_capture = HotkeyCaptureEntry(stop_hotkey_frame, self.stop_hotkey, width=15)
        self.stop_hotkey_capture.update_callback = self.update_hotkeys
        self.stop_hotkey_capture.pack(side=LEFT, padx=5)
        
        Label(stop_hotkey_frame, text="(Click to capture)", bg=COLORS['frame_bg'], 
             fg=COLORS['warning'], font=("Arial", 8)).pack(side=LEFT, padx=5)
        
        # Info label
        hotkey_info = Label(hotkey_frame, 
                           text="Note: Click on the hotkey field, then press your desired key combination. Hotkeys work globally.",
                           font=("Arial", 8), fg=COLORS['warning'], bg=COLORS['frame_bg'], 
                           wraplength=500)
        hotkey_info.pack(anchor=W, padx=5, pady=(5, 0))
        
        # Re-bind mousewheel after all widgets are added
        if hasattr(scrollable_frame, '_bind_mousewheel'):
            scrollable_frame._bind_mousewheel()
    
    def create_control_buttons(self):
        """Create control buttons with modern styling"""
        button_frame = Frame(self.root, bg=COLORS['bg'])
        button_frame.pack(pady=10)
        
        self.start_button = Button(button_frame, text="Start Bot", command=self.start_bot, 
                                  bg=COLORS['success'], fg=COLORS['fg'], 
                                  font=("Arial", 12, "bold"), width=15,
                                  activebackground='#00a043',
                                  activeforeground=COLORS['fg'],
                                  relief=FLAT, cursor="hand2", padx=10, pady=5,
                                  bd=0, highlightthickness=0)
        self.start_button.pack(side=LEFT, padx=5)
        
        self.stop_button = Button(button_frame, text="Stop Bot", command=self.stop_bot, 
                                 bg=COLORS['danger'], fg=COLORS['fg'], 
                                 font=("Arial", 12, "bold"), width=15, state=DISABLED,
                                 activebackground='#b71c1c',
                                 activeforeground=COLORS['fg'],
                                 relief=FLAT, cursor="hand2", padx=10, pady=5,
                                 bd=0, highlightthickness=0)
        self.stop_button.pack(side=LEFT, padx=5)
        
        # Status label
        self.status_label = Label(self.root, text="Status: Ready", fg=COLORS['success'], 
                                 bg=COLORS['bg'], font=("Arial", 10, "bold"))
        self.status_label.pack(pady=5)
    
    def update_ocr_results(self, text):
        """Update the OCR results display with new text"""
        self.root.after(0, lambda: self._update_ocr_text(text))
    
    def _update_ocr_text(self, text):
        """Internal method to update OCR text widget (must be called from main thread)"""
        self.ocr_results_text.config(state=NORMAL)
        self.ocr_results_text.insert(END, text + "\n")
        self.ocr_results_text.see(END)  # Auto-scroll to bottom
        self.ocr_results_text.config(state=DISABLED)
    
    def clear_ocr_results(self):
        """Clear the OCR results display"""
        self.root.after(0, lambda: self.ocr_results_text.config(state=NORMAL) or self.ocr_results_text.delete(1.0, END) or self.ocr_results_text.config(state=DISABLED))
        
    def build_config(self):
        """Build configuration dictionary from GUI values"""
        config = {}
        
        # Window name - default to "Maplestory" if empty
        window_name = self.selected_window.get()
        config["window_name"] = window_name if window_name else "Maplestory"
        
        # Cube type
        config["cube_type"] = self.cube_type.get()
        
        # Auto-detect crop is always enabled
        config["auto_detect_crop"] = True
        config["crop_region"] = None  # Will be set automatically
        config["test_image_path"] = None  # Always use live window capture
        
        # Stat threshold settings
        config["stopAtStatThreshold"] = self.stop_at_threshold.get()
        config["statThreshold"] = self.threshold_value.get()
        
        # Stat type checks
        config["STRcheck"] = self.str_check.get()
        config["DEXcheck"] = self.dex_check.get()
        config["INTcheck"] = self.int_check.get()
        config["LUKcheck"] = self.luk_check.get()
        config["ALLcheck"] = self.all_check.get()
        config["ATTcheck"] = self.att_check.get()
        config["MATTcheck"] = self.matt_check.get()
        
        # Flexible roll check (new system)
        flex_stat_types = []
        if self.flex_stat_bd.get():
            flex_stat_types.append("BD")
        if self.flex_stat_att.get():
            flex_stat_types.append("ATT")
        if self.flex_stat_matt.get():
            flex_stat_types.append("MATT")
        if self.flex_stat_ied.get():
            flex_stat_types.append("IED")
        if self.flex_stat_cd.get():
            flex_stat_types.append("CD")
        if self.flex_stat_ia.get():
            flex_stat_types.append("IA")
        if self.flex_stat_meso.get():
            flex_stat_types.append("MESO")
        if self.flex_stat_sc.get():
            flex_stat_types.append("SC")
        
        config["flexible_roll_check"] = {
            "enabled": self.flex_check_enabled.get(),
            "stat_types": flex_stat_types,
            "required_count": int(self.flex_required_count.get())
        }
        
        return config
        
    def start_bot(self):
        if self.bot_running:
            return
            
        self.config = self.build_config()
        self.bot_running = True
        self.start_button.config(state=DISABLED)
        self.stop_button.config(state=NORMAL)
        self.status_label.config(text=f"Status: Running (Hotkey: {self.start_hotkey.get()})", fg=COLORS['warning'])
        
        # Run bot in separate thread
        bot_thread = threading.Thread(target=self.run_bot_thread, daemon=True)
        bot_thread.start()
        
    def run_bot_thread(self):
        try:
            # Pass OCR callback to bot config
            self.config["ocr_callback"] = self.update_ocr_results
            run_bot(self.config)
        except Exception as e:
            self.update_ocr_results(f"Bot error: {str(e)}")
        finally:
            # Save debug image and clear cache when bot stops
            try:
                from src.translate_ocr_results import get_potlines, clear_potlines_cache
                potlines_instance = get_potlines()
                if potlines_instance:
                    potlines_instance.save_debug_image()
                    potlines_instance.clear_cache()
                # Clear the global cache
                clear_potlines_cache()
            except Exception as e:
                print(f"Could not save debug image or clear cache: {e}")
            self.bot_running = False
            self.root.after(0, self.bot_stopped)
            
    def bot_stopped(self):
        self.start_button.config(state=NORMAL)
        self.stop_button.config(state=DISABLED)
        self.status_label.config(text="Status: Stopped", fg=COLORS['danger'])
        
    def stop_bot(self):
        # Immediately signal the bot to stop
        bot_stop_event.set()
        self.status_label.config(text="Status: Stopping...", fg=COLORS['warning'])
        print("Stop button clicked - bot will stop immediately")

if __name__ == "__main__":
    root = Tk()
    app = BotGUI(root)
    root.mainloop()
