from django import template
from datetime import datetime
import re
from ..models import Commission, ExamResult,Users, DocumentUpload, Branch,BqpMaster
from datetime import timedelta
register = template.Library()
from datetime import datetime, date, timedelta

@register.filter
def fallback(primary, secondary):
    return primary or secondary

@register.filter
def blank_if_none_or_text_none(value):
    if value in [None, 'None']:
        return ''
    return value

@register.filter
def indian_currency(value):
    try:
        value = float(value)
        int_part, dot, decimal_part = f"{value:.2f}".partition(".")
        int_part = int(int_part)
        if int_part < 1000:
            return f"{int_part}.{decimal_part}"
        else:
            s = str(int_part)
            last3 = s[-3:]
            rest = s[:-3]
            rest = ",".join([rest[max(i - 2, 0):i] for i in range(len(rest), 0, -2)][::-1])
            return f"{rest},{last3}.{decimal_part}" if rest else f"{last3}.{decimal_part}"
    except:
        return value


@register.filter
def dict_key(d, key):
    # safely get dict value by key
    if isinstance(d, dict):
        return d.get(key, '')
    return ''

@register.filter
def replace_underscore_with_space(value):
    """Replaces underscores with spaces in a string."""
    return value.replace('_', ' ')


@register.filter
def replace(value, args):
    """
    Replace all occurrences of first string with the second string.
    Usage: {{ value|replace:"_ , " " }}
    Args is a string like "old,new" separated by a comma.
    """
    old, new = args.split(',')
    return value.replace(old, new)

@register.filter
def split(value, key):
    """Returns the value turned into a list split by the key."""
    if value:
        return value.split(key)
    return [] 

@register.filter
def get_item(dictionary, key):
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None

@register.filter
def format_date(value, output_format="%Y-%m-%d"):
    """Convert '03-Mar-2025' to '2025-03-03' (YYYY-MM-DD)."""
    try:
        if not value:
            return ""

        value = str(value).strip()  # Ensure it's a string

        # Convert 'DD-MMM-YYYY' → 'YYYY-MM-DD'
        date_obj = datetime.strptime(value, "%d-%b-%Y")

        # Format as YYYY-MM-DD
        return date_obj.strftime(output_format)
    except ValueError:
        return "Invalid Date"

   
@register.filter
def str_replace(value, args):
    """Replace old substring with new substring. Args format: 'old,new'"""
    old, new = args.split(',')
    return value.replace(old, new)

@register.filter
def title_case(value):
    """Convert a string to title case (first letter capitalized)."""
    if isinstance(value, str):
        return value.title()
    return value

@register.filter
def trim(value):
    """Removes leading and trailing spaces from a string."""
    return value.strip() if isinstance(value, str) else value
 
@register.filter  # Register get_year as a valid Django template filter
def get_year(value):
    """Extracts the year from 'MM/YYYY' format."""
    if value:
        match = re.search(r"\d{2}/(\d{4})", value)
        if match:
            return match.group(1)  # Extracts the year (YYYY)
    return ""  # Return an empty string if parsing fails

@register.filter
def get_attr(obj, attr_name):
    """Safely gets an attribute from an object."""
    return getattr(obj, attr_name, "")

@register.filter
def attr(obj, field_name):
    """Returns the attribute of an object dynamically."""
    return getattr(obj, field_name, "")

@register.filter
def get_index(sequence, index):
    """Custom filter to get an item from a list using its index."""
    try:
        return sequence[index]
    except (IndexError, TypeError):
        return ""
    
@register.filter(name='subtract')
def subtract(value, arg):
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0
    
@register.simple_tag
def get_user_details(user_id):
    try:
        return Users.objects.get(id=user_id)
    except Users.DoesNotExist:
        return None
    
    
@register.filter
def add_days(value, days):
    try:
        return value + timedelta(days=int(days))
    except:
        return value
    
    
@register.filter
def mask_aadhaar(value):
    """
    Mask Aadhaar number to format XXXX XXXX 1234
    """
    try:
        digits = ''.join(filter(str.isdigit, str(value)))
        if len(digits) == 12:
            return f"XXXX XXXX {digits[-4:]}"
    except Exception as e:
        print("mask_aadhaar error:", e)
    return "-"

@register.filter
def add_t_days(value, days):
    try:
        days = int(days)
        if isinstance(value, (datetime, date)):
            return value + timedelta(days=days)
    except Exception as e:
        print("add_t_days error:", e)
    return value

@register.filter
def add_days_str(value, days):
    from datetime import datetime, timedelta
    from django.utils.timezone import make_aware

    try:
        dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        aware_dt = make_aware(dt)
        return aware_dt + timedelta(days=int(days))
    except Exception:
        return value