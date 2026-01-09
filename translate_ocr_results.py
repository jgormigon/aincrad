import re

# Lazy import to avoid errors during module import
_potlines_instance = None
_current_window_name = None

def clear_potlines_cache():
    """Clear the cached potlines instance - call this when starting a new bot run"""
    global _potlines_instance, _current_window_name
    _potlines_instance = None
    _current_window_name = None

def get_potlines(window_name=None, debug=False, crop_region=None, test_image_path=None, auto_detect_crop=False, cube_type="Glowing"):
    """Get or create potlines instance (lazy initialization)"""
    global _potlines_instance, _current_window_name
    
    # Get current instance values
    current_test_image = getattr(_potlines_instance, 'test_image_path', None) if _potlines_instance else None
    current_crop_region = getattr(_potlines_instance, 'crop_region', None) if _potlines_instance else None
    current_auto_detect = getattr(_potlines_instance, 'auto_detect_crop', False) if _potlines_instance else False
    current_cube_type = getattr(_potlines_instance, 'cube_type', "Glowing") if _potlines_instance else "Glowing"
    
    # If window name, crop region, test image, auto_detect, or cube_type changed or instance doesn't exist, create new one
    # Important: Check if test_image_path changed (including from None to value or value to None)
    test_image_changed = (test_image_path != current_test_image)
    
    # When auto_detect_crop is True, we don't check crop_region changes (the instance detects and caches it internally)
    # Only check crop_region changes if auto_detect is False (manual crop_region)
    if auto_detect_crop:
        crop_region_changed = False  # Don't check crop_region when auto-detecting
    else:
        crop_region_changed = (crop_region is not None and crop_region != current_crop_region) or (crop_region is None and current_crop_region is not None and not current_auto_detect)
    
    should_recreate = (_potlines_instance is None or 
                      (window_name and window_name != _current_window_name) or
                      test_image_changed or
                      crop_region_changed or
                      (auto_detect_crop != current_auto_detect) or
                      (cube_type != current_cube_type))
    
    if should_recreate:
        try:
            from image_finder import potlines
            if debug:
                print(f"[DEBUG] Recreating potlines instance - changes detected:")
                print(f"  Current test_image: {current_test_image}, New test_image: {test_image_path}")
                print(f"  Current crop_region: {current_crop_region}, New crop_region: {crop_region}")
                print(f"  Current auto_detect: {current_auto_detect}, New auto_detect: {auto_detect_crop}")
            _potlines_instance = potlines(window_name, crop_region=crop_region, test_image_path=test_image_path, auto_detect_crop=auto_detect_crop, cube_type=cube_type)
            _current_window_name = window_name
            if debug:
                print(f"[DEBUG] Created new potlines instance for window: {window_name}, crop_region: {crop_region}, test_image: {test_image_path}, auto_detect: {auto_detect_crop}")
        except Exception as e:
            error_msg = (
                f"\n{'='*60}\n"
                f"ERROR: Failed to initialize window capture!\n\n"
                f"{str(e)}\n"
                f"{'='*60}\n"
            )
            raise Exception(error_msg) from e
    else:
        if debug and _potlines_instance:
            current_test_image = getattr(_potlines_instance, 'test_image_path', None)
            print(f"[DEBUG] Reusing existing potlines instance")
            print(f"  Using test_image: {current_test_image if current_test_image else 'None (using live window)'}")
    return _potlines_instance

single_lines_dict = {"BD":['Boss Damage: +30%', 'Boss Damage: +35%', 'Boss Damage: +40%', 'Boss Damage: +45%', 'Boss Damage: +50%'],"IA":['tem Acquisition Rate: +12%','tem Acquisition Rate: +10%'],"CD":['Critical Damage: +3%', 'Critical Damage: +6%'],"ATT":['ATT: +3%','ATT: +4%','ATT: +6%','ATT: +7%','ATT: +9%','ATT: +10%', 'Attack Power: +3%', 'Attack Power: +4%', 'Attack Power: +6%', 'Attack Power: +7%', 'Attack Power: +9%', 'Attack Power: +10%', 'Attack Power +3%', 'Attack Power +4%', 'Attack Power +6%', 'Attack Power +7%', 'Attack Power +9%', 'Attack Power +10%'],"MATT":['Magic ATT: +6%','Magic ATT: +9%']}
double_lines_dict = {"IED":['Attacks ignore 30% Monster', 'Attacks ignore 35% Monster', 'Attacks ignore 40% Monster', 'Attacks ignore 45% Monster', 'Attacks ignore 50% Monster'],'Drop':['Increases Item Drop Rate by a'],}
single_lines_list = ['Boss Damage: +30%', 'Boss Damage: +35%', 'Boss Damage: +40%', 'Boss Damage: +45%', 'Boss Damage: +50%','tem Acquisition Rate: +12%','tem Acquisition Rate: +10%','Critical Damage: +3%', 'Critical Damage: +6%','ATT: +3%','ATT: +4%','ATT: +6%','ATT: +7%','ATT: +9%','ATT: +10%','Attack Power: +3%', 'Attack Power: +4%', 'Attack Power: +6%', 'Attack Power: +7%', 'Attack Power: +9%', 'Attack Power: +10%', 'Attack Power +3%', 'Attack Power +4%', 'Attack Power +6%', 'Attack Power +7%', 'Attack Power +9%', 'Attack Power +10%','Magic ATT: +6%','Magic ATT: +9%']
double_lines_list = ['Attacks ignore 30% Monster', 'Attacks ignore 35% Monster', 'Attacks ignore 40% Monster', 'Attacks ignore 45% Monster', 'Attacks ignore 50% Monster','Increases Item Drop Rate by a','Increases tem and Meso Drop']

