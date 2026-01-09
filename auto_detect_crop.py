"""
Automatic detection of Potential region from screenshots
"""
import cv2 as cv
import numpy as np
import tesseract_config  # Configure Tesseract path before importing pytesseract
import pytesseract
import os
from crop_config import OFFSET_X, OFFSET_ABOVE, STAT_WIDTH, STAT_HEIGHT, BRIGHT_OFFSET_X, BRIGHT_OFFSET_ABOVE, BRIGHT_STAT_WIDTH, BRIGHT_STAT_HEIGHT

def find_reset_button_template(image, template_path=None, debug=False):
    """
    Find Reset button using template matching.
    
    Args:
        image: OpenCV image (BGR format) - full window screenshot
        template_path: Path to Reset button template image. If None, tries 'templates/reset_button'
        debug: If True, print debug info
    
    Returns:
        Tuple (x, y, width, height) of Reset button, or None if not found
    """
    if template_path is None:
        # Try to find template in templates folder
        script_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(script_dir, 'templates', 'reset_button')
    
    if not os.path.exists(template_path):
        if debug:
            print(f"[TEMPLATE-MATCH] Template not found at: {template_path}")
        return None
    
    try:
        # Load template
        template = cv.imread(template_path, cv.IMREAD_COLOR)
        if template is None:
            if debug:
                print(f"[TEMPLATE-MATCH] Failed to load template from: {template_path}")
            return None
        
        # Convert both to grayscale for better matching
        img_gray = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
        template_gray = cv.cvtColor(template, cv.COLOR_BGR2GRAY)
        
        # Try multiple matching methods for better tolerance
        # TM_CCOEFF_NORMED works well but may fail with cursor overlay
        # Try different methods and pick the best result
        matching_methods = [
            (cv.TM_CCOEFF_NORMED, 0.6),  # Lower threshold for cursor overlay tolerance
            (cv.TM_CCORR_NORMED, 0.6),   # Alternative method
        ]
        
        best_match = None
        best_confidence = 0.0
        
        for method, threshold in matching_methods:
            try:
                result = cv.matchTemplate(img_gray, template_gray, method)
                min_val, max_val, min_loc, max_loc = cv.minMaxLoc(result)
                
                # For TM_SQDIFF, lower values are better, but we're not using it
                # For other methods, higher values are better
                if max_val >= threshold and max_val > best_confidence:
                    best_confidence = max_val
                    best_match = (max_loc[0], max_loc[1], max_val, method)
            except Exception as e:
                if debug:
                    print(f"[TEMPLATE-MATCH] Error with method {method}: {e}")
                continue
        
        # Use the best match if it meets the threshold
        if best_match and best_confidence >= 0.6:
            # Get template dimensions
            template_h, template_w = template_gray.shape
            
            # Calculate button center position
            reset_x = best_match[0]
            reset_y = best_match[1]
            reset_w = template_w
            reset_h = template_h
            
            if debug:
                print(f"[TEMPLATE-MATCH] Reset button found at: x={reset_x}, y={reset_y}, w={reset_w}, h={reset_h}, confidence={best_confidence:.2f}")
            
            return (reset_x, reset_y, reset_w, reset_h)
        else:
            if debug:
                print(f"[TEMPLATE-MATCH] Reset button not found (best match confidence: {best_confidence:.2f}, threshold: 0.6)")
            return None
    except Exception as e:
        if debug:
            print(f"[TEMPLATE-MATCH] Error in template matching: {e}")
        return None


