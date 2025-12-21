from typing import Dict, Any, Optional

# XP Requirements to reach the NEXT level
LEVEL_THRESHOLDS = {
    "Новичок": 0,
    "Энтузиаст": 1000,
    "Собеседник": 3000,
    "Знаток": 7000,
    "Мастер": 15000,
    "Легенда": 30000
}

LEVEL_ORDER = [
    "Новичок", 
    "Энтузиаст", 
    "Собеседник", 
    "Знаток", 
    "Мастер", 
    "Легенда"
]

def calculate_user_progress(total_xp: int) -> Dict[str, Any]:
    """
    Calculate user's level progress based on total XP.
    """
    current_level = LEVEL_ORDER[0]
    next_level = LEVEL_ORDER[1]
    level_xp_start = 0
    level_xp_end = LEVEL_THRESHOLDS[next_level]
    
    # Determine current level based on XP
    for i, level in enumerate(LEVEL_ORDER):
        threshold = LEVEL_THRESHOLDS[level]
        if total_xp >= threshold:
            current_level = level
            level_xp_start = threshold
            
            # Set next level info
            if i + 1 < len(LEVEL_ORDER):
                next_level = LEVEL_ORDER[i + 1]
                level_xp_end = LEVEL_THRESHOLDS[next_level]
            else:
                # Max level reached
                next_level = None
                level_xp_end = None
        else:
            break
            
    # Calculate progress percentage
    if level_xp_end is not None:
        xp_in_level = total_xp - level_xp_start
        level_range = level_xp_end - level_xp_start
        progress_percent = int((xp_in_level / level_range) * 100)
        progress_percent = min(100, max(0, progress_percent)) # Clamp 0-100
        xp_needed = level_xp_end - total_xp
    else:
        # Max level
        progress_percent = 100
        xp_needed = 0
        
    return {
        "current_level": current_level,
        "next_level": next_level,
        "level_xp_start": level_xp_start,
        "level_xp_end": level_xp_end,
        "progress_percent": progress_percent,
        "xp_needed": xp_needed
    }