# Stat dictionaries - common OCR patterns for stat lines
# These patterns account for OCR variations like "STR: +9%" or "STR +9%" or "STR:+9%"
stat_patterns = {
    "STR": [r'STR\s*:?\s*\+?(\d+)%', r'STR\s*\+(\d+)%'],  # Added optional + for missing + cases
    "DEX": [r'DEX\s*:?\s*\+?(\d+)%', r'DEX\s*\+(\d+)%'],
    "INT": [r'INT\s*:?\s*\+?(\d+)%', r'INT\s*\+(\d+)%'],
    "LUK": [r'LUK\s*:?\s*\+?(\d+)%', r'LUK\s*\+(\d+)%'],  # Added optional + for missing + cases
    "ALL": [r'All\s+Stats\s*:?\s*\+?(\d+)%', r'All\s+Stats\s*\+(\d+)%', r'All\s*:?\s*\+?(\d+)%', r'Allstats\s*:?\s*\+?(\d+)%', r'Allstats\s*\+(\d+)%', r'Alistats\s*:?\s*\+?(\d+)%', r'Alistats\s*\+(\d+)%', r'Alstats\s*:?\s*\+?(\d+)%', r'Alstats\s*\+(\d+)%'],
    "ATT": [r'(?<!Magic\s)ATT\s*:?\s*\+?(\d+)%', r'(?<!Magic\s)ATT\s*\+(\d+)%', r'(?<!Magic\s)Attack\s+Power\s*:?\s*\+?(\d+)%', r'(?<!Magic\s)Attack\s+Power\s*\+(\d+)%', r'(?<!Magic)AttackPower\s*:?\s*\+?(\d+)%', r'(?<!Magic)AttackPower\s*\+(\d+)%'],
    "MATT": [r'Magic\s+ATT\s*:?\s*\+?(\d+)%', r'Magic\s+ATT\s*\+(\d+)%', r'MagicATT\s*:?\s*\+?(\d+)%', r'MagicATT\s*\+(\d+)%', r'Magic\s+Attack\s+Power\s*:?\s*\+?(\d+)%', r'Magic\s+Attack\s+Power\s*\+(\d+)%', r'MagicAttackPower\s*:?\s*\+?(\d+)%', r'MagicAttackPower\s*\+(\d+)%'],
    "BD": [r'Boss\s+Damage\s*:?\s*\+?(\d+)%', r'Boss\s+Damage\s*\+(\d+)%'],
    "IED": [r'Ign[aoe]r[ae]Defense\s*\+(\d+)%', r'Ign[aoe]r[ae]Defense\s*:?\s*\+?(\d+)%', r'Ign[aoe]r[ae]\s+Defense\s*\+(\d+)%', r'Ign[aoe]r[ae]\s+Defense\s*:?\s*\+?(\d+)%', r'Attacks\s+ignore\s+(\d+)%\s+Monster(?:\s+Defense)?']
}
def get_lines(window_name=None, debug=False, crop_region=None, test_image_path=None, auto_detect_crop=False, cube_type="Glowing"):
    try:
        raw_lines = get_potlines(window_name, debug=debug, crop_region=crop_region, test_image_path=test_image_path, auto_detect_crop=auto_detect_crop, cube_type=cube_type)
        if raw_lines is None:
            if debug:
                print("[DEBUG] get_potlines returned None")
            return ""
        
        # Always call get_ocr_result which will take a fresh screenshot
        # get_ocr_result() will save debug_original_image.png if debug is enabled
        lines = raw_lines.get_ocr_result(debug=debug)
        
        if lines is None:
            if debug:
                print("[DEBUG] get_ocr_result returned None")
            return ""
        if debug:
            print(f"[DEBUG] Raw OCR text: {repr(lines)}")
        return lines
    except Exception as e:
        print(f"Error getting OCR lines: {e}")
        if debug:
            import traceback
            traceback.print_exc()
        return ""
