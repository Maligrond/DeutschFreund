
from datetime import datetime, timedelta, timezone

def calculate_next_review(quality: int, interval: float, ease_factor: float) -> dict:
    """
    Calculates next review interval using SuperMemo-2 (SM-2) algorithm.
    
    Args:
        quality: 0-5 rating (we map: 1=Again(0), 2=Hard(3), 3=Good(4), 4=Easy(5))
                 Wait, actually mapping:
                 1 (Again) -> 0 (Complete blackout)
                 2 (Hard)  -> 3 (Recall with difficulty)
                 3 (Good)  -> 4 (Hesitation)
                 4 (Easy)  -> 5 (Perfect)
                 
        interval: Current interval in days
        ease_factor: Current ease factor (min 1.3)
        
    Returns:
        dict: {
            "interval": float,
            "ease_factor": float,
            "next_review": datetime
        }
    """
    
    # Map frontend 1-4 buttons to SM-2 0-5 scale
    # Button 1 "Again" -> Quality 0
    # Button 2 "Hard"  -> Quality 3
    # Button 3 "Good"  -> Quality 4
    # Button 4 "Easy"  -> Quality 5
    
    sm_quality = 0
    if quality == 1: sm_quality = 0
    elif quality == 2: sm_quality = 3
    elif quality == 3: sm_quality = 4
    elif quality == 4: sm_quality = 5
    
    new_interval = 0.0
    new_ease_factor = ease_factor
    
    if sm_quality >= 3:
        # Correct response
        if interval == 0:
            new_interval = 1.0
        elif interval == 1.0:
            new_interval = 6.0
        else:
            new_interval = interval * ease_factor
            
        # Update ease factor
        # EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        new_ease_factor = ease_factor + (0.1 - (5 - sm_quality) * (0.08 + (5 - sm_quality) * 0.02))
    else:
        # Incorrect response
        new_interval = 1.0
        # Ease factor doesn't change on failure in standard SM-2, but we keep it same
        # Optionally could decrease it
    
    if new_ease_factor < 1.3:
        new_ease_factor = 1.3
        
    next_review_date = datetime.now(timezone.utc) + timedelta(days=new_interval)
    
    return {
        "interval": round(new_interval, 2),
        "ease_factor": round(new_ease_factor, 2),
        "next_review": next_review_date
    }
