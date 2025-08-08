from django import template
from datetime import date, datetime

register = template.Library()

@register.filter
def calculate_age(birth_date):
    """Calculate age from birth date"""
    if not birth_date:
        return None
    
    # Handle string dates
    if isinstance(birth_date, str):
        try:
            # Try parsing ISO format (YYYY-MM-DD)
            birth_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
        except ValueError:
            try:
                # Try parsing other common formats
                birth_date = datetime.strptime(birth_date, '%m/%d/%Y').date()
            except ValueError:
                return None
    
    today = date.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age

@register.filter
def format_date(date_string):
    """Format date string to Month Day, Year"""
    if not date_string:
        return None
    
    if isinstance(date_string, str):
        try:
            # Try parsing ISO format (YYYY-MM-DD)
            date_obj = datetime.strptime(date_string, '%Y-%m-%d')
            return date_obj.strftime('%B %d, %Y')
        except ValueError:
            try:
                # Try parsing other common formats
                date_obj = datetime.strptime(date_string, '%m/%d/%Y')
                return date_obj.strftime('%B %d, %Y')
            except ValueError:
                return date_string
    
    # If it's already a date object
    if hasattr(date_string, 'strftime'):
        return date_string.strftime('%B %d, %Y')
    
    return str(date_string)