#print(single_lines_dict.values())
def split_lines(lines):
    if lines is None:
        return []
    if not isinstance(lines, str):
        return []
    
    splitlines = lines.split("\n")
    # Remove empty last element if it exists
    if splitlines and splitlines[-1] == "":
        splitlines.remove(splitlines[-1])
    #print(splitlines)
    return splitlines

def fix_ocr_percent_errors(line):
    """
    Fix common OCR errors where '%' is misread as '5'.
    Example: 'Attack Power +95' -> 'Attack Power +9%'
    Valid stat values: 3, 4, 6, 7, 9, 10, 12, 13, 15, 18, 21, 30, 35, 40, 45, 50
    Since there's no possible line with +95, +85, +75, etc., we fix +XX5 patterns.
    """
    if not line:
        return line
    
    import re
    
    # Fix pattern: +XX5 where XX is a digit, at end or followed by whitespace/comma
    # Replace trailing 5 with % for numbers that don't make sense
    # Valid stats ending in 5: +15, +35, +45 (but user said no +95 possible)
    # We'll fix: +25, +55, +65, +75, +85, +95 (definitely wrong)
    # And also +35, +45 if they appear (could be valid but likely misreads)
    
    def replace_percent_error(match):
        """Replace trailing 5 with % if it's likely a misread"""
        full_match = match.group(0)
        # Extract the number before the 5 (e.g., "9" from "+95")
        number_match = re.search(r'\+(\d+)5', full_match)
        if number_match:
            prefix = number_match.group(1)
            if prefix:
                prefix_num = int(prefix)
                # Fix all +XX5 where XX >= 2 (since user said no +95 is possible)
                # This covers: +25, +35, +45, +55, +65, +75, +85, +95
                # +15 is valid, so we skip it (prefix_num == 1)
                if prefix_num >= 2:
                    return full_match.replace('5', '%')
        return full_match
    
    # Match: + followed by digits, then 5, at word boundary or end of line/comma
    # This will match patterns like: +95, +85, +75, +65, +55, +45, +35, +25
    fixed = re.sub(r'\+\d+5(?=\s|$|,|%)', replace_percent_error, line)
    
    return fixed

