from translate_ocr_results import process_lines, get_stat_from_line, get_all_stats_from_line, extract_stat_value, get_potlines, matches_line_pattern
from macro_controls import time_to_start , click, press_reset_spacebar
import keyboard
import time
import threading
#single_lines_dict = {"BD":['Boss Damage: +30%', 'Boss Damage: +35%', 'Boss Damage: +40%', 'Boss Damage: +45%', 'Boss Damage: +50%'],"IA":['Item Acquisition Rate: +12%','Item Acquisition Rate: +10%','tem Acquisition Rate: +12%','tem Acquisition Rate: +10%'],"CD":['Critical Damage: +6%', 'Critical Damage: +3%'],"ATT":['ATT: +9%','ATT: +6%'],"MATT":['Magic ATT: +6%','Magic ATT: +9%']}
single_lines_dict = {"BD":['Boss Damage: +35%', 'Boss Damage: +40%', 'Boss Damage: +45%', 'Boss Damage: +50%'],"IA":['Item Acquisition Rate: +12%','Item Acquisition Rate: +10%','tem Acquisition Rate: +12%','tem Acquisition Rate: +10%'],"CD":['Critical Damage: +6%', 'Critical Damage: +3%'],"ATT":['ATT: +3%','ATT: +4%','ATT: +6%','ATT: +7%','ATT: +9%','ATT: +10%', 'Attack Power: +3%', 'Attack Power: +4%', 'Attack Power: +6%', 'Attack Power: +7%', 'Attack Power: +9%', 'Attack Power: +10%', 'Attack Power +3%', 'Attack Power +4%', 'Attack Power +6%', 'Attack Power +7%', 'Attack Power +9%', 'Attack Power +10%'],"MATT":['Magic ATT: +6%','Magic ATT: +9%']}
double_lines_dict = {"IED":['Attacks ignore 30% Monster', 'Attacks ignore 35% Monster', 'Attacks ignore 40% Monster', 'Attacks ignore 45% Monster', 'Attacks ignore 50% Monster'],'Drop':['Increases Item Drop Rate by a'],'MnD':['Increases tem and Meso Drop']}

# Default configuration - will be overridden by GUI
default_config = {
    "window_name": "Maplestory",  # Default window name
    "crop_region": None,  # Crop region as (x, y, width, height) percentages (0.0-1.0) or pixels
                           # Example: (0.35, 0.45, 0.3, 0.25) = center region
                           # Set to None to use full window
    "cube_type": "Glowing",  # "Glowing" or "Bright"
    "STRcheck": False,
    "DEXcheck": False,
    "INTcheck": False,
    "LUKcheck": False,
    "ALLcheck": False,
    "ATTcheck": False,
    "MATTcheck": False,
    "statThreshold": 21,
    "stopAtStatThreshold": False,
    "flexible_roll_check": {
        "enabled": False,
        "stat_types": [],  # List of stat types: ["BD", "ATT", "MATT", "IED", "CD", "IA", "MESO"]
        "required_count": 2  # Number of matching lines required (1, 2, or 3)
    },
    "ocr_callback": None  # Callback function to update OCR results in GUI
}

# Global config - will be set by GUI
config = default_config.copy()

# Global stop event for immediate bot stopping
bot_stop_event = threading.Event()


