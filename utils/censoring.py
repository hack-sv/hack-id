"""Utility functions for censoring sensitive data in the dashboard."""

import re
from datetime import datetime


def censor_email(email):
    """Censor email address showing only first character and domain.
    
    Example: john.doe@gmail.com -> j***@gmail.com
    """
    if not email or '@' not in email:
        return email
    
    local, domain = email.split('@', 1)
    if len(local) == 0:
        return email
    
    return f"{local[0]}***@{domain}"


def censor_name(name):
    """Censor name showing only first 3 characters.
    
    Example: Jason Smith -> Jas***
    """
    if not name:
        return name
    
    if len(name) <= 3:
        return name  # Don't censor very short names
    
    return f"{name[:3]}***"


def censor_phone(phone):
    """Censor phone number showing country code and area code only.
    
    Example: +1 (650) 555-1234 -> +1 (650) ***-****
    """
    if not phone:
        return phone
    
    # Pattern for US phone numbers: +1 (XXX) XXX-XXXX
    pattern = r'(\+\d+\s*\(\d+\)\s*)\d{3}-\d{4}'
    replacement = r'\1***-****'
    
    censored = re.sub(pattern, replacement, phone)
    
    # If pattern didn't match, try simpler patterns
    if censored == phone:
        # Try pattern: +1-XXX-XXX-XXXX
        pattern = r'(\+\d+-\d{3}-)\d{3}-\d{4}'
        replacement = r'\1***-****'
        censored = re.sub(pattern, replacement, phone)
    
    if censored == phone:
        # Try pattern: (XXX) XXX-XXXX
        pattern = r'(\(\d{3}\)\s*)\d{3}-\d{4}'
        replacement = r'\1***-****'
        censored = re.sub(pattern, replacement, phone)
    
    return censored


def censor_address(address):
    """Censor address showing only city and state.
    
    Example: 123 Main Street, Apt 4B, Palo Alto, CA -> *** ********* ****** Palo Alto, CA
    """
    if not address:
        return address
    
    # Split by comma and assume last two parts are city, state
    parts = [part.strip() for part in address.split(',')]
    
    if len(parts) < 2:
        return address  # Can't determine city/state
    
    # Keep last two parts (city, state), censor the rest
    city = parts[-2]
    state = parts[-1]
    
    # Create censored version of street address
    censored_parts = []
    for i in range(len(parts) - 2):
        part = parts[i]
        # Replace each word with asterisks of similar length
        words = part.split()
        censored_words = []
        for word in words:
            if word.isdigit():
                censored_words.append('***')
            else:
                censored_words.append('*' * min(len(word), 9))
        censored_parts.append(' '.join(censored_words))
    
    if censored_parts:
        return f"{', '.join(censored_parts)}, {city}, {state}"
    else:
        return f"*** ********* ******, {city}, {state}"


def censor_emergency_contact(contact_info):
    """Censor emergency contact info.
    
    Example: Deborah Smith, d.smith@outlook.com, +1 (408) 555-9876 
             -> Deb***, d***@outlook.com, +1 (408) ***-****
    """
    if not contact_info:
        return contact_info
    
    # Split by comma
    parts = [part.strip() for part in contact_info.split(',')]
    
    if len(parts) < 3:
        return contact_info  # Not in expected format
    
    name = parts[0]
    email = parts[1]
    phone = parts[2]
    
    # Censor each part
    censored_name = censor_name(name)
    censored_email = censor_email(email)
    censored_phone = censor_phone(phone)
    
    return f"{censored_name}, {censored_email}, {censored_phone}"


def censor_date(date_str):
    """Censor date showing only year pattern.
    
    Example: 03/15/1995 -> **/**/20**
    Example: 1995-03-15 -> **/**/20**
    """
    if not date_str:
        return date_str
    
    # Try to parse different date formats
    date_patterns = [
        (r'\d{2}/\d{2}/(\d{4})', '**/**/20**'),  # MM/DD/YYYY
        (r'\d{4}-\d{2}-\d{2}', '**/**/20**'),    # YYYY-MM-DD
        (r'\d{2}-\d{2}-(\d{4})', '**/**/20**'),  # MM-DD-YYYY
    ]
    
    for pattern, replacement in date_patterns:
        if re.match(pattern, date_str):
            return replacement
    
    # If no pattern matches, return generic censored date
    return '**/**/20**'


def censor_dob(dob):
    """Censor date of birth, keeping it generic.
    
    Example: 1995-03-15 -> **/**/20**
    """
    return censor_date(dob)


# Flask template filters
def register_censoring_filters(app):
    """Register censoring functions as Jinja2 template filters."""
    app.jinja_env.filters['censor_email'] = censor_email
    app.jinja_env.filters['censor_name'] = censor_name
    app.jinja_env.filters['censor_phone'] = censor_phone
    app.jinja_env.filters['censor_address'] = censor_address
    app.jinja_env.filters['censor_emergency'] = censor_emergency_contact
    app.jinja_env.filters['censor_date'] = censor_dob