def fix_missing_plus_sign(line):
    """
    Fix OCR errors where '+' sign is missing before percentages.
    Example: 'LUK 12%' -> 'LUK +12%', 'B LUK 12%' -> 'LUK +12%'
    Handles stat names: STR, DEX, INT, LUK, ALL/All Stats, ATT/Attack Power, etc.
    """
    if not line:
        return line
    
    import re
    
    # Pattern to match stat names followed by optional colon/space, then digits and %
    # This will match: "LUK 12%", "LUK: 12%", "STR 9%", "All Stats 6%", etc.
    # Also handles noise before stat name: "B LUK 12%" -> "LUK +12%"
    
    # Stat name patterns (case-insensitive) - order matters (longer patterns first)
    stat_patterns = [
        (r'(All\s+Stats?|Allstats?|Alistats?|Alstats?)', 'ALL'),  # All stats variations
        (r'(Magic\s+ATT|MagicATT|Magic\s+Attack\s+Power|MagicAttackPower)', 'MATT'),  # Magic ATT (with or without space)
        (r'(Attack\s+Power|AttackPower)', 'ATT'),  # Attack Power (with or without space)
        (r'(Boss\s+Damage)', 'BD'),  # Boss Damage
        (r'(Ign[aoe]r[ae]\s+Defense|Ign[aoe]r[ae]Defense)', 'IED'),  # Ignore Defense (handles OCR errors where 'o'→'a'/'e' and 'e'→'a'/'e', with or without space)
        (r'(Critical\s+Damage)', 'CD'),  # Critical Damage
        (r'(STR|DEX|INT|LUK)', 'STAT'),  # Single stat
        (r'(ATT)', 'ATT'),  # ATT (short) - but check for Magic first
    ]
    
    # Try to find and fix missing + signs
    for stat_pattern, stat_type in stat_patterns:
        # Pattern: optional text before, stat name, optional colon, optional space, digits, %
        # But NOT if there's already a + sign before the digits
        # This matches: "LUK 12%", "B LUK 12%", "LUK: 12%", etc.
        pattern = rf'([A-Za-z\s]*?)({stat_pattern})\s*:?\s+(?!\+)(\d+)%'
        
        def add_plus(match):
            # match.group(1) = text before stat (might be noise like "B " or "Alstats ")
            # match.group(2) = stat name
            # match.group(3) = number
            before = match.group(1).strip()
            stat = match.group(2)
            number = match.group(3)
            
            # Special handling: exclude Magic before AttackPower/ATT for ATT stat type
            if stat_type == 'ATT':
                # Check if "Magic" appears before the stat (with or without space)
                full_match = match.group(0)
                if re.search(r'Magic\s*Attack\s*Power|MagicAttackPower|Magic\s*ATT|MagicATT', full_match, re.IGNORECASE):
                    return full_match  # Don't fix, this is Magic ATT
            
            # Check if text before is likely noise
            # Noise indicators:
            # 1. Single character that's not a known stat prefix
            # 2. Text that doesn't match known stat patterns
            is_noise = False
            if before:
                before_clean = before.strip()
                # Single character before stat is likely noise (e.g., "B" before "LUK")
                if len(before_clean) == 1:
                    is_noise = True
                # Check if before text is part of a known stat pattern (like "Al" from "Alstats")
                elif stat_type == 'ALL' and before_clean.lower() in ['al', 'all']:
                    # This is part of "Allstats" or similar, keep it
                    is_noise = False
                elif before_clean.lower() in ['str', 'dex', 'int', 'luk', 'att', 'all']:
                    # This is a stat name, not noise
                    is_noise = False
                else:
                    # Unknown text, likely noise
                    is_noise = True
            
            if is_noise:
                # Remove noise and add +
                return f"{stat} +{number}%"
            else:
                # Keep the text before, but add + before number
                return f"{before} {stat} +{number}%" if before else f"{stat} +{number}%"
        
        line = re.sub(pattern, add_plus, line, flags=re.IGNORECASE)
    
    return line

def fix_missing_numbers(line):
    """
    Fix OCR errors where numbers are missing in stat lines.
    Example: 'Luk +Luk%' -> 'LUK +9%', 'STR +STR%' -> 'STR +9%'
    This handles cases where OCR reads the stat name instead of the number.
    """
    if not line:
        return line
    
    import re
    
    # Pattern to match stat name followed by + and then the stat name again (missing number)
    # Examples: "Luk +Luk%", "STR +STR%", "LUK +LUK%", "Luk+Luk%"
    # Match case-insensitively and handle both stat names being the same
    stat_pattern = r'\b(STR|DEX|INT|LUK|ATT|Luk|Str|Dex|Int|Att)\s*\+?\s*\1\s*%'
    
    def replace_missing_number(match):
        stat_name = match.group(1).upper()
        # Try to infer the number - use most common value (9)
        # Common stat values: 3, 4, 6, 7, 9, 10, 12, 15, 18, 21, 30, 35, 40, 45, 50
        # 9 is the most common for single-line stats
        inferred_value = 9  # Default to most common
        
        return f"{stat_name} +{inferred_value}%"
    
    # Apply the fix (case-insensitive)
    line = re.sub(stat_pattern, replace_missing_number, line, flags=re.IGNORECASE)
    
    # Also handle cases where stat name is repeated with % but no number and no +
    # Pattern: "LUK LUK%" or "STR STR%" (without +)
    repeated_stat_pattern = r'\b(STR|DEX|INT|LUK|ATT|Luk|Str|Dex|Int|Att)\s+\1\s*%'
    def fix_repeated_stat(match):
        stat_name = match.group(1).upper()
        return f"{stat_name} +9%"  # Use default value
    
    line = re.sub(repeated_stat_pattern, fix_repeated_stat, line, flags=re.IGNORECASE)
    
    return line