class potential:
    line1=None
    line2=None
    line3=None
    stop_bot = False
    last_three_rolls = []  # Track last 3 roll results to detect when cubes are used up
    
    def _send_ocr_result(self, text):
        """Send OCR result to GUI callback if available"""
        ocr_callback = config.get("ocr_callback")
        if ocr_callback:
            try:
                ocr_callback(text)
            except Exception as e:
                # Silently fail if callback has issues
                pass

    def get_lines(self):
        window_name = config.get("window_name", "Maplestory")
        crop_region = config.get("crop_region", None)
        test_image_path = config.get("test_image_path", None)
        auto_detect_crop = config.get("auto_detect_crop", False)
        cube_type = config.get("cube_type", "Glowing")
        lines = process_lines(window_name, debug=False, crop_region=crop_region, test_image_path=test_image_path, auto_detect_crop=auto_detect_crop, cube_type=cube_type)
        self.line1 = lines[0]
        self.line2 = lines[1]
        self.line3 = lines[2] if len(lines) > 2 else "Trash"
    
    def get_stat_values(self):
        """
        Extract stat values from all lines (up to 3) and return a dictionary.
        ALL stats are added to STR, DEX, INT, and LUK as per reference logic.
        """
        stats = {"STR": 0, "DEX": 0, "INT": 0, "LUK": 0, "ALL": 0, "ATT": 0, "MATT": 0, "BD": 0, "CD": 0, "IED": 0}
        
        # Get stats from all lines
        lines_to_process = [self.line1, self.line2]
        if self.line3 and self.line3 != "Trash":
            lines_to_process.append(self.line3)
        
        for line in lines_to_process:
            if line and line != "Trash":
                # Extract all stats from the line (handles comma-separated stats)
                line_stats = get_all_stats_from_line(line)
                for stat_type, stat_value in line_stats:
                    if stat_type == "ALL":
                        stats["ALL"] += stat_value
                    elif stat_type == "ATT":
                        stats["ATT"] += stat_value
                    elif stat_type == "MATT":
                        stats["MATT"] += stat_value
                    elif stat_type == "BD":
                        stats["BD"] += stat_value
                    elif stat_type == "CD":
                        stats["CD"] += stat_value
                    elif stat_type == "IED":
                        stats["IED"] += stat_value
                    else:
                        stats[stat_type] += stat_value
        
        # Apply ALL stats to all four main stats (as per reference logic)
        all_value = stats["ALL"]
        if all_value > 0:
            stats["STR"] += all_value
            stats["DEX"] += all_value
            stats["INT"] += all_value
            stats["LUK"] += all_value
        
        return stats
    
    def _normalize_lines_for_comparison(self):
        """
        Normalize lines for comparison by removing OCR variations.
        Removes colons, normalizes spacing, handles case differences, fixes common OCR errors.
        Returns tuple of normalized (line1, line2, line3)
        """
        import re
        
        def normalize(line):
            if not line or line == "Trash":
                return "Trash"
            
            # Convert to uppercase for case-insensitive comparison
            line = line.upper()
            
            # Remove colons (DEX:+12% vs DEX+12%)
            line = re.sub(r':\s*', '', line)
            
            # Normalize spacing around + and %
            line = re.sub(r'\s*\+\s*', '+', line)
            line = re.sub(r'\s*%\s*', '%', line)
            
            # Fix common OCR errors that don't affect meaning
            # "DAMAGE" vs "DAMAGE" - normalize common misspellings
            line = re.sub(r'DAMAU?E', 'DAMAGE', line)  # "DAMAGE" or "DAMAGE" -> "DAMAGE"
            line = re.sub(r'EFFCIENCY', 'EFFICIENCY', line)  # "EFFCIENCY" -> "EFFICIENCY"
            line = re.sub(r'CHANCETO', 'CHANCE TO', line)  # Normalize spacing
            line = re.sub(r'REFLECT', 'REFLECT', line)  # Keep as is
            line = re.sub(r'HPRECOVERY', 'HP RECOVERY', line)  # Normalize spacing
            line = re.sub(r'ITEMSAND', 'ITEMS AND', line)  # Normalize spacing
            line = re.sub(r'SKILLS', 'SKILLS', line)  # Keep as is
            
            # Remove extra whitespace
            line = ' '.join(line.split())
            
            # Remove any remaining single-character noise at start
            line = re.sub(r'^[^A-Z0-9]\s*', '', line)
            
            return line
        
        return (normalize(self.line1), normalize(self.line2), normalize(self.line3))
    
    def _is_garbage_ocr(self, line):
        """
        Check if a line is garbage OCR that should be ignored.
        Returns True if the line is garbage, False if it contains valid stats.
        
        Based on user-provided examples, garbage patterns include:
        - Damage reduction chance lines: "6%chancetoignare20%damagewhenattacked"
        - Standalone "Damage" without context: "Damage+9%"
        - Stat lines without %: "MagicATT+32", "AttackPower+32" (correct OCR, but unwanted format)
        - "CriticalRate" (not "Critical Damage")
        - Lines with only chance text
        
        Note: Double %% like "BossDamage+3%%" is actually "BossDamage+35%" where OCR misread "5" as "%".
        This is a valid OCR error, not garbage - the stat patterns handle it by allowing %+ (one or more %).
        
        Note: Lines like "MagicATT+32" without % are correct OCR readings (the number 32 is exact),
        but they don't match our stat patterns (which require %), so they don't extract stats and are filtered out.
        """
        if not line or line == "Trash":
            return True
        
        import re
        
        # Check for damage reduction chance lines (these are not stats)
        # Patterns like "6%chancetoignare20%damagewhenattacked", "10%chancetoignare40%damagewhenattackec"
        if re.search(r'chancetoignare.*damagewhenattacked', line, re.IGNORECASE) or \
           re.search(r'%chancetoignare.*damagewhenattacked', line, re.IGNORECASE) or \
           re.search(r'chancetoignare.*damagewhenattackec', line, re.IGNORECASE):
            return True  # Damage reduction chance, not a stat
        
        # Check for standalone "Damage" without any stat context (garbage)
        # This matches "Damage+9%" or "Damage+12%" but NOT "Boss Damage+40%" or "Critical Damage+6%"
        # Must check that it's at start of line or after comma, and not preceded by a stat word
        if re.search(r'(^|,\s*)Damage\s*\+?\d+%', line, re.IGNORECASE) or \
           re.search(r'(^|,\s*)Damage\s*\+?\d+$', line, re.IGNORECASE):
            # Make sure it's not "Boss Damage" or "Critical Damage" - check for preceding words
            if not re.search(r'(Boss|Critical)\s+Damage', line, re.IGNORECASE):
                return True  # Just "Damage" without context, garbage
        
        # Note: Double %% like "BossDamage+3%%" is actually valid OCR error where "35%" is misread as "3%%"
        # (the "5" is read as "%"), so we don't mark it as garbage - the stat extraction will handle it
        
        # Check for stat lines without % at the end (like "MagicATT+32", "AttackPower+32")
        # These are correct OCR readings, but they don't match our stat patterns (which require %),
        # so they don't extract stats and should be classified as garbage/unwanted
        # Check if line ends with stat+number (no %) or if there's a stat+number pattern followed by comma/end without %
        if re.search(r'(MagicATT|AttackPower|MagicAttackPower|AitackPower)\+?\d+($|,)', line, re.IGNORECASE):
            # Stat line without % - correct OCR but unwanted format, classified as garbage
            return True
        
        # Check for "CriticalRate" which is NOT "Critical Damage" (should be CD, not "CriticalRate")
        # This is a different stat that shouldn't be recognized
        if re.search(r'CriticalRate\s*\+?\d+', line, re.IGNORECASE):
            return True  # "Critical Rate" is not "Critical Damage", likely OCR error
        
        # Check if line only contains chance text and no recognizable stats
        # Lines like "%chancetoignare20%damagewhenattacked" or "10%chancetoignare40%damagewhenattackec"
        # or starting with %chanceto
        if re.search(r'^\d*%?chancetoignare', line, re.IGNORECASE) or \
           re.search(r'^%chancetoignare', line, re.IGNORECASE) or \
           re.search(r'^%chancetoIgnare', line, re.IGNORECASE):
            return True  # Only chance text, no stats
        
        return False
    
    def _has_valid_stats_in_roll(self, stats, original_lines):
        """
        Check if a roll has valid stats (not garbage OCR).
        Returns True if at least one valid stat is extracted.
        
        A roll is considered valid if it extracts at least one stat (sum > 0).
        Garbage lines (like chance text, standalone Damage) don't extract stats, so they're automatically filtered.
        
        Args:
            stats: Dictionary of stat values
            original_lines: Tuple of (line1, line2, line3) original lines (not normalized) - kept for compatibility
        """
        # Check if stats are extracted (at least one non-zero stat)
        # If we have stats extracted, at least one line must be valid
        # Garbage lines (like "6%chancetoignare20%damagewhenattacked") don't extract any stats
        has_stats = sum(stats.values()) > 0
        
        return has_stats
    
    def get_total_stats_string(self):
        """
        Format the total stats as a string for display.
        Returns a string like "STR: 9, DEX: 9, ATT: 6, MATT: 9, BD: 40, IED: 35" or empty string if no stats.
        """
        stats = self.get_stat_values()
        stat_parts = []
        
        # Add main stats (STR, DEX, INT, LUK, ATT, MATT) if they have values
        for stat_type in ["STR", "DEX", "INT", "LUK", "ATT", "MATT"]:
            if stats.get(stat_type, 0) > 0:
                stat_parts.append(f"{stat_type}: {stats[stat_type]}")
        
        # Add BD (Boss Damage) if it exists
        if stats.get("BD", 0) > 0:
            stat_parts.append(f"BD: {stats['BD']}")
        
        # Add CD (Critical Damage) if it exists
        if stats.get("CD", 0) > 0:
            stat_parts.append(f"CD: {stats['CD']}")
        
        # Add IED (Ignore Defense) if it exists
        if stats.get("IED", 0) > 0:
            stat_parts.append(f"IED: {stats['IED']}")
        
        # Add ALL stat separately if it exists
        if stats.get("ALL", 0) > 0:
            stat_parts.append(f"ALL: {stats['ALL']}")
        
        if stat_parts:
            return ", ".join(stat_parts)
        return ""
    
    def get_highest_stat(self):
        """
        Calculate the highest stat value, considering only enabled stat checks.
        Returns the maximum stat value among checked stats.
        """
        stats = self.get_stat_values()
        statcalc = {}
        
        if config["STRcheck"]:
            statcalc['STR'] = stats['STR']
        if config["DEXcheck"]:
            statcalc['DEX'] = stats['DEX']
        if config["INTcheck"]:
            statcalc['INT'] = stats['INT']
        if config["LUKcheck"]:
            statcalc['LUK'] = stats['LUK']
        if config["ALLcheck"]:
            statcalc['ALL'] = stats['ALL']
        if config["ATTcheck"]:
            statcalc['ATT'] = stats['ATT']
        if config["MATTcheck"]:
            statcalc['MATT'] = stats['MATT']
        
        if not statcalc:
            return 0
        
        return max(statcalc.values())
    
    def check_roll_stat_threshold(self):
        """
        Check if the highest stat meets the threshold requirement.
        Returns True if threshold is met, False otherwise.
        """
        if not config["stopAtStatThreshold"]:
            return False
        
        highest_stat = self.get_highest_stat()
        if highest_stat >= config["statThreshold"]:
            self.stop_bot = True
            stats = self.get_stat_values()
            # Format output with 3 lines and total stats
            lines_str = f"{self.line1}, {self.line2}"
            if self.line3 and self.line3 != "Trash":
                lines_str += f", {self.line3}"
            total_stats = self.get_total_stats_string()
            result_text = f"{lines_str}    PASS (Stats: {total_stats}, Highest: {highest_stat}, Threshold: {config['statThreshold']})"
            self._send_ocr_result(result_text)
            return True
        return False

    def check_roll_2L_BD(self):
        if self.line1 in single_lines_dict["BD"] and self.line2 in single_lines_dict['BD']:
            self.stop_bot = True
            result_text = f"{self.line1}, {self.line2}    PASS"
            self._send_ocr_result(result_text)
            return True
        else:
            return False

    def check_roll_2L_IA(self):
        if self.line1 in single_lines_dict['IA'] and self.line2 in single_lines_dict['IA']:
            self.stop_bot = True
            lines_str = f"{self.line1}, {self.line2}"
            if self.line3 and self.line3 != "Trash":
                lines_str += f", {self.line3}"
            total_stats = self.get_total_stats_string()
            result_text = f"{lines_str}    PASS (Stats: {total_stats})"
            self._send_ocr_result(result_text)
            return True
        else:
            return False

    def check_roll_2L_CD_6(self):
        if self.line1 == single_lines_dict['CD'][0] and self.line2 == single_lines_dict['CD'][0]:
            self.stop_bot = True
            lines_str = f"{self.line1}, {self.line2}"
            if self.line3 and self.line3 != "Trash":
                lines_str += f", {self.line3}"
            total_stats = self.get_total_stats_string()
            result_text = f"{lines_str}    PASS (Stats: {total_stats})"
            self._send_ocr_result(result_text)
            return True
        else:
            return

    def check_roll_2L_ATT_18(self):
        """
        Check if there are 2 lines (or 2 instances) of ATT/Attack Power.
        Handles comma-separated stats in a single line.
        """
        att_count = 0
        lines_to_check = [self.line1, self.line2]
        if self.line3 and self.line3 != "Trash":
            lines_to_check.append(self.line3)
        
        # Check each line for ATT (handles comma-separated stats)
        for line in lines_to_check:
            if line and line != "Trash":
                # Split by comma to handle multiple stats in one line
                parts = [part.strip() for part in line.split(',')]
                for part in parts:
                    if self._has_attack_power(part):
                        att_count += 1
                        if att_count >= 2:
                            # Found 2 ATT instances, stop bot
                            self.stop_bot = True
                            lines_str = f"{self.line1}, {self.line2}"
                            if self.line3 and self.line3 != "Trash":
                                lines_str += f", {self.line3}"
                            total_stats = self.get_total_stats_string()
                            result_text = f"{lines_str}    PASS (2L ATT, Stats: {total_stats})"
                            self._send_ocr_result(result_text)
                            return True
        
        return False
    
    def check_roll_2L_ATT_15(self):
        if self.line1 in single_lines_dict['ATT'] and self.line2 in double_lines_dict.get('ATT', []):
            self.stop_bot = True
            lines_str = f"{self.line1}, {self.line2}"
            if self.line3 and self.line3 != "Trash":
                lines_str += f", {self.line3}"
            total_stats = self.get_total_stats_string()
            result_text = f"{lines_str}    PASS (Stats: {total_stats})"
            self._send_ocr_result(result_text)
            return True
        elif self.line2 in single_lines_dict['ATT'] and self.line1 in double_lines_dict.get('ATT', []):
            self.stop_bot = True
            lines_str = f"{self.line1}, {self.line2}"
            if self.line3 and self.line3 != "Trash":
                lines_str += f", {self.line3}"
            total_stats = self.get_total_stats_string()
            result_text = f"{lines_str}    PASS (Stats: {total_stats})"
            self._send_ocr_result(result_text)
            return True
        else:
            return False
    
    def check_roll_BD_IED(self):
        if self.line1 in single_lines_dict['BD'] and self.line2 in double_lines_dict['IED']:
            self.stop_bot = True
            lines_str = f"{self.line1}, {self.line2}"
            if self.line3 and self.line3 != "Trash":
                lines_str += f", {self.line3}"
            total_stats = self.get_total_stats_string()
            result_text = f"{lines_str}    PASS (Stats: {total_stats})"
            self._send_ocr_result(result_text)
            return True
        elif self.line2 in single_lines_dict['BD'] and self.line1 in double_lines_dict['IED']:
            self.stop_bot = True
            lines_str = f"{self.line1}, {self.line2}"
            if self.line3 and self.line3 != "Trash":
                lines_str += f", {self.line3}"
            total_stats = self.get_total_stats_string()
            result_text = f"{lines_str}    PASS (Stats: {total_stats})"
            self._send_ocr_result(result_text)
            return True
        else:
            return False
    
    def _has_boss_damage(self, line):
        """Check if line contains Boss Damage (handles both "Boss Damage" and "BossDamage")"""
        if not line or line == "Trash":
            return False
        import re
        # Check exact match first (most reliable)
        if line in single_lines_dict['BD']:
            return True
        # Use strict regex pattern matching (more reliable than fuzzy matching)
        # Only match if we see "Boss Damage" or "BossDamage" followed by a percentage
        return bool(re.search(r'Boss\s+Damage\s*:?\s*\+?\d+%', line, re.IGNORECASE) or
                   re.search(r'BossDamage\s*:?\s*\+?\d+%', line, re.IGNORECASE))
    
    def _has_attack_power(self, line):
        """Check if line contains Attack Power (ATT) - does NOT include Magic ATT"""
        if not line or line == "Trash":
            return False
        import re
        # CRITICAL: Check for Magic ATT FIRST and exclude it immediately (with or without space)
        # This must be done before any other checks to prevent false matches
        # Handle OCR error "Aitack" (t→i)
        if (re.search(r'Magic\s*ATT', line, re.IGNORECASE) or 
            re.search(r'Magic\s*A[ti]tack\s*Power', line, re.IGNORECASE) or
            re.search(r'MagicA[ti]tackPower', line, re.IGNORECASE)):
            return False  # Explicitly exclude Magic ATT (handles "Magic ATT", "MagicATT", "MagicAttackPower", "MagicAitackPower", etc.)
        
        # Check exact match or pattern match (only ATT, not MATT)
        # Note: matches_line_pattern might match Magic ATT, so we check Magic ATT first above
        if line in single_lines_dict['ATT']:
            return True
        
        # Check pattern match, but be careful - matches_line_pattern might match Magic ATT
        # So we verify it's not Magic ATT after matching
        if matches_line_pattern(line, single_lines_dict['ATT']):
            # Double-check it's not Magic ATT (in case matches_line_pattern matched it)
            # Handle OCR error "Aitack" (t→i)
            if not (re.search(r'Magic\s*ATT', line, re.IGNORECASE) or re.search(r'Magic\s*A[ti]tack\s*Power', line, re.IGNORECASE)):
                return True
        
        # Also check with regex for variations (exclude Magic ATT using negative lookbehind)
        # Match ATT or Attack Power (with or without space, handles OCR error "Aitack"), but NOT Magic ATT
        # Use negative lookbehind to ensure ATT is not preceded by "Magic " (with space)
        # For cases without space (MagicATT), we already checked above
        return bool(re.search(r'(?<!Magic\s)(ATT|A[ti]tack\s+Power|A[ti]tackPower)\s*:?\s*\+?\d+%', line, re.IGNORECASE))
    
    def _has_magic_att(self, line):
        """Check if line contains Magic ATT specifically"""
        if not line or line == "Trash":
            return False
        import re
        # Check exact match or pattern match
        if (line in single_lines_dict['MATT'] or 
                matches_line_pattern(line, single_lines_dict['MATT'])):
            return True
        # Also check with regex for variations (handles both "Magic ATT" and "MagicATT", and OCR error "Aitack")
        return bool(re.search(r'Magic\s*ATT\s*:?\s*\+?\d+%', line, re.IGNORECASE) or 
                   re.search(r'Magic\s*A[ti]tack\s*Power\s*:?\s*\+?\d+%', line, re.IGNORECASE) or
                   re.search(r'MagicA[ti]tackPower\s*:?\s*\+?\d+%', line, re.IGNORECASE))
    
    def _has_ignore_defense(self, line):
        """Check if line contains Ignore Defense (IED) - only actual IED stat lines, not damage reduction chance"""
        if not line or line == "Trash":
            return False
        import re
        # Use strict regex pattern matching - only match actual IED stat lines
        # Exclude "X% chance to ignore Y% damage" lines (those are damage reduction, not IED)
        ied_patterns = [
            r'Ign[aoe]r[ae]\s+Defense\s*:?\s*\+?\d+%',  # "Ignore Defense +35%" (handles OCR errors where 'o'→'a'/'e' and 'e'→'a'/'e', with space)
            r'Ign[aoe]r[ae]Defense\s*:?\s*\+?\d+%',  # "IgnareDefense+40%" (handles OCR errors where 'o'→'a'/'e' and 'e'→'a'/'e', no space)
            r'Attacks\s+ignore\s+\d+%\s+Monster(?:\s+Defense)?',  # "Attacks ignore 35% Monster" or "Attacks ignore 35% Monster Defense"
        ]
        for pattern in ied_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                # Double-check: exclude lines with "chance to ignore" (damage reduction, not IED)
                if not re.search(r'chance\s+to\s+ignore', line, re.IGNORECASE):
                    return True
        return False
    
    def _has_crit_damage(self, line):
        """Check if line contains Critical Damage (handles both "Critical Damage" and "CriticalDamage")"""
        if not line or line == "Trash":
            return False
        import re
        # Check exact match or pattern match
        if (line in single_lines_dict['CD'] or 
                matches_line_pattern(line, single_lines_dict['CD'])):
            return True
        # Also check with regex for variations (with or without space)
        return bool(re.search(r'Critical\s+Damage\s*:?\s*\+?\d+%', line, re.IGNORECASE) or
                   re.search(r'CriticalDamage\s*:?\s*\+?\d+%', line, re.IGNORECASE))
    
    def _has_item_drop_rate(self, line):
        """Check if line contains Item Drop Rate - gracefully handles OCR errors"""
        if not line or line == "Trash":
            return False
        import re
        # Check exact match or pattern match (same pattern as MATT, BD, IED)
        if (line in single_lines_dict['IA'] or 
                matches_line_pattern(line, single_lines_dict['IA'])):
            return True
        
        # Match "Item Drop Rate" with OCR error tolerance
        # Handles variations like: "Item Drop Rate +20%", "ltemDropRate+20%", "tem Dr0p Rat3", etc.
        # No % check to handle cases where % is misread by OCR
        # Spaces are optional to handle cases like "ltemDropRate"
        return bool(re.search(r'\b(Item|tem|Itern|ltem)\s*(Drop|Dr0p)\s*(Rate|Rat3)', line, re.IGNORECASE))
    
    def _has_meso_obtained(self, line):
        """Check if line contains Meso Obtained - gracefully handles OCR errors"""
        if not line or line == "Trash":
            return False
        import re
        # Check exact match or pattern match (same pattern as MATT, BD, IED)
        meso_dict = double_lines_dict.get('MnD', [])
        if (line in meso_dict or 
                matches_line_pattern(line, meso_dict)):
            return True
        
        # Match "Meso Obtained" with OCR error tolerance
        # Handles variations like: "Meso Obtained +20%", "MesosObtained+20%", "Mes0 Obtain3d", etc.
        # No % check to handle cases where % is misread by OCR
        # Spaces are optional to handle cases like "MesosObtained"
        return bool(re.search(r'\b(Meso|Mesos|Mes0|Mes\s+o)\s*(Obtained|Obtain3d)', line, re.IGNORECASE))
    
    def _line_matches_stat_type(self, line, stat_type):
        """Check if a line matches a given stat type"""
        stat_type_upper = stat_type.upper()
        if stat_type_upper == "BD" or stat_type_upper == "BOSS DAMAGE":
            return self._has_boss_damage(line)
        elif stat_type_upper == "ATT" or stat_type_upper == "ATTACK POWER":
            return self._has_attack_power(line)
        elif stat_type_upper == "MATT" or stat_type_upper == "MAGIC ATT":
            return self._has_magic_att(line)
        elif stat_type_upper == "IED" or stat_type_upper == "IGNORE DEFENSE":
            return self._has_ignore_defense(line)
        elif stat_type_upper == "CD" or stat_type_upper == "CRIT DAMAGE" or stat_type_upper == "CRITICAL DAMAGE":
            return self._has_crit_damage(line)
        elif stat_type_upper == "IA" or stat_type_upper == "ITEM DROP RATE" or stat_type_upper == "DROP RATE":
            return self._has_item_drop_rate(line)
        elif stat_type_upper == "MESO" or stat_type_upper == "MESO OBTAINED":
            return self._has_meso_obtained(line)
        return False
    
    def check_roll_flexible(self, stat_types, required_count):
        """
        Flexible roll check: stop if required_count lines match any of the selected stat types.
        
        Args:
            stat_types: List of stat types to check for (e.g., ["BD", "ATT", "MATT"])
            required_count: Number of matching lines required (1, 2, or 3)
        
        Returns:
            True if condition is met (bot should stop), False otherwise
        """
        if not stat_types or required_count < 1 or required_count > 3:
            return False
        
        lines_to_check = [self.line1, self.line2]
        if self.line3 and self.line3 != "Trash":
            lines_to_check.append(self.line3)
        
        matching_count = 0
        matched_lines = []
        
        # Check each line against all selected stat types
        # Handle comma-separated stats in a single line
        for line in lines_to_check:
            if line and line != "Trash":
                # Split by comma to handle multiple stats in one line
                parts = [part.strip() for part in line.split(',')]
                for part in parts:
                    for stat_type in stat_types:
                        if self._line_matches_stat_type(part, stat_type):
                            matching_count += 1
                            matched_lines.append((part, stat_type))
                            # Debug: log what matched (can be removed later)
                            print(f"[DEBUG] Stat matched {stat_type}: {repr(part)}")
                            break  # Count each stat only once
                    if matching_count >= required_count:
                        break  # Stop if we have enough matches
                if matching_count >= required_count:
                    break  # Stop checking lines if we have enough matches
        print("--------------------------------")
        
        # Stop if we have enough matching lines
        if matching_count >= required_count:
            self.stop_bot = True
            lines_str = f"{self.line1}, {self.line2}"
            if self.line3 and self.line3 != "Trash":
                lines_str += f", {self.line3}"
            total_stats = self.get_total_stats_string()
            stat_types_str = ", ".join(stat_types)
            result_text = f"{lines_str}    PASS ({required_count}L: {stat_types_str}, Stats: {total_stats})"
            self._send_ocr_result(result_text)
            return True
        
        return False
    
    def check_roll_BD_ATT_IED(self):
        """
        Check if all 3 lines contain Boss Damage, Attack Power (or MATK), and Ignore Defense
        in any combination across the 3 lines.
        """
        lines_to_check = [self.line1, self.line2]
        if self.line3 and self.line3 != "Trash":
            lines_to_check.append(self.line3)
        
        has_bd = False
        has_att = False
        has_ied = False
        
        # Check each line for the three stat types
        for line in lines_to_check:
            if line and line != "Trash":
                if self._has_boss_damage(line):
                    has_bd = True
                if self._has_attack_power(line):
                    has_att = True
                if self._has_ignore_defense(line):
                    has_ied = True
        
        # All three must be present
        if has_bd and has_att and has_ied:
            self.stop_bot = True
            lines_str = f"{self.line1}, {self.line2}"
            if self.line3 and self.line3 != "Trash":
                lines_str += f", {self.line3}"
            total_stats = self.get_total_stats_string()
            result_text = f"{lines_str}    PASS (BD + ATT/MATK + IED, Stats: {total_stats})"
            self._send_ocr_result(result_text)
            return True
        else:
            return False

    def check_roll_1L_IA(self):
        if self.line1 in single_lines_dict['IA'] or self.line2 in single_lines_dict['IA']:
            self.stop_bot = True
            lines_str = f"{self.line1}, {self.line2}"
            if self.line3 and self.line3 != "Trash":
                lines_str += f", {self.line3}"
            total_stats = self.get_total_stats_string()
            result_text = f"{lines_str}    PASS (Stats: {total_stats})"
            self._send_ocr_result(result_text)
            return True
        else:
            return False
    
    def check_roll_IA_DR(self):
        if self.line1 in single_lines_dict['IA'] and self.line2 in double_lines_dict.get('Drop', []):
            self.stop_bot=True
            lines_str = f"{self.line1}, {self.line2}"
            if self.line3 and self.line3 != "Trash":
                lines_str += f", {self.line3}"
            total_stats = self.get_total_stats_string()
            result_text = f"{lines_str}    PASS (Stats: {total_stats})"
            self._send_ocr_result(result_text)
            return True
        elif self.line2 in single_lines_dict['IA'] and self.line1 in double_lines_dict.get('Drop', []):
            self.stop_bot = True
            lines_str = f"{self.line1}, {self.line2}"
            if self.line3 and self.line3 != "Trash":
                lines_str += f", {self.line3}"
            total_stats = self.get_total_stats_string()
            result_text = f"{lines_str}    PASS (Stats: {total_stats})"
            self._send_ocr_result(result_text)
            return True

        else:
            return



    def startbot(self):
        # Reset stop event at start
        bot_stop_event.clear()
        
        # Reset roll tracking
        self.last_three_rolls = []
        
        # Clear cached potlines instance to ensure fresh start
        from translate_ocr_results import clear_potlines_cache
        clear_potlines_cache()
        
        # Check if current potential already satisfies threshold before starting
        self._send_ocr_result("Checking initial potential...")
        # No delay needed - get_lines() will take a fresh screenshot
        self.get_lines()  # Take a fresh screenshot and get current lines
        
        # Check if threshold is already met
        if config["stopAtStatThreshold"]:
            if self.check_roll_stat_threshold():
                self._send_ocr_result("Initial potential already meets threshold! Stopping bot.")
                return
        
        # Check all other conditions
        checks_passed = False
        
        # Flexible roll check
        if config.get("flexible_roll_check", {}).get("enabled", False):
            flex_config = config["flexible_roll_check"]
            stat_types = flex_config.get("stat_types", [])
            required_count = flex_config.get("required_count", 2)
            if self.check_roll_flexible(stat_types, required_count):
                checks_passed = True
        
        if checks_passed or self.stop_bot:
            print("Initial potential already satisfies conditions! Stopping bot.")
            return
        
        print("Initial potential does not meet requirements. Starting bot loop...")
        
        time_to_start(bot_stop_event)
        
        # Cache config values to avoid repeated lookups in loop
        window_name = config.get("window_name", "Maplestory")
        auto_detect_crop = config.get("auto_detect_crop", False)
        
        while self.stop_bot == False and keyboard.is_pressed('q') == False and not bot_stop_event.is_set():
            # Check stop event before each action
            if bot_stop_event.is_set():
                self._send_ocr_result("Bot stopped by user")
                break
            
            # FIRST: Get and check the CURRENT potential before resetting
            # This ensures we don't skip a good potential by resetting too early
            self.get_lines()
            
            # Check if cubes are used up (same stats 3 times in a row)
            # Compare based on extracted stats, not raw text, to handle OCR variations
            current_stats = self.get_stat_values()
            # Store original lines for garbage detection, and normalized lines for comparison
            original_lines = (self.line1, self.line2, self.line3)
            normalized_lines = self._normalize_lines_for_comparison()
            current_roll = (original_lines, normalized_lines, current_stats)
            
            self.last_three_rolls.append(current_roll)
            if len(self.last_three_rolls) > 3:
                self.last_three_rolls.pop(0)  # Keep only last 3
            
            # If we have 3 rolls and they're all the same, cubes are used up
            # Compare based on extracted stats, not raw text, to handle OCR variations
            if len(self.last_three_rolls) == 3:
                roll1_orig, roll1_norm, roll1_stats = self.last_three_rolls[0]
                roll2_orig, roll2_norm, roll2_stats = self.last_three_rolls[1]
                roll3_orig, roll3_norm, roll3_stats = self.last_three_rolls[2]
                
                # Check if all three rolls have valid stats (not garbage OCR)
                roll1_valid = self._has_valid_stats_in_roll(roll1_stats, roll1_orig)
                roll2_valid = self._has_valid_stats_in_roll(roll2_stats, roll2_orig)
                roll3_valid = self._has_valid_stats_in_roll(roll3_stats, roll3_orig)
                
                all_rolls_valid = roll1_valid and roll2_valid and roll3_valid
                
                # Only check for same stats if all three rolls have valid stats (not garbage)
                if all_rolls_valid:
                    # Check if stats are the same (primary check - most reliable)
                    stats_match = (roll1_stats == roll2_stats == roll3_stats)
                    
                    if stats_match:
                        # Same valid stats 3 times in a row - cubes are used up
                        self.stop_bot = True
                        lines_str = f"{self.line1}, {self.line2}"
                        if self.line3 and self.line3 != "Trash":
                            lines_str += f", {self.line3}"
                        result_text = f"{lines_str}    STOP (Cubes used up - same stats 3 times in a row)"
                        self._send_ocr_result(result_text)
                        print("Cubes used up - same stats detected 3 times in a row. Stopping bot.")
                        return
            
            # Stat threshold checking (if enabled)
            if config["stopAtStatThreshold"]:
                self.check_roll_stat_threshold()
            
            # Flexible roll check
            if config.get("flexible_roll_check", {}).get("enabled", False):
                flex_config = config["flexible_roll_check"]
                stat_types = flex_config.get("stat_types", [])
                required_count = flex_config.get("required_count", 2)
                self.check_roll_flexible(stat_types, required_count)
            
            # Check if we should stop (potential passed)
            if self.stop_bot:
                # Potential passed - stop immediately without resetting
                return
            
            # Potential did NOT pass - format output and reset for next iteration
            lines_str = f"{self.line1}, {self.line2}"
            if self.line3 and self.line3 != "Trash":
                lines_str += f", {self.line3}"
            total_stats = self.get_total_stats_string()
            result_text = f"{lines_str}    REJECT (Stats: {total_stats})"
            self._send_ocr_result(result_text)
            
            # Check stop event before resetting
            if bot_stop_event.is_set():
                self._send_ocr_result("Bot stopped by user")
                break
            
            # NOW reset to get a new potential for the next iteration
            press_reset_spacebar()
            
            # Check immediately after reset
            if bot_stop_event.is_set():
                self._send_ocr_result("Bot stopped by user")
                break
            
            # Wait for potential window to update after reset
            # Use shorter sleep intervals for more responsive stopping
            for _ in range(5):  # Break 0.5 seconds into 5 checks of 0.1 seconds
                if bot_stop_event.is_set():
                    print("Bot stopped by user")
                    break
                time.sleep(0.1)
            
            # Small delay before next iteration
            time.sleep(0.2)








def run_bot(bot_config=None):
    """Run the bot with the given configuration"""
    global config
    if bot_config:
        config = bot_config.copy()
    else:
        config = default_config.copy()
    
    # Reset stop event when starting
    bot_stop_event.clear()
    
    pot = potential()
    pot.startbot()

# Only auto-start if not imported as a module
if __name__ == "__main__":
    pot = potential()
    pot.startbot()