def is_reset_button_unavailable(image, template_path=None, debug=False):
    """
    Check if Reset button is in unavailable (grayed out) state.
    
    Uses template matching first, then falls back to brightness analysis if template not found.
    
    Args:
        image: OpenCV image (BGR format) - full window screenshot
        template_path: Path to Reset button unavailable template image. If None, tries 'templates/reset_button_unavailable'
        debug: If True, print debug info
    
    Returns:
        True if unavailable template is found (button is grayed out), False otherwise
    """
    if template_path is None:
        # Try to find template in templates folder
        script_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(script_dir, 'templates', 'reset_button_unavailable')
    
    template_exists = os.path.exists(template_path)
    template_match_result = None
    
    # Try template matching first if template exists
    if template_exists:
        try:
            # Load template
            template = cv.imread(template_path, cv.IMREAD_COLOR)
            if template is None:
                if debug:
                    print(f"[TEMPLATE-MATCH] Failed to load unavailable template from: {template_path}")
                template_match_result = None
            else:
                # Convert both to grayscale for better matching
                img_gray = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
                template_gray = cv.cvtColor(template, cv.COLOR_BGR2GRAY)
                
                # Try multiple matching methods for better tolerance
                # Lower threshold to 0.5 for better detection of grayed-out buttons
                matching_methods = [
                    (cv.TM_CCOEFF_NORMED, 0.5),  # Lower threshold for better grayed-out button detection
                    (cv.TM_CCORR_NORMED, 0.5),   # Alternative method
                    (cv.TM_SQDIFF_NORMED, 0.5),  # Another method (lower is better for SQDIFF)
                ]
                
                best_confidence = 0.0
                best_method = None
                
                for method, threshold in matching_methods:
                    try:
                        result = cv.matchTemplate(img_gray, template_gray, method)
                        min_val, max_val, min_loc, max_loc = cv.minMaxLoc(result)
                        
                        # For TM_SQDIFF_NORMED, lower values are better (1 - value gives similarity)
                        if method == cv.TM_SQDIFF_NORMED:
                            similarity = 1 - min_val
                            if similarity >= threshold and similarity > best_confidence:
                                best_confidence = similarity
                                best_method = method
                        else:
                            # For other methods, higher values are better
                            if max_val >= threshold and max_val > best_confidence:
                                best_confidence = max_val
                                best_method = method
                    except Exception as e:
                        if debug:
                            print(f"[TEMPLATE-MATCH] Error with method {method}: {e}")
                        continue
                
                # If we found a match above threshold, button is unavailable
                # Lower threshold to 0.5 for better detection
                if best_confidence >= 0.5:
                    if debug:
                        print(f"[TEMPLATE-MATCH] Reset button is UNAVAILABLE (grayed out) - confidence: {best_confidence:.2f}, method: {best_method}")
                    return True
                else:
                    template_match_result = False
                    if debug:
                        print(f"[TEMPLATE-MATCH] Template match confidence too low ({best_confidence:.2f}), falling back to brightness check")
        except Exception as e:
            if debug:
                print(f"[TEMPLATE-MATCH] Error in template matching: {e}, falling back to brightness check")
            template_match_result = None
    else:
        if debug:
            print(f"[TEMPLATE-MATCH] Unavailable template not found at: {template_path}, using brightness check")
        template_match_result = None
    
    # Fallback: Use brightness analysis if template matching failed, had low confidence, or template doesn't exist
    # Grayed-out buttons are typically darker (lower brightness)
    if template_match_result is None or template_match_result is False:
        if debug:
            print(f"[BRIGHTNESS-CHECK] Using brightness analysis to detect grayed-out button...")
        
        reset_pos = find_reset_button_template(image, debug=debug)
        if reset_pos:
            reset_x, reset_y, reset_w, reset_h = reset_pos
            # Extract button region
            button_region = image[reset_y:reset_y+reset_h, reset_x:reset_x+reset_w]
            if button_region.size > 0:
                # Convert to grayscale and calculate mean brightness
                button_gray = cv.cvtColor(button_region, cv.COLOR_BGR2GRAY)
                mean_brightness = np.mean(button_gray)
                
                # Grayed-out buttons typically have brightness < 120 (out of 255)
                # Normal buttons are usually brighter (> 150)
                # Use a threshold around 120-130 to distinguish
                threshold = 125  # Adjust based on testing
                is_grayed = mean_brightness < threshold
                
                if debug:
                    print(f"[BRIGHTNESS-CHECK] Reset button brightness: {mean_brightness:.1f}, threshold: {threshold}, is_grayed: {is_grayed}")
                
                return is_grayed
        # If we can't find button or analyze it, assume available (safer to continue)
        if debug:
            print(f"[BRIGHTNESS-CHECK] Could not find reset button for brightness analysis, assuming available")
        return False
    
    # Template matching succeeded but didn't find grayed-out button
    # (This should not be reached if brightness check was used, but included for safety)
    if debug:
        print(f"[TEMPLATE-MATCH] Reset button is AVAILABLE (not grayed out)")
    return False