def normalize_line(line):
    """
    Normalize OCR line by removing leading noise characters and extra whitespace.
    Handles cases like '@ Attack Power +9%' -> 'Attack Power +9%'
    Also fixes OCR errors where '%' is misread as '5'.
    """
    if not line:
        return line
    
    import re
    
    # First fix OCR percent errors (e.g., +95 -> +9%)
    line = fix_ocr_percent_errors(line)
    
    # Fix missing numbers in stat lines (e.g., "Luk +Luk%" -> "LUK +9%")
    line = fix_missing_numbers(line)
    
    # Fix missing + signs before percentages (e.g., "LUK 12%" -> "LUK +12%")
    line = fix_missing_plus_sign(line)
    
    # Remove leading single non-alphanumeric characters that are likely OCR noise
    # Common OCR noise: @, ©, G, and other symbols
    normalized = line.strip()
    
    # Remove leading noise: any non-alphanumeric character at start, followed by space
    # This handles: '@ Attack Power' -> 'Attack Power', '© Attack Power' -> 'Attack Power', 'G Attack Power' -> 'Attack Power'
    # Pattern: any character that's not a letter, digit, or space, followed by space
    normalized = re.sub(r'^[^A-Za-z0-9\s]\s+', '', normalized)
    
    # Also handle single noise character directly before a letter (no space)
    # Check if first char is not alphanumeric and removing it would help
    if len(normalized) > 1 and not normalized[0].isalnum() and normalized[0] != ' ':
        # Check if removing first char would make it start with a known pattern
        test_line = normalized[1:].strip()
        for pattern_list in single_lines_dict.values():
            for pattern in pattern_list:
                pattern_start = pattern.split('+')[0].strip().lower()
                if test_line.lower().startswith(pattern_start):
                    normalized = test_line
                    break
    
    # Also try removing just the first character if it's a common noise character
    # and it's not part of a valid pattern
    if len(normalized) > 0:
        first_char = normalized[0]
        # Common OCR noise characters (expanded list including ©)
        noise_chars = '@©©G¢€£¥§¶•‡†‡°±²³´µ¶·¸¹º»¼½¾¿'
        if first_char in noise_chars and len(normalized) > 1:
            # Try removing the first character
            test_line = normalized[1:].strip()
            # Check if test_line starts with a known pattern (case-insensitive)
            for pattern_list in single_lines_dict.values():
                for pattern in pattern_list:
                    # Get the start of the pattern (before the +)
                    pattern_parts = pattern.split('+')
                    if len(pattern_parts) > 0:
                        pattern_start = pattern_parts[0].strip().lower()
                        test_start = test_line[:min(len(pattern_start), len(test_line))].strip().lower()
                        if test_start == pattern_start or test_line.lower().startswith(pattern_start):
                            normalized = test_line
                            break
                if normalized != line.strip():  # If we already normalized, break outer loop
                    break
    
    return normalized.strip()

def matches_line_pattern(line, pattern_list):
    """
    Check if a line matches any pattern in the list, accounting for OCR noise.
    Uses normalization and fuzzy matching to handle leading noise characters.
    Also uses regex patterns for ATT/Attack Power to handle variations.
    """
    if not line:
        return False
    
    import re
    normalized = normalize_line(line)
    
    # Try exact match first (both original and normalized)
    if line in pattern_list or normalized in pattern_list:
        return True
    
    # For stat lines (STR, DEX, INT, LUK, ALL, ATT), use regex matching since they can have noise
    # Check if this looks like a stat line using regex (accept any numeric value)
    stat_patterns_to_check = {
        "STR": [r'STR\s*:?\s*\+(\d+)%', r'STR\s*\+(\d+)%'],
        "DEX": [r'DEX\s*:?\s*\+(\d+)%', r'DEX\s*\+(\d+)%'],
        "INT": [r'INT\s*:?\s*\+(\d+)%', r'INT\s*\+(\d+)%'],
        "LUK": [r'LUK\s*:?\s*\+(\d+)%', r'LUK\s*\+(\d+)%'],
        "ALL": [r'All\s+Stats\s*:?\s*\+(\d+)%', r'All\s+Stats\s*\+(\d+)%', r'All\s*:?\s*\+(\d+)%', r'Allstats\s*:?\s*\+(\d+)%', r'Allstats\s*\+(\d+)%', r'Alistats\s*:?\s*\+(\d+)%', r'Alistats\s*\+(\d+)%', r'Alstats\s*:?\s*\+(\d+)%', r'Alstats\s*\+(\d+)%'],
        "ATT": [r'(?<!Magic\s)ATT\s*:?\s*\+(\d+)%', r'(?<!Magic\s)ATT\s*\+(\d+)%', r'(?<!Magic\s)Attack\s+Power\s*:?\s*\+(\d+)%', r'(?<!Magic\s)Attack\s+Power\s*\+(\d+)%']
    }
    
    for stat_type, patterns in stat_patterns_to_check.items():
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                # Found a stat line - if we're checking against single_lines_list, accept it
                # (since stat lines are valid potential lines even if not in the exact list)
                if pattern_list == single_lines_list:
                    return True
                # Also check if pattern_list contains this stat type
                has_stat_patterns = any(stat_type in p or stat_type.lower() in p.lower() for p in pattern_list)
                if has_stat_patterns:
                    return True
    
    # Try fuzzy matching - check if the line contains the pattern
    for pattern in pattern_list:
        pattern_clean = pattern.strip()
        normalized_clean = normalized.strip()
        line_clean = line.strip()
        
        # Check if normalized line contains the pattern (or vice versa)
        if pattern_clean in normalized_clean or normalized_clean in pattern_clean:
            return True
        
        # Check if original line contains pattern (for cases where normalization didn't help)
        if pattern_clean in line_clean:
            return True
        
        # Try matching without spaces and colons (for OCR variations)
        pattern_no_spaces = pattern_clean.replace(' ', '').replace(':', '')
        normalized_no_spaces = normalized_clean.replace(' ', '').replace(':', '')
        if pattern_no_spaces in normalized_no_spaces:
            return True
    
    return False

