from tkinter import *
from tkinter import ttk
from tkinter import filedialog
import threading
import win32gui
import hashlib
import secrets
import tesseract_config  # Configure Tesseract before importing bot_logic
from bot_logic import run_bot, default_config, bot_stop_event

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

class BotGUI:
    def __init__(self, root):
        self.root = root
        # Generate a random hash code for window title to avoid detection
        random_bytes = secrets.token_bytes(16)
        hash_code = hashlib.sha256(random_bytes).hexdigest()[:12].upper()
        self.root.title(f"{hash_code}")
        self.root.geometry('600x750')
        
        # Configuration variables
        self.config = default_config.copy()
        self.bot_running = False
        self.selected_window = StringVar(value="Maplestory")
        
        self.create_widgets()
        
    def create_widgets(self):
        # Container frame for Window Selection and Cube Type (same row)
        top_frame = Frame(self.root)
        top_frame.pack(fill=X, padx=10, pady=5)
        
        # Window Selection and Cube Type Section (before tabs)
        self.create_window_selection(top_frame)
        self.create_cube_type_selection(top_frame)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        # Stat Threshold Tab
        stat_frame = Frame(notebook)
        notebook.add(stat_frame, text="Stat Threshold")
        self.create_stat_tab(stat_frame)
        
        # Roll Checks Tab
        roll_frame = Frame(notebook)
        notebook.add(roll_frame, text="Roll Checks")
        self.create_roll_tab(roll_frame)
        
        # Control Buttons
        self.create_control_buttons()
    
    def create_window_selection(self, parent):
        """Create window selection dropdown"""
        window_frame = LabelFrame(parent, text="Window Selection", padx=10, pady=10)
        window_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 5))
        
        Label(window_frame, text="Select Target Window:").pack(anchor=W, pady=(0, 5))
        
        # Frame for dropdown and refresh button
        dropdown_frame = Frame(window_frame)
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
                                           values=available_windows, state="readonly", width=40)
        self.window_dropdown.pack(side=LEFT, padx=(0, 5))
        
        # Refresh button
        refresh_button = Button(dropdown_frame, text="Refresh", command=self.refresh_windows, width=10)
        refresh_button.pack(side=LEFT)
        
        # Status label for window selection
        self.window_status = Label(window_frame, text="", fg="gray", font=("Arial", 8))
        self.window_status.pack(anchor=W, pady=(5, 0))
        
        # Show initial status
        if available_windows:
            self.window_status.config(text=f"Found {len(available_windows)} window(s)", fg="green")
    
    def create_cube_type_selection(self, parent):
        """Create cube type selection section"""
        cube_type_frame = LabelFrame(parent, text="Cube Type", padx=10, pady=10)
        cube_type_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=(5, 0))
        
        self.cube_type = StringVar(value=self.config.get("cube_type", "Glowing"))
        cube_type_label = Label(cube_type_frame, text="Select Cube Type:")
        cube_type_label.pack(anchor=W, pady=(0, 5))
        
        cube_type_glowing = Radiobutton(cube_type_frame, text="Glowing Cube", variable=self.cube_type, value="Glowing")
        cube_type_glowing.pack(anchor=W)
        
        cube_type_bright = Radiobutton(cube_type_frame, text="Bright Cube", variable=self.cube_type, value="Bright")
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
            
            self.window_status.config(text=f"Found {len(available_windows)} window(s)", fg="green")
        except Exception as e:
            self.window_status.config(text=f"Error refreshing windows: {str(e)}", fg="red")
        
    def create_scrollable_frame(self, parent):
        """Create a scrollable frame with canvas and scrollbar"""
        # Create a frame to hold canvas and scrollbar
        container = Frame(parent)
        container.pack(fill="both", expand=True)
        
        # Create canvas and scrollbar
        canvas = Canvas(container)
        scrollbar = Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = Frame(canvas)
        
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
            # Check if event is from canvas area or its children
            # Windows/Mac: event.delta is positive (scroll up) or negative (scroll down)
            # Linux: event.num is 4 (scroll up) or 5 (scroll down)
            if hasattr(event, 'delta'):
                # Windows/Mac
                if event.delta > 0:
                    canvas.yview_scroll(-1, "units")
                elif event.delta < 0:
                    canvas.yview_scroll(1, "units")
            elif hasattr(event, 'num'):
                # Linux
                if event.num == 4:
                    canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    canvas.yview_scroll(1, "units")
            return "break"  # Prevent event propagation
        
        def bind_mousewheel_recursive(widget):
            """Recursively bind mousewheel to widget and all its children"""
            # Skip Text widgets - they handle their own scrolling
            if isinstance(widget, Text):
                return
            
            # Windows/Mac
            widget.bind("<MouseWheel>", on_mousewheel)
            # Linux
            widget.bind("<Button-4>", on_mousewheel)
            widget.bind("<Button-5>", on_mousewheel)
            
            # Bind to all current children
            for child in widget.winfo_children():
                bind_mousewheel_recursive(child)
        
        # Bind to canvas (covers entire scrollable area)
        bind_mousewheel_recursive(canvas)
        
        # Bind to scrollable frame and all its children
        bind_mousewheel_recursive(scrollable_frame)
        
        # Also bind to container
        bind_mousewheel_recursive(container)
        
        # Store canvas reference for later binding when new widgets are added
        scrollable_frame._canvas = canvas
        scrollable_frame._bind_mousewheel = lambda: bind_mousewheel_recursive(scrollable_frame)
        
        return scrollable_frame
    
    def create_stat_tab(self, parent):
        # Create scrollable frame
        scrollable_frame = self.create_scrollable_frame(parent)
        
        # OCR Results Display
        ocr_frame = LabelFrame(scrollable_frame, text="OCR Results", padx=10, pady=10)
        ocr_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)
        
        # Text widget with scrollbar for OCR results
        ocr_text_frame = Frame(ocr_frame)
        ocr_text_frame.pack(fill=BOTH, expand=True)
        
        self.ocr_results_text = Text(ocr_text_frame, height=8, wrap=WORD, state=DISABLED, font=("Courier", 9))
        ocr_scrollbar = Scrollbar(ocr_text_frame, orient=VERTICAL, command=self.ocr_results_text.yview)
        self.ocr_results_text.config(yscrollcommand=ocr_scrollbar.set)
        
        self.ocr_results_text.pack(side=LEFT, fill=BOTH, expand=True)
        ocr_scrollbar.pack(side=RIGHT, fill=Y)
        
        # Stat threshold section
        threshold_frame = LabelFrame(scrollable_frame, text="Stat Threshold Settings", padx=10, pady=10)
        threshold_frame.pack(fill=X, padx=10, pady=5)
        
        self.stop_at_threshold = BooleanVar(value=self.config["stopAtStatThreshold"])
        threshold_check = Checkbutton(threshold_frame, text="Enable Stat Threshold Checking", 
                                     variable=self.stop_at_threshold)
        threshold_check.pack(anchor=W)
        
        threshold_label = Label(threshold_frame, text="Stat Threshold Value:")
        threshold_label.pack(anchor=W, pady=(10, 0))
        
        self.threshold_value = IntVar(value=self.config["statThreshold"])
        threshold_entry = Entry(threshold_frame, textvariable=self.threshold_value, width=10)
        threshold_entry.pack(anchor=W)
        
        # Stat type checkboxes
        stat_types_frame = LabelFrame(scrollable_frame, text="Stat Types to Check", padx=10, pady=10)
        stat_types_frame.pack(fill=X, padx=10, pady=5)
        
        self.str_check = BooleanVar(value=self.config["STRcheck"])
        self.dex_check = BooleanVar(value=self.config["DEXcheck"])
        self.int_check = BooleanVar(value=self.config["INTcheck"])
        self.luk_check = BooleanVar(value=self.config["LUKcheck"])
        self.all_check = BooleanVar(value=self.config["ALLcheck"])
        
        Checkbutton(stat_types_frame, text="STR", variable=self.str_check).pack(anchor=W)
        Checkbutton(stat_types_frame, text="DEX", variable=self.dex_check).pack(anchor=W)
        Checkbutton(stat_types_frame, text="INT", variable=self.int_check).pack(anchor=W)
        Checkbutton(stat_types_frame, text="LUK", variable=self.luk_check).pack(anchor=W)
        Checkbutton(stat_types_frame, text="ALL Stats", variable=self.all_check).pack(anchor=W)
        
        # Re-bind mousewheel after all widgets are added to ensure scrolling works everywhere
        if hasattr(scrollable_frame, '_bind_mousewheel'):
            scrollable_frame._bind_mousewheel()
    
    def create_roll_tab(self, parent):
        # Create scrollable frame
        scrollable_frame = self.create_scrollable_frame(parent)
        
        # Flexible Roll Check (new system)
        flex_frame = LabelFrame(scrollable_frame, text="Flexible Roll Check", padx=10, pady=10)
        flex_frame.pack(fill=X, padx=10, pady=5)
        
        # Enable checkbox
        flex_config = self.config.get("flexible_roll_check", {"enabled": False, "stat_types": [], "required_count": 2})
        self.flex_check_enabled = BooleanVar(value=flex_config.get("enabled", False))
        Checkbutton(flex_frame, text="Enable Flexible Roll Check", variable=self.flex_check_enabled, 
                   font=("Arial", 10, "bold")).pack(anchor=W, pady=(0, 10))
        
        # Stat type checkboxes
        stat_types_frame = LabelFrame(flex_frame, text="Select Stat Types", padx=10, pady=10)
        stat_types_frame.pack(fill=X, padx=5, pady=5)
        
        self.flex_stat_bd = BooleanVar(value="BD" in flex_config.get("stat_types", []))
        self.flex_stat_att = BooleanVar(value="ATT" in flex_config.get("stat_types", []))
        self.flex_stat_matt = BooleanVar(value="MATT" in flex_config.get("stat_types", []))
        self.flex_stat_ied = BooleanVar(value="IED" in flex_config.get("stat_types", []))
        self.flex_stat_cd = BooleanVar(value="CD" in flex_config.get("stat_types", []))
        self.flex_stat_ia = BooleanVar(value="IA" in flex_config.get("stat_types", []))
        self.flex_stat_meso = BooleanVar(value="MESO" in flex_config.get("stat_types", []))
        
        # Two columns for stat checkboxes
        stats_left = Frame(stat_types_frame)
        stats_left.pack(side=LEFT, fill=BOTH, expand=True, padx=5)
        stats_right = Frame(stat_types_frame)
        stats_right.pack(side=LEFT, fill=BOTH, expand=True, padx=5)
        
        Checkbutton(stats_left, text="Boss Damage (BD)", variable=self.flex_stat_bd).pack(anchor=W)
        Checkbutton(stats_left, text="Attack Power (ATT)", variable=self.flex_stat_att).pack(anchor=W)
        Checkbutton(stats_left, text="Magic ATT (MATT)", variable=self.flex_stat_matt).pack(anchor=W)
        Checkbutton(stats_left, text="Ignore Defense (IED)", variable=self.flex_stat_ied).pack(anchor=W)
        
        Checkbutton(stats_right, text="Critical Damage (CD)", variable=self.flex_stat_cd).pack(anchor=W)
        Checkbutton(stats_right, text="Item Drop Rate (IA)", variable=self.flex_stat_ia).pack(anchor=W)
        Checkbutton(stats_right, text="Meso Obtained (MESO)", variable=self.flex_stat_meso).pack(anchor=W)
        
        # Required count selector
        count_frame = LabelFrame(flex_frame, text="Required Matching Lines", padx=10, pady=10)
        count_frame.pack(fill=X, padx=5, pady=5)
        
        Label(count_frame, text="Stop when this many lines match:").pack(anchor=W, pady=(0, 5))
        self.flex_required_count = StringVar(value=str(flex_config.get("required_count", 2)))
        count_dropdown = ttk.Combobox(count_frame, textvariable=self.flex_required_count, 
                                     values=["1", "2", "3"], state="readonly", width=5)
        count_dropdown.pack(anchor=W)
        
        # Info label
        info_label = Label(flex_frame, text="Example: Select MATT + BD, count=3 → stops if 3 lines match MATT or BD", 
                          font=("Arial", 8), fg="gray", wraplength=500)
        info_label.pack(anchor=W, padx=5, pady=5)
        
    def create_control_buttons(self):
        button_frame = Frame(self.root)
        button_frame.pack(pady=10)
        
        self.start_button = Button(button_frame, text="Start Bot", command=self.start_bot, 
                                  bg="green", fg="white", font=("Arial", 12, "bold"), width=15)
        self.start_button.pack(side=LEFT, padx=5)
        
        self.stop_button = Button(button_frame, text="Stop Bot", command=self.stop_bot, 
                                 bg="red", fg="white", font=("Arial", 12, "bold"), width=15, state=DISABLED)
        self.stop_button.pack(side=LEFT, padx=5)
        
        # Status label
        self.status_label = Label(self.root, text="Status: Ready", fg="green", font=("Arial", 10))
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
        self.status_label.config(text="Status: Running (Press 'q' to stop)", fg="orange")
        
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
                from translate_ocr_results import get_potlines, clear_potlines_cache
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
        self.status_label.config(text="Status: Stopped", fg="red")
        
    def stop_bot(self):
        # Immediately signal the bot to stop
        bot_stop_event.set()
        self.status_label.config(text="Status: Stopping...", fg="orange")
        print("Stop button clicked - bot will stop immediately")

if __name__ == "__main__":
    root = Tk()
    app = BotGUI(root)
    root.mainloop()
