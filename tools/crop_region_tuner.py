"""
Interactive GUI tool to tune crop region offsets in real-time
"""
import cv2 as cv
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import threading
from src.auto_detect_crop import detect_potential_region

# Try to import config, if it fails we'll use defaults
try:
    from src.crop_config import (
        OFFSET_X,
        OFFSET_ABOVE,
        STAT_WIDTH,
        STAT_HEIGHT,
        BRIGHT_OFFSET_X,
        BRIGHT_OFFSET_ABOVE,
        BRIGHT_STAT_WIDTH,
        BRIGHT_STAT_HEIGHT,
    )
except ImportError:
    OFFSET_X = 200
    OFFSET_ABOVE = 200
    STAT_WIDTH = 350
    STAT_HEIGHT = 95
    BRIGHT_OFFSET_X = 107
    BRIGHT_OFFSET_ABOVE = 232
    BRIGHT_STAT_WIDTH = 212
    BRIGHT_STAT_HEIGHT = 108


class CropRegionTuner:
    def __init__(self, root):
        self.root = root
        self.root.title("Crop Region Tuner")
        self.root.geometry("1200x800")
        
        # Image data
        self.original_image = None
        self.display_image = None
        self.reset_x = None
        self.reset_y = None
        self.reset_w = None
        self.reset_h = None
        self.image_path = None
        self.cube_type = tk.StringVar(value="Glowing")
        
        # Current config values
        self.offset_x = tk.IntVar(value=OFFSET_X)
        self.offset_above = tk.IntVar(value=OFFSET_ABOVE)
        self.stat_width = tk.IntVar(value=STAT_WIDTH)
        self.stat_height = tk.IntVar(value=STAT_HEIGHT)
        
        # Create UI
        self.create_ui()
        
        # Load image button
        load_btn = tk.Button(self.root, text="Load Image", command=self.load_image, font=("Arial", 12))
        load_btn.pack(pady=10)
        
    def create_ui(self):
        # Main container
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Image display
        left_frame = tk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        image_label = tk.Label(left_frame, text="Load an image to begin", font=("Arial", 14))
        image_label.pack(fill=tk.BOTH, expand=True)
        self.image_label = image_label
        
        # Right panel - Controls
        right_frame = tk.Frame(main_frame, width=300)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right_frame.pack_propagate(False)
        
        # Title
        title_label = tk.Label(right_frame, text="Crop Region Settings", font=("Arial", 14, "bold"))
        title_label.pack(pady=10)

        # Cube type selector
        cube_frame = tk.Frame(right_frame)
        cube_frame.pack(pady=(0, 10), fill=tk.X)
        tk.Label(cube_frame, text="Cube Type", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        cube_menu = tk.OptionMenu(cube_frame, self.cube_type, "Glowing", "Bright", command=self.on_cube_type_changed)
        cube_menu.config(width=20)
        cube_menu.pack(anchor=tk.W, pady=(4, 0))
        
        # Sliders
        self.create_slider(right_frame, "Offset X", self.offset_x, -500, 500, 
                          "X offset from Reset button\n(negative = left, positive = right)")
        self.create_slider(right_frame, "Offset Above", self.offset_above, 0, 800,
                          "Pixels above Reset button")
        self.create_slider(right_frame, "Stat Width", self.stat_width, 100, 800,
                          "Width of crop region")
        self.create_slider(right_frame, "Stat Height", self.stat_height, 50, 500,
                          "Fixed height of crop region")
        
        # Buttons
        button_frame = tk.Frame(right_frame)
        button_frame.pack(pady=20)
        
        save_btn = tk.Button(button_frame, text="Save to Config", command=self.save_config,
                            font=("Arial", 11), bg="#4CAF50", fg="white", width=20)
        save_btn.pack(pady=5)
        
        detect_btn = tk.Button(button_frame, text="Detect Reset Button", command=self.detect_reset,
                              font=("Arial", 11), bg="#2196F3", fg="white", width=20)
        detect_btn.pack(pady=5)
        
        # Info label
        self.info_label = tk.Label(right_frame, text="", font=("Arial", 9), 
                                   wraplength=280, justify=tk.LEFT, fg="gray")
        self.info_label.pack(pady=10, padx=5)

    def on_cube_type_changed(self, *_):
        """Load defaults for the selected cube type and refresh preview."""
        if self.cube_type.get() == "Bright":
            self.offset_x.set(BRIGHT_OFFSET_X)
            self.offset_above.set(BRIGHT_OFFSET_ABOVE)
            self.stat_width.set(BRIGHT_STAT_WIDTH)
            self.stat_height.set(BRIGHT_STAT_HEIGHT)
        else:
            self.offset_x.set(OFFSET_X)
            self.offset_above.set(OFFSET_ABOVE)
            self.stat_width.set(STAT_WIDTH)
            self.stat_height.set(STAT_HEIGHT)
        if self.original_image is not None:
            self.detect_reset()
        
    def create_slider(self, parent, label, variable, min_val, max_val, tooltip):
        frame = tk.Frame(parent)
        frame.pack(pady=10, fill=tk.X)
        
        label_widget = tk.Label(frame, text=label, font=("Arial", 10, "bold"))
        label_widget.pack(anchor=tk.W)
        
        value_label = tk.Label(frame, textvariable=variable, font=("Arial", 9))
        value_label.pack(anchor=tk.W)
        
        slider = tk.Scale(frame, from_=min_val, to=max_val, orient=tk.HORIZONTAL,
                         variable=variable, command=lambda v: self.update_preview(),
                         length=250, resolution=1)
        slider.pack(fill=tk.X)
        
        tooltip_label = tk.Label(frame, text=tooltip, font=("Arial", 8), 
                                fg="gray", wraplength=250, justify=tk.LEFT)
        tooltip_label.pack(anchor=tk.W, pady=(2, 0))
        
    def load_image(self):
        file_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp"), ("All files", "*.*")]
        )
        if file_path:
            self.image_path = file_path
            self.original_image = cv.imread(file_path)
            if self.original_image is None:
                messagebox.showerror("Error", "Could not load image")
                return
            
            # Auto-detect Reset button
            self.detect_reset()
            
    def detect_reset(self):
        if self.original_image is None:
            messagebox.showwarning("Warning", "Please load an image first")
            return
        
        # Show detecting message
        self.info_label.config(text="Detecting Reset button...", fg="blue")
        self.root.update()
        
        # Run detection in a thread to avoid freezing UI
        def detect_thread():
            try:
                result = detect_potential_region(
                    self.original_image.copy(),
                    debug=False,
                    cube_type=self.cube_type.get(),
                )

                if result and result[1] is not None:
                    _, reset_pos = result
                    self.reset_x, self.reset_y, self.reset_w, self.reset_h = reset_pos
                    self.root.after(0, lambda: self.info_label.config(
                        text=f"{self.cube_type.get()} anchor found at ({self.reset_x}, {self.reset_y})",
                        fg="green"))
                else:
                    self.root.after(0, lambda: self.info_label.config(
                        text=f"{self.cube_type.get()} anchor not found. Please check the image.",
                        fg="red"))
                    self.reset_x = None
                    self.reset_y = None
                    self.reset_w = None
                    self.reset_h = None
                
                self.root.after(0, self.update_preview)
                
            except Exception as e:
                self.root.after(0, lambda: self.info_label.config(
                    text=f"Error: {str(e)}", fg="red"))
        
        threading.Thread(target=detect_thread, daemon=True).start()
        
    def calculate_crop_region(self):
        if self.original_image is None or self.reset_x is None or self.reset_y is None:
            return None
        
        h, w = self.original_image.shape[:2]
        offset_x = self.offset_x.get()
        offset_above = self.offset_above.get()
        stat_width = self.stat_width.get()
        stat_height = self.stat_height.get()
        
        # Calculate crop region
        crop_x = max(0, self.reset_x + offset_x)
        crop_y = max(0, self.reset_y - offset_above)
        crop_w = min(w - crop_x, stat_width)
        # Use fixed height instead of calculating
        crop_h = min(stat_height, h - crop_y)
        
        # Validate and fix crop region to ensure positive dimensions
        if crop_w <= 0:
            # If crop_x is too far right, move it left
            crop_x = max(0, w - stat_width)
            crop_w = min(stat_width, w - crop_x)
        
        if crop_h <= 0:
            # If crop_y is too far down, move it up
            crop_y = max(0, h - stat_height)
            crop_h = min(stat_height, h - crop_y)
        
        # Final validation - ensure all values are positive and within bounds
        crop_x = max(0, min(crop_x, w - 1))
        crop_y = max(0, min(crop_y, h - 1))
        crop_w = max(1, min(crop_w, w - crop_x))
        crop_h = max(1, min(crop_h, h - crop_y))
        
        return (int(crop_x), int(crop_y), int(crop_w), int(crop_h))
        
    def update_preview(self):
        if self.original_image is None:
            return
        
        # Create a copy for drawing
        display_img = self.original_image.copy()
        h, w = display_img.shape[:2]
        
        # Draw Reset button if detected
        if self.reset_x is not None and self.reset_y is not None and self.reset_w is not None and self.reset_h is not None:
            cv.rectangle(display_img, 
                        (self.reset_x, self.reset_y), 
                        (self.reset_x + self.reset_w, self.reset_y + self.reset_h), 
                        (255, 0, 0), 2)
            cv.putText(display_img, "Reset (Anchor)", 
                      (self.reset_x, self.reset_y - 10), 
                      cv.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
        
        # Draw crop region
        crop_region = self.calculate_crop_region()
        if crop_region:
            crop_x, crop_y, crop_w, crop_h = crop_region
            cv.rectangle(display_img, 
                        (crop_x, crop_y), 
                        (crop_x + crop_w, crop_y + crop_h), 
                        (0, 255, 0), 2)
            cv.putText(display_img, "Crop Region", 
                      (crop_x, crop_y - 10), 
                      cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Update info
            info_text = f"Crop Region:\nX: {crop_x} ({crop_x/w:.1%})\nY: {crop_y} ({crop_y/h:.1%})\n"
            info_text += f"W: {crop_w} ({crop_w/w:.1%})\nH: {crop_h} ({crop_h/h:.1%})"
            self.info_label.config(text=info_text, fg="black")
        
        # Resize for display (max 700px height)
        display_h, display_w = display_img.shape[:2]
        max_height = 700
        if display_h > max_height:
            scale = max_height / display_h
            new_w = int(display_w * scale)
            new_h = int(display_h * scale)
            display_img = cv.resize(display_img, (new_w, new_h))
        
        # Convert to RGB for tkinter
        display_img_rgb = cv.cvtColor(display_img, cv.COLOR_BGR2RGB)
        pil_image = Image.fromarray(display_img_rgb)
        photo = ImageTk.PhotoImage(image=pil_image)
        
        self.image_label.config(image=photo, text="")
        self.image_label.image = photo  # Keep a reference
        
    def save_config(self):
        try:
            # Save selected slider values into the matching cube profile.
            if self.cube_type.get() == "Bright":
                glowing_offset_x = OFFSET_X
                glowing_offset_above = OFFSET_ABOVE
                glowing_stat_width = STAT_WIDTH
                glowing_stat_height = STAT_HEIGHT
                bright_offset_x = self.offset_x.get()
                bright_offset_above = self.offset_above.get()
                bright_stat_width = self.stat_width.get()
                bright_stat_height = self.stat_height.get()
            else:
                glowing_offset_x = self.offset_x.get()
                glowing_offset_above = self.offset_above.get()
                glowing_stat_width = self.stat_width.get()
                glowing_stat_height = self.stat_height.get()
                bright_offset_x = BRIGHT_OFFSET_X
                bright_offset_above = BRIGHT_OFFSET_ABOVE
                bright_stat_width = BRIGHT_STAT_WIDTH
                bright_stat_height = BRIGHT_STAT_HEIGHT

            config_content = f'''"""
Configuration file for crop region offsets
Adjust these values to fine-tune the auto-detected crop region
"""

# Crop region offsets relative to Reset button position
# These determine where the crop region is positioned relative to the detected Reset button

# X offset from Reset button
# Negative value = move LEFT from Reset button
# Positive value = move RIGHT from Reset button
OFFSET_X = {glowing_offset_x}

# Y offset from Reset button (always positive, moves UP)
# This is how many pixels ABOVE the Reset button to start the crop
OFFSET_ABOVE = {glowing_offset_above}

# Width of the crop region (in pixels)
# Should be wide enough to capture stat lines like "Attack Power +xx"
STAT_WIDTH = {glowing_stat_width}

# Height of the crop region (in pixels)
# Fixed height for the crop region
STAT_HEIGHT = {glowing_stat_height}

# Bright cube offsets (different from Glowing cube)
# For Bright cube, potential lines are under "AFTER" text
# These offsets are relative to the Reset button position
BRIGHT_OFFSET_X = {bright_offset_x}
BRIGHT_OFFSET_ABOVE = {bright_offset_above}
BRIGHT_STAT_WIDTH = {bright_stat_width}
BRIGHT_STAT_HEIGHT = {bright_stat_height}
'''
            with open('crop_config.py', 'w') as f:
                f.write(config_content)
            messagebox.showinfo("Success", "Configuration saved to crop_config.py")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save config: {str(e)}")


def main():
    root = tk.Tk()
    app = CropRegionTuner(root)
    root.mainloop()


if __name__ == "__main__":
    main()