def detect_potential_region(image, debug=False, cube_type="Glowing"):
    """
    Automatically detect the Potential lines region in an image.
    Uses "Reset" button (via template matching) as an anchor point to locate the Potential section.
    
    Args:
        image: OpenCV image (BGR format)
        debug: If True, save debug images
        cube_type: "Glowing" or "Bright" - determines which offsets to use for crop region calculation
    
    Returns:
        Tuple ((crop_x, crop_y, crop_w, crop_h), (reset_x, reset_y, reset_w, reset_h)) 
        or (crop_region, None) if Reset button not found, or None if crop region can't be determined
    """
    # Get image dimensions - use tuple unpacking to avoid variable shadowing
    img_height, img_width = image.shape[:2]
    if debug:
        print(f"[AUTO-DETECT] Input image dimensions: {img_width}x{img_height}")
    
    # Method 1: Try template matching first (more reliable than OCR)
    reset_pos = find_reset_button_template(image, debug=debug)
    reset_found = False
    reset_x = None
    reset_y = None
    reset_w = None
    reset_h = None
    
    if reset_pos:
        reset_x, reset_y, reset_w, reset_h = reset_pos
        reset_found = True
    
    # Method 2: Fallback to OCR if template matching fails
    gray = None
    if not reset_found:
        if debug:
            print("[AUTO-DETECT] Template matching failed, falling back to OCR...")
        gray = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
        
        # Try different PSM modes (optimized - fewer modes for speed)
        # PSM 6 works best for finding "Reset" button
        ocr_configs = [
            ('--psm 6', 'uniform block'),  # Best for this use case
            ('--psm 11', 'sparse text'),   # Fallback
        ]
        
        # Also try with enhanced contrast
        enhanced_gray = cv.createCLAHE(clipLimit=2.0, tileGridSize=(8,8)).apply(gray)
        
        images_to_try = [
            (gray, 'original'),
            (enhanced_gray, 'enhanced'),
        ]
        
        all_potential_matches = []
        
        try:
            for img, img_name in images_to_try:
                if debug:
                    print(f"[AUTO-DETECT] Trying OCR on {img_name} image...")
                
                for psm_config, psm_desc in ocr_configs:
                    try:
                        # Get OCR data with bounding boxes
                        ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, config=psm_config)
                        
                        # Search for "Reset" button text
                        for i, text in enumerate(ocr_data['text']):
                            text_lower = text.lower().strip()
                            # More flexible matching - check for exact or close match
                            if len(text_lower) > 0:
                                # Check for "reset" - should be exact or close match
                                if text_lower == 'reset' or 'reset' in text_lower:
                                    x = ocr_data['left'][i]
                                    y = ocr_data['top'][i]
                                    width = ocr_data['width'][i]
                                    height = ocr_data['height'][i]
                                    conf = ocr_data['conf'][i]
                                    
                                    # Accept even low confidence matches (OCR can be finicky)
                                    if conf >= -1:  # -1 means no confidence data, but still valid
                                        all_potential_matches.append((x, y, width, height, conf, i, text, psm_config, img_name))
                                        if debug:
                                            print(f"[AUTO-DETECT] Found 'Reset' text at: x={x}, y={y}, w={width}, h={height}, conf={conf}, text='{text}', psm={psm_config}, img={img_name}")
                    except Exception as e:
                        if debug:
                            print(f"[AUTO-DETECT] Error with PSM {psm_config}: {e}")
                        continue
            
            # Remove duplicates (same location)
            unique_matches = []
            seen_locations = set()
            for match in all_potential_matches:
                x, y, btn_w, btn_h, conf, idx, text, psm, img_name = match  # Use btn_w, btn_h to avoid overwriting image dimensions
                # Consider matches within 20 pixels as duplicates
                location_key = (x // 20, y // 20)
                if location_key not in seen_locations:
                    seen_locations.add(location_key)
                    unique_matches.append(match)
            
            if debug:
                print(f"[AUTO-DETECT] Found {len(unique_matches)} unique 'Reset' text matches")
            
            # If multiple matches found, use the one with highest confidence (usually there's only one)
            if len(unique_matches) > 0:
                # Sort by confidence (descending) - prefer higher confidence
                unique_matches.sort(key=lambda m: -m[4])  # -conf for descending
                # Use the best match
                reset_x, reset_y, reset_w, reset_h, conf, idx, text, psm, img_name = unique_matches[0]
                reset_found = True
                if debug:
                    print(f"[AUTO-DETECT] Found 'Reset' anchor at: x={reset_x}, y={reset_y}, w={reset_w}, h={reset_h}, text='{text}'")
            else:
                if debug:
                    print(f"[AUTO-DETECT] No 'Reset' text found in OCR results")
                    # Debug: show what OCR actually found
                    try:
                        ocr_data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT, config='--psm 6')
                        all_texts = [t for t in ocr_data.get('text', []) if len(t.strip()) > 0]
                        print(f"[AUTO-DETECT] OCR found these texts: {all_texts[:20]}")
                    except:
                        pass
        except Exception as e:
            if debug:
                print(f"[AUTO-DETECT] Error in OCR detection: {e}")
                import traceback
                traceback.print_exc()
    
    if reset_found:
        # Calculate crop region based on "Reset" button position
        # The crop region should include "Attack Power +xx" and other stat lines
        # The Reset button is usually at the bottom of the Potential window
        
        # Load offsets from config file
        # These offsets are relative to the Reset button position
        # See crop_config.py to adjust these values
        
        if debug:
            print(f"[AUTO-DETECT] Reset button found at: x={reset_x}, y={reset_y}, w={reset_w}, h={reset_h}")
            print(f"[AUTO-DETECT] Image dimensions: {img_width}x{img_height}")
            print(f"[AUTO-DETECT] Reset button position check: x={reset_x} (should be < {img_width}), y={reset_y} (should be < {img_height})")
            if reset_x >= img_width or reset_y >= img_height:
                print(f"[AUTO-DETECT] WARNING: Reset button coordinates are OUTSIDE image bounds!")
                print(f"[AUTO-DETECT]   Reset button at ({reset_x}, {reset_y}) but image is only {img_width}x{img_height}")
                print(f"[AUTO-DETECT]   This suggests the image passed to detect_potential_region() may be incorrect or already cropped.")
        
        # Load offsets from config file based on cube type
        # These offsets are relative to the Reset button position
        # See crop_config.py to adjust these values
        if cube_type == "Bright":
            offset_x = BRIGHT_OFFSET_X
            offset_above = BRIGHT_OFFSET_ABOVE
            stat_width = BRIGHT_STAT_WIDTH
            stat_height = BRIGHT_STAT_HEIGHT
        else:  # Default to Glowing cube
            offset_x = OFFSET_X
            offset_above = OFFSET_ABOVE
            stat_width = STAT_WIDTH
            stat_height = STAT_HEIGHT
        
        # Calculate crop region based on Reset button position
        # X position: Reset X + offset_x
        # If offset_x is negative, crop goes LEFT of Reset
        # If offset_x is positive, crop goes RIGHT of Reset
        crop_x = max(0, reset_x + offset_x)
        # Y position: Reset Y - offset_above (moves up from Reset button)
        # For both Glowing and Bright cube, potential lines are above the Reset button
        crop_y = max(0, reset_y - offset_above)
        # Width: enough for stat lines (should be narrow, only covering right panel stat area)
        # Ensure width doesn't exceed image bounds
        crop_w = min(img_width - crop_x, stat_width)
        # Height: use fixed height from config
        crop_h = min(stat_height, img_height - crop_y)
        
        # Validate and fix crop region to ensure positive dimensions
        if crop_w <= 0:
            if debug:
                print(f"[AUTO-DETECT] Warning: Calculated width is negative or zero ({crop_w}), adjusting...")
            # If crop_x is too far right, move it left
            crop_x = max(0, img_width - stat_width)
            crop_w = min(stat_width, img_width - crop_x)
        
        if crop_h <= 0:
            if debug:
                print(f"[AUTO-DETECT] Warning: Calculated height is negative or zero ({crop_h}), adjusting...")
            # If crop_y is too far down, move it up
            crop_y = max(0, img_height - stat_height)
            crop_h = min(stat_height, img_height - crop_y)
        
        # Final validation - ensure all values are positive and within bounds
        # IMPORTANT: Ensure crop_x + crop_w <= img_width and crop_y + crop_h <= img_height
        # Don't clamp crop_x to img_width-1 first, as that would make crop_w = 1
        crop_x = max(0, crop_x)
        crop_y = max(0, crop_y)
        
        # Ensure crop region fits within image bounds by adjusting position if needed
        if crop_x + crop_w > img_width:
            # Move crop_x left to fit
            crop_x = max(0, img_width - crop_w)
        
        if crop_y + crop_h > img_height:
            # Move crop_y up to fit
            crop_y = max(0, img_height - crop_h)
        
        # Final safety check - ensure dimensions are valid
        crop_w = max(1, min(crop_w, img_width - crop_x))
        crop_h = max(1, min(crop_h, img_height - crop_y))
        
        if debug:
            print(f"[AUTO-DETECT] Crop calculation:")
            print(f"[AUTO-DETECT]   Reset button: x={reset_x}, y={reset_y}")
            print(f"[AUTO-DETECT]   Cube type: {cube_type}, offset_x={offset_x} -> crop_x = {reset_x} + {offset_x} = {crop_x}")
            print(f"[AUTO-DETECT]   offset_above={offset_above} -> crop_y = {reset_y} - {offset_above} = {crop_y}")
            print(f"[AUTO-DETECT]   crop_w={crop_w}, crop_h={crop_h} (fixed width: {stat_width}, height: {stat_height})")
        
        if debug:
            print(f"[AUTO-DETECT] Calculated crop region from 'Reset' anchor: x={crop_x}, y={crop_y}, w={crop_w}, h={crop_h}")
        
        # Save visualization
        if debug:
            vis_img = image.copy()
            # Draw box around Reset button (anchor)
            cv.rectangle(vis_img, (reset_x, reset_y), 
                       (reset_x + reset_w, reset_y + reset_h), (255, 0, 0), 2)
            cv.putText(vis_img, "Reset (Anchor)", (reset_x, reset_y - 10), 
                      cv.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            # Draw box around detected Potential region
            cv.rectangle(vis_img, (crop_x, crop_y), (crop_x + crop_w, crop_y + crop_h), (0, 255, 0), 2)
            cv.putText(vis_img, "Detected Potential Region", (crop_x, crop_y - 10), 
                      cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv.imwrite('auto_detected_crop_region.png', vis_img)
            print(f"[AUTO-DETECT] Saved visualization to: auto_detected_crop_region.png")
        
        # Return both crop region and reset button position
        return ((crop_x, crop_y, crop_w, crop_h), (reset_x, reset_y, reset_w, reset_h))
    
    # Method 2: If "Reset" button not found, try to find stat lines directly
    # Look for common stat patterns: "STR:", "DEX:", "INT:", "LUK:", "Max HP", "Max MP", etc.
    if not reset_found:
        if debug:
            print("[AUTO-DETECT] 'Potential' text not found, trying to find stat lines directly...")
        
        stat_keywords = ['str:', 'dex:', 'int:', 'luk:', 'max hp', 'max mp', 'all stats', '%', '+']
        stat_matches = []
        
        for img, img_name in images_to_try:
            for psm_config, psm_desc in ocr_configs:
                try:
                    ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, config=psm_config)
                    
                    for i, text in enumerate(ocr_data['text']):
                        text_lower = text.lower().strip()
                        if len(text_lower) > 0:
                            # Check if text contains stat keywords
                            for keyword in stat_keywords:
                                if keyword in text_lower:
                                    x = ocr_data['left'][i]
                                    y = ocr_data['top'][i]
                                    width = ocr_data['width'][i]
                                    height = ocr_data['height'][i]
                                    conf = ocr_data['conf'][i]
                                    
                                    if conf >= -1:
                                        stat_matches.append((x, y, width, height, conf, text))
                                        if debug:
                                            print(f"[AUTO-DETECT] Found stat line: '{text}' at x={x}, y={y}, conf={conf}")
                                    break
                except:
                    continue
        
        # If we found stat lines, use the topmost one to estimate the region
        if stat_matches:
            if debug:
                print(f"[AUTO-DETECT] Found {len(stat_matches)} stat line matches")
            # Sort by y position (ascending - topmost first)
            stat_matches.sort(key=lambda m: m[1])
            # Use the topmost stat line
            stat_x, stat_y, stat_w, stat_h, stat_conf, stat_text = stat_matches[0]
            
            # Calculate crop region based on stat line position
            # Assume "Potential" title is ~30-50px above the first stat line
            crop_x = max(0, stat_x - 50)  # Start left of stat lines
            crop_y = max(0, stat_y - 50)  # Start above to include "Potential" title
            crop_w = min(img_width - crop_x, 450)  # Width for stat lines
            crop_h = min(img_height - crop_y, 180)  # Height for title + 3-4 stat lines
            
            if debug:
                print(f"[AUTO-DETECT] Calculated crop region from stat line: x={crop_x}, y={crop_y}, w={crop_w}, h={crop_h}")
            
            # Save visualization
            if debug:
                vis_img = image.copy()
                cv.rectangle(vis_img, (crop_x, crop_y), (crop_x + crop_w, crop_y + crop_h), (0, 255, 0), 2)
                cv.putText(vis_img, "Detected from Stat Lines", (crop_x, crop_y - 10), 
                          cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv.imwrite('auto_detected_crop_region.png', vis_img)
                print(f"[AUTO-DETECT] Saved visualization to: auto_detected_crop_region.png")
            
            # Return crop region but no reset button position (found via stat lines, not reset button)
            return ((crop_x, crop_y, crop_w, crop_h), None)
    
    # Method 3: Use heuristics based on typical UI layout
    # Potential section is often in the center-right area of enhance window
    # Try a default region if detection fails
    if debug:
        print("[AUTO-DETECT] All detection methods failed, using fallback region")
        # Show what OCR actually found for debugging
        try:
            ocr_data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT, config='--psm 6')
            all_texts = [t for t in ocr_data.get('text', []) if len(t.strip()) > 0]
            if all_texts:
                print(f"[AUTO-DETECT] OCR found these texts: {all_texts[:20]}")
        except:
            pass
    
    # Fallback: center-right region (typical for Potential window)
    fallback_x = int(img_width * 0.4)
    fallback_y = int(img_height * 0.2)
    fallback_w = int(img_width * 0.5)
    fallback_h = int(img_height * 0.3)
    
    # Return fallback crop region but no reset button position
    return ((fallback_x, fallback_y, fallback_w, fallback_h), None)