def set_lines(splitlines):
    # Handle empty or invalid input
    if not splitlines or len(splitlines) == 0:
        return "Trash", "Trash", "Trash"
    
    import re
    # Normalize all lines first
    normalized_lines = [normalize_line(line) for line in splitlines]
    
    if len(splitlines) == 1:
        # Only one line found, use it as line1 and set line2, line3 as Trash
        # Normalize the line before returning
        normalized = normalize_line(splitlines[0])
        return normalized, "Trash", "Trash"
    
    if len(splitlines) == 2:
        # Normalize both lines before returning, line3 is Trash
        # Check if lines look like potential lines (even if not exact matches)
        line1 = normalize_line(splitlines[0]) if splitlines[0] and splitlines[0].strip() else "Trash"
        line2 = normalize_line(splitlines[1]) if splitlines[1] and splitlines[1].strip() else "Trash"
        # Only return Trash if both are actually empty
        if line1 == "Trash" and line2 == "Trash":
            return "Trash", "Trash", "Trash"
        return line1, line2, "Trash"
    
    if len(splitlines) == 3:
        # Check for double lines first
        if matches_line_pattern(splitlines[0], double_lines_list):
            line1 = normalize_line(splitlines[0])
            line2 = normalize_line(splitlines[2])
            line3 = normalize_line(splitlines[1])  # Use the remaining line
            return line1, line2, line3
        elif matches_line_pattern(splitlines[1], double_lines_list):
            line1 = normalize_line(splitlines[0])
            line2 = normalize_line(splitlines[1])
            line3 = normalize_line(splitlines[2])  # Use the remaining line
            return line1, line2, line3
        
        # Check if any line matches single_lines patterns OR looks like a potential line
        # Find lines that match patterns or look like valid potential lines
        matched_indices = []
        for i in range(len(splitlines)):
            if matches_line_pattern(splitlines[i], single_lines_list):
                matched_indices.append(i)
        
        # Also check for stat lines (STR, DEX, INT, LUK, ALL, ATT) using regex
        # and other potential lines (BD, IED, etc.) using fuzzy matching
        for i in range(len(splitlines)):
            if i not in matched_indices:
                line = splitlines[i]
                normalized = normalize_line(line)
                # Check if it looks like a stat line (STR, DEX, INT, LUK, ALL, ATT)
                if re.search(r'(STR|DEX|INT|LUK|All\s+Stats?|ATT|Attack\s+Power)\s*:?\s*\+?\d+%', line, re.IGNORECASE):
                    matched_indices.append(i)
                # Check if it looks like Boss Damage
                elif re.search(r'Boss\s+Damage\s*:?\s*\+?\d+%', line, re.IGNORECASE):
                    matched_indices.append(i)
                # Check if it looks like IED (Ignore Defense) - exclude "chance to ignore" lines
                elif (re.search(r'Ign[aoe]r[ae]\s+Defense\s*:?\s*\+?\d+%', line, re.IGNORECASE) or 
                      re.search(r'Ign[aoe]r[ae]Defense\s*:?\s*\+?\d+%', line, re.IGNORECASE) or
                      re.search(r'Attacks\s+ignore\s+\d+%\s+Monster', line, re.IGNORECASE)) and \
                     not re.search(r'chance\s+to\s+ignore', line, re.IGNORECASE):
                    matched_indices.append(i)
                # Check if it looks like Critical Damage
                elif re.search(r'Critical\s+Damage\s*:?\s*\+?\d+%', line, re.IGNORECASE):
                    matched_indices.append(i)
                # Check if it looks like Item Drop Rate
                elif re.search(r'(Item|tem)\s+Drop\s+Rate\s*:?\s*\+?\d+%', line, re.IGNORECASE):
                    matched_indices.append(i)
                # Check if it looks like Magic ATT
                elif re.search(r'Magic\s+ATT\s*:?\s*\+?\d+%', line, re.IGNORECASE):
                    matched_indices.append(i)
        
        # If we found at least one matching line, use up to 3 lines
        if len(matched_indices) >= 1:
            # Use first match as line1
            line1_idx = matched_indices[0]
            line1 = normalize_line(splitlines[line1_idx])
            
            # For line2, prefer another matched line, otherwise use the next line
            if len(matched_indices) >= 2:
                line2_idx = matched_indices[1]
            else:
                # Use the line after line1, or before if line1 is last
                line2_idx = (line1_idx + 1) % len(splitlines)
            line2 = normalize_line(splitlines[line2_idx])
            
            # For line3, prefer another matched line, otherwise use the next available line
            if len(matched_indices) >= 3:
                line3_idx = matched_indices[2]
            elif len(splitlines) == 3:
                # If we have exactly 3 lines, use the remaining one
                used_indices = {line1_idx, line2_idx}
                line3_idx = next(i for i in range(3) if i not in used_indices)
            else:
                line3_idx = (line2_idx + 1) % len(splitlines) if len(splitlines) > 2 else line2_idx
            
            line3 = normalize_line(splitlines[line3_idx]) if line3_idx < len(splitlines) else "Trash"
            return line1, line2, line3
        else:
            # If no patterns matched, still return the lines (they might be valid but OCR variations)
            # Only return Trash if lines are clearly empty or invalid
            line1 = normalize_line(splitlines[0]) if splitlines[0] and splitlines[0].strip() else "Trash"
            line2 = normalize_line(splitlines[1]) if len(splitlines) > 1 and splitlines[1] and splitlines[1].strip() else "Trash"
            line3 = normalize_line(splitlines[2]) if len(splitlines) > 2 and splitlines[2] and splitlines[2].strip() else "Trash"
            # Only return all Trash if all lines are actually empty/invalid
            if line1 == "Trash" and line2 == "Trash" and line3 == "Trash":
                return "Trash", "Trash", "Trash"
            return line1, line2, line3

    if len(splitlines) > 3:
        if matches_line_pattern(splitlines[0], double_lines_dict['IED']) and len(splitlines) > 3 and matches_line_pattern(splitlines[3], double_lines_dict['IED']):
            line1 = normalize_line(splitlines[0])
            line2 = normalize_line(splitlines[3])
            line3 = normalize_line(splitlines[4]) if len(splitlines) > 4 else "Trash"
            return line1, line2, line3
        else:
            # Try to find up to 3 matching single lines or potential lines
            matched_indices = []
            for i in range(len(splitlines)):
                if matches_line_pattern(splitlines[i], single_lines_list):
                    matched_indices.append(i)
                    if len(matched_indices) >= 3:
                        break
            
            # Also check for stat lines and other potential lines using regex
            for i in range(len(splitlines)):
                if i not in matched_indices and len(matched_indices) < 3:
                    line = splitlines[i]
                    # Check if it looks like a stat line or potential line
                    if re.search(r'(STR|DEX|INT|LUK|All\s+Stats?|ATT|Attack\s+Power|Boss\s+Damage|Critical\s+Damage|(Item|tem)\s+Drop\s+Rate|Magic\s+ATT)\s*:?\s*\+?\d+%', line, re.IGNORECASE):
                        matched_indices.append(i)
                        if len(matched_indices) >= 3:
                            break
                    # Check for IED - exclude "chance to ignore" lines (damage reduction, not IED)
                    elif (re.search(r'Ign[aoe]r[ae]\s+Defense\s*:?\s*\+?\d+%', line, re.IGNORECASE) or 
                          re.search(r'Ign[aoe]r[ae]Defense\s*:?\s*\+?\d+%', line, re.IGNORECASE) or
                          re.search(r'Attacks\s+ignore\s+\d+%\s+Monster', line, re.IGNORECASE)) and \
                         not re.search(r'chance\s+to\s+ignore', line, re.IGNORECASE):
                        matched_indices.append(i)
                        if len(matched_indices) >= 3:
                            break
            
            if len(matched_indices) >= 1:
                line1 = normalize_line(splitlines[matched_indices[0]])
                line2 = normalize_line(splitlines[matched_indices[1]]) if len(matched_indices) >= 2 else normalize_line(splitlines[matched_indices[0] + 1] if matched_indices[0] + 1 < len(splitlines) else splitlines[0])
                line3 = normalize_line(splitlines[matched_indices[2]]) if len(matched_indices) >= 3 else "Trash"
                return line1, line2, line3
            else:
                # If no patterns matched, try to use first 3 lines if they look valid
                valid_lines = []
                for i in range(min(3, len(splitlines))):
                    if splitlines[i] and splitlines[i].strip():
                        valid_lines.append(normalize_line(splitlines[i]))
                if len(valid_lines) >= 2:
                    while len(valid_lines) < 3:
                        valid_lines.append("Trash")
                    return tuple(valid_lines[:3])
                return "Trash", "Trash", "Trash"
    
    # Fallback for any other case
    return "Trash", "Trash", "Trash"

