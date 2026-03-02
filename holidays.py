from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import calendar

def get_holidays_for_month(start_date, num_days=30):
    """
    Get relevant US holidays and book-related observances for the given date range.
    Returns a list of holidays that fall within or near the posting period.
    """
    if isinstance(start_date, str):
        start_date = datetime.fromisoformat(start_date).date()
    
    end_date = start_date + relativedelta(days=num_days)
    year = start_date.year
    
    # Define major US holidays and book-related observances
    holidays = []
    
    # Comprehensive fixed date holidays and national observances
    fixed_holidays = {
        # January
        (1, 1): "New Year's Day",
        (1, 15): "National Hat Day",
        (1, 17): "Kid Inventors' Day",
        (1, 21): "National Hugging Day",
        (1, 24): "International Day of Education",
        (1, 28): "Data Privacy Day",
        
        # February
        (2, 2): "Groundhog Day",
        (2, 11): "International Day of Women and Girls in Science",
        (2, 14): "Valentine's Day",
        (2, 17): "Random Acts of Kindness Day",
        (2, 20): "World Day of Social Justice",
        (2, 27): "Tell a Fairy Tale Day",
        
        # March
        (3, 2): "Read Across America Day",
        (3, 3): "World Wildlife Day",
        (3, 8): "International Women's Day",
        (3, 14): "Pi Day",
        (3, 17): "St. Patrick's Day",
        (3, 20): "International Day of Happiness",
        (3, 21): "World Poetry Day",
        (3, 22): "World Water Day",
        (3, 27): "World Theatre Day",
        
        # April
        (4, 2): "International Children's Book Day",
        (4, 7): "World Health Day",
        (4, 11): "National Pet Day",
        (4, 22): "Earth Day",
        (4, 23): "World Book Day",
        (4, 25): "Take Our Daughters and Sons to Work Day",
        (4, 30): "National Honesty Day",
        
        # May
        (5, 1): "May Day",
        (5, 4): "Star Wars Day",
        (5, 5): "Cinco de Mayo",
        (5, 15): "International Day of Families",
        (5, 21): "World Day for Cultural Diversity",
        (5, 22): "International Day for Biological Diversity",
        
        # June
        (6, 1): "Global Day of Parents",
        (6, 5): "World Environment Day",
        (6, 8): "World Oceans Day",
        (6, 12): "World Day Against Child Labor",
        (6, 19): "Juneteenth",
        (6, 21): "International Day of Yoga / First Day of Summer",
        
        # July
        (7, 4): "Independence Day",
        (7, 11): "World Population Day",
        (7, 30): "International Day of Friendship",
        
        # August
        (8, 9): "International Day of the World's Indigenous Peoples",
        (8, 12): "International Youth Day",
        (8, 13): "International Left-Handers Day",
        (8, 19): "World Humanitarian Day",
        (8, 26): "National Dog Day",
        
        # September
        (9, 8): "International Literacy Day",
        (9, 15): "International Day of Democracy",
        (9, 16): "International Day for the Preservation of the Ozone Layer",
        (9, 21): "International Day of Peace",
        (9, 23): "First Day of Autumn",
        (9, 27): "World Tourism Day",
        (9, 28): "World Rabies Day",
        
        # October
        (10, 1): "International Day of Older Persons",
        (10, 2): "International Day of Non-Violence",
        (10, 5): "World Teachers' Day",
        (10, 10): "World Mental Health Day",
        (10, 11): "International Day of the Girl Child",
        (10, 16): "World Food Day",
        (10, 24): "United Nations Day",
        (10, 31): "Halloween",
        
        # November
        (11, 1): "World Vegan Day",
        (11, 5): "National Love Your Red Hair Day",
        (11, 11): "Veterans Day",
        (11, 13): "World Kindness Day",
        (11, 16): "International Day for Tolerance",
        (11, 19): "International Men's Day",
        (11, 20): "Universal Children's Day",
        (11, 25): "International Day for the Elimination of Violence Against Women",
        
        # December
        (12, 1): "World AIDS Day",
        (12, 3): "International Day of Persons with Disabilities",
        (12, 5): "International Volunteer Day",
        (12, 10): "Human Rights Day",
        (12, 11): "International Mountain Day",
        (12, 21): "First Day of Winter",
        (12, 25): "Christmas Day",
        (12, 31): "New Year's Eve"
    }
    
    # Add fixed holidays that fall in range
    for month, day in fixed_holidays:
        holiday_date = date(year, month, day)
        if start_date <= holiday_date <= end_date:
            holidays.append({
                "date": holiday_date,
                "name": fixed_holidays.get((month, day), ""),
                "type": "holiday"
            })
    
    # Variable holidays (calculated)
    variable_holidays = []
    
    # Martin Luther King Jr. Day (3rd Monday in January)
    mlk_day = get_nth_weekday(year, 1, 0, 3)  # 3rd Monday
    variable_holidays.append((mlk_day, "Martin Luther King Jr. Day"))
    
    # Presidents Day (3rd Monday in February)  
    presidents_day = get_nth_weekday(year, 2, 0, 3)  # 3rd Monday
    variable_holidays.append((presidents_day, "Presidents Day"))
    
    # Mother's Day (2nd Sunday in May)
    mothers_day = get_nth_weekday(year, 5, 6, 2)  # 2nd Sunday
    variable_holidays.append((mothers_day, "Mother's Day"))
    
    # Memorial Day (last Monday in May)
    memorial_day = get_last_weekday(year, 5, 0)  # Last Monday
    variable_holidays.append((memorial_day, "Memorial Day"))
    
    # Father's Day (3rd Sunday in June)
    fathers_day = get_nth_weekday(year, 6, 6, 3)  # 3rd Sunday
    variable_holidays.append((fathers_day, "Father's Day"))
    
    # Labor Day (1st Monday in September)
    labor_day = get_nth_weekday(year, 9, 0, 1)  # 1st Monday
    variable_holidays.append((labor_day, "Labor Day"))
    
    # Columbus Day (2nd Monday in October)
    columbus_day = get_nth_weekday(year, 10, 0, 2)  # 2nd Monday
    variable_holidays.append((columbus_day, "Columbus Day"))
    
    # Thanksgiving (4th Thursday in November)
    thanksgiving = get_nth_weekday(year, 11, 3, 4)  # 4th Thursday
    variable_holidays.append((thanksgiving, "Thanksgiving"))
    
    # Add variable holidays that fall in range
    for holiday_date, name in variable_holidays:
        if start_date <= holiday_date <= end_date:
            holidays.append({
                "date": holiday_date,
                "name": name,
                "type": "holiday"
            })
    
    # Add awareness months and weeks
    awareness_periods = []
    
    # January - National Mentoring Month
    if start_date.month <= 1 <= end_date.month:
        awareness_periods.append({
            "date": date(year, 1, 1),
            "name": "National Mentoring Month",
            "type": "awareness"
        })
    
    # February - Black History Month
    if start_date.month <= 2 <= end_date.month:
        awareness_periods.append({
            "date": date(year, 2, 1),
            "name": "Black History Month",
            "type": "awareness"
        })
    
    # March - National Reading Month / Women's History Month
    if start_date.month <= 3 <= end_date.month:
        awareness_periods.append({
            "date": date(year, 3, 1),
            "name": "National Reading Month",
            "type": "educational"
        })
        awareness_periods.append({
            "date": date(year, 3, 1),
            "name": "Women's History Month",
            "type": "awareness"
        })
    
    # April - National Poetry Month / Autism Awareness Month
    if start_date.month <= 4 <= end_date.month:
        awareness_periods.append({
            "date": date(year, 4, 1),
            "name": "National Poetry Month",
            "type": "educational"
        })
        awareness_periods.append({
            "date": date(year, 4, 1),
            "name": "Autism Awareness Month",
            "type": "awareness"
        })
    
    # May - Asian American and Pacific Islander Heritage Month
    if start_date.month <= 5 <= end_date.month:
        awareness_periods.append({
            "date": date(year, 5, 1),
            "name": "Asian American and Pacific Islander Heritage Month",
            "type": "awareness"
        })
        # Children's Book Week (1st week of May)
        book_week_start = get_nth_weekday(year, 5, 0, 1)  # 1st Monday in May
        if start_date <= book_week_start <= end_date:
            awareness_periods.append({
                "date": book_week_start,
                "name": "Children's Book Week",
                "type": "educational"
            })
    
    # June - Pride Month
    if start_date.month <= 6 <= end_date.month:
        awareness_periods.append({
            "date": date(year, 6, 1),
            "name": "Pride Month",
            "type": "awareness"
        })
    
    # August - Back to School Season
    if start_date.month <= 8 <= end_date.month:
        awareness_periods.append({
            "date": date(year, 8, 20),
            "name": "Back to School Season",
            "type": "seasonal"
        })
    
    # September - Hispanic Heritage Month (Sep 15 - Oct 15)
    if start_date.month <= 9 <= end_date.month:
        awareness_periods.append({
            "date": date(year, 9, 15),
            "name": "Hispanic Heritage Month",
            "type": "awareness"
        })
    
    # October - National Bullying Prevention Month
    if start_date.month <= 10 <= end_date.month:
        awareness_periods.append({
            "date": date(year, 10, 1),
            "name": "National Bullying Prevention Month",
            "type": "awareness"
        })
    
    # November - Native American Heritage Month
    if start_date.month <= 11 <= end_date.month:
        awareness_periods.append({
            "date": date(year, 11, 1),
            "name": "Native American Heritage Month",
            "type": "awareness"
        })
    
    holidays.extend(awareness_periods)
    
    # Sort by date
    holidays.sort(key=lambda x: x["date"])
    
    return holidays

def get_nth_weekday(year, month, weekday, n):
    """Get the nth occurrence of a weekday in a month"""
    first_day = date(year, month, 1)
    first_weekday = first_day.weekday()
    
    # Calculate days to add
    days_ahead = weekday - first_weekday
    if days_ahead < 0:
        days_ahead += 7
    
    # Get the first occurrence
    first_occurrence = first_day + relativedelta(days=days_ahead)
    
    # Get the nth occurrence
    nth_occurrence = first_occurrence + relativedelta(weeks=n-1)
    
    return nth_occurrence

def get_last_weekday(year, month, weekday):
    """Get the last occurrence of a weekday in a month"""
    # Get the last day of the month
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    
    # Find the last occurrence of the weekday
    days_back = (last_day.weekday() - weekday) % 7
    last_occurrence = last_day - relativedelta(days=days_back)
    
    return last_occurrence

def format_holidays_for_ai(holidays):
    """Format holidays list for inclusion in AI prompt"""
    if not holidays:
        return "No major holidays during this period."
    
    formatted = "Relevant holidays and observances during this period:\n"
    for holiday in holidays:
        formatted += f"- {holiday['name']} ({holiday['date'].strftime('%B %d')})\n"
    
    return formatted.strip()