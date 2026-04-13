"""
Configuration file for crop region offsets
Adjust these values to fine-tune the auto-detected crop region
"""

# Crop region offsets relative to Reset button position
# These determine where the crop region is positioned relative to the detected Reset button

# X offset from Reset button
# Negative value = move LEFT from Reset button
# Positive value = move RIGHT from Reset button
OFFSET_X = -76

# Y offset from Reset button (always positive, moves UP)
# This is how many pixels ABOVE the Reset button to start the crop
OFFSET_ABOVE = 388

# Width of the crop region (in pixels)
# Should be wide enough to capture stat lines like "Attack Power +xx"
STAT_WIDTH = 284

# Height of the crop region (in pixels)
# Fixed height for the crop region
STAT_HEIGHT = 107

# Bright cube offsets (different from Glowing cube)
# For Bright cube, potential lines are under "AFTER" text
# These offsets are relative to the Reset button position
BRIGHT_OFFSET_X = 167
BRIGHT_OFFSET_ABOVE = 288
BRIGHT_STAT_WIDTH = 184
BRIGHT_STAT_HEIGHT = 97