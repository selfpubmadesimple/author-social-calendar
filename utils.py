from datetime import date, timedelta
import pandas as pd

def build_date_series(start_date: date, days: int = 30, cadence: str = "daily"):
    """
    Build a series of dates based on the specified cadence.
    
    Args:
        start_date: Starting date
        days: Number of dates to generate
        cadence: "daily", "weekdays", or "3x_week"
        
    Returns:
        List of date objects
    """
    dates = []
    current_date = start_date
    
    while len(dates) < days:
        # For weekdays cadence, skip weekends (Saturday=5, Sunday=6)
        if cadence == "weekdays" and current_date.weekday() >= 5:
            current_date += timedelta(days=1)
            continue
        
        # For 3x/week cadence, only post on Monday (0), Wednesday (2), Friday (4)
        if cadence == "3x_week" and current_date.weekday() not in [0, 2, 4]:
            current_date += timedelta(days=1)
            continue
            
        dates.append(current_date)
        current_date += timedelta(days=1)
    
    return dates

def posts_to_dataframe(posts, dates):
    """
    Convert posts and dates into a pandas DataFrame.
    
    Args:
        posts: List of post dictionaries
        dates: List of date objects
        
    Returns:
        pandas DataFrame with posts data
    """
    rows = []
    
    for i, post in enumerate(posts):
        # Ensure we don't exceed the number of dates
        if i >= len(dates):
            break
            
        rows.append({
            "Date": dates[i].isoformat(),
            "Hook": post.get("hook", ""),
            "Caption": post.get("caption", ""),
            "Hashtags": post.get("hashtags", ""),
            "Image Idea": post.get("image_idea", ""),
            "Theme": post.get("theme", ""),
            "CTA": post.get("cta", ""),
        })
    
    return pd.DataFrame(rows)