def extract_stat_value(line, stat_type):
    """
    Extract numeric value from a stat line.
    Returns the stat value as an integer, or 0 if not found.
    """
    if stat_type not in stat_patterns:
        return 0
    
    # Special handling for ATT: exclude if "Magic" appears before ATT/Attack Power
    if stat_type == "ATT":
        # Check if "Magic" appears before ATT or Attack Power (with or without space)
        if (re.search(r'Magic\s*ATT', line, re.IGNORECASE) or 
            re.search(r'Magic\s*Attack\s*Power', line, re.IGNORECASE) or
            re.search(r'MagicAttackPower', line, re.IGNORECASE)):
            return 0  # This is Magic ATT, not regular ATT
    
    for pattern in stat_patterns[stat_type]:
        match = re.search(pattern, line, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return 0

def get_stat_from_line(line):
    """
    Determine which stat type a line contains and return (stat_type, value).
    Returns (None, 0) if no stat is found.
    Note: Check MATT before ATT to avoid matching Magic ATT as regular ATT.
    This function returns only the FIRST stat found in the line.
    For lines with multiple stats, use get_all_stats_from_line().
    """
    # Check MATT first to avoid matching it as ATT
    for stat_type in ["STR", "DEX", "INT", "LUK", "ALL", "MATT", "ATT", "BD", "IED"]:
        value = extract_stat_value(line, stat_type)
        if value > 0:
            return (stat_type, value)
    return (None, 0)

def get_all_stats_from_line(line):
    """
    Extract all stats from a line (handles comma-separated stats).
    Returns a list of (stat_type, value) tuples.
    """
    if not line or line == "Trash":
        return []
    
    stats = []
    # Split by comma to handle multiple stats in one line
    parts = [part.strip() for part in line.split(',')]
    
    # Check each part for stats
    for part in parts:
        # Check MATT first to avoid matching it as ATT
        for stat_type in ["STR", "DEX", "INT", "LUK", "ALL", "MATT", "ATT", "BD", "IED"]:
            value = extract_stat_value(part, stat_type)
            if value > 0:
                stats.append((stat_type, value))
                break  # Only count each part once (first matching stat)
    
    return stats

def process_lines(window_name=None, debug=False, crop_region=None, test_image_path=None, auto_detect_crop=False, cube_type="Glowing"):
    try:
        lines = get_lines(window_name, debug=debug, crop_region=crop_region, test_image_path=test_image_path, auto_detect_crop=auto_detect_crop, cube_type=cube_type)
        splitlines = split_lines(lines)
        if debug:
            print(f"[DEBUG] Split lines: {splitlines}")
        potential_lines = set_lines(splitlines)
        if debug:
            print(f"[DEBUG] Processed lines: {potential_lines}")
            print(f"[DEBUG] Normalized lines: {[normalize_line(line) for line in splitlines] if splitlines else []}")
            if splitlines:
                for i, line in enumerate(splitlines):
                    matches = matches_line_pattern(line, single_lines_list)
                    print(f"[DEBUG] Line {i} '{line}' -> normalized: '{normalize_line(line)}', matches: {matches}")
        
        # Ensure we always return a tuple of 3 strings
        if potential_lines is None:
            return "Trash", "Trash", "Trash"
        if not isinstance(potential_lines, tuple):
            return "Trash", "Trash", "Trash"
        if len(potential_lines) == 2:
            # Convert 2-tuple to 3-tuple by adding "Trash" as line3
            return potential_lines[0], potential_lines[1], "Trash"
        if len(potential_lines) >= 3:
            return potential_lines[0], potential_lines[1], potential_lines[2]
        return "Trash", "Trash", "Trash"
    except Exception as e:
        print(f"Error processing lines: {e}")
        import traceback
        traceback.print_exc()
        return "Trash", "Trash"

#print(process_lines())
#print(process_lines())

