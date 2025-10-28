"""
Social handle normalization utilities for Dating Popcorn Bot
"""

import re
from typing import Optional

def normalize_query(query: str) -> str:
    """
    Normalize input for better searching:
    - If it looks like a phone number: keep + sign, remove other special characters
    - If it's a username: prepend @ if missing and ensure alphanumeric
    
    Args:
        query: Input string to normalize
    
    Returns:
        Normalized string
    """
    if not query or not query.strip():
        return ""
    
    query = query.strip()
    
    # Check if it looks like a phone number (contains digits and possibly + at start)
    if re.match(r'^\+?[\d\s\-\(\)]+$', query):
        # Format as phone number: keep + if present, remove other special chars
        phone_number = query.lstrip('+')
        # Remove spaces, dashes, parentheses
        phone_number = re.sub(r'[\s\-\(\)]', '', phone_number)
        # Add + prefix if it was there originally or if it's a long number
        if query.startswith('+') or len(phone_number) >= 10:
            return f"+{phone_number}"
        else:
            return phone_number
    
    # Handle as username
    # Remove any existing @ prefix
    username = query.lstrip('@')
    
    # Check if it's alphanumeric (with underscores and dots allowed)
    if re.match(r'^[a-zA-Z0-9_.]+$', username):
        # Valid username format, add @ prefix
        return f"@{username}"
    else:
        # Invalid username format, return as is with @ prefix
        return f"@{username}"

def is_username(text: str) -> bool:
    """
    Check if the given text is a valid username format
    
    Args:
        text: Text to check
    
    Returns:
        True if valid username format, False otherwise
    """
    if not text or not text.strip():
        return False
    
    username = text.strip().lstrip('@')
    return bool(re.match(r'^[a-zA-Z0-9_.]+$', username))

def is_phone_like(text: str) -> bool:
    """
    Check if the given text looks like a phone number
    
    Args:
        text: Text to check
    
    Returns:
        True if it looks like a phone number, False otherwise
    """
    if not text or not text.strip():
        return False
    
    text = text.strip()
    # Check if it contains mostly digits with some common phone number characters
    return bool(re.match(r'^\+?[\d\s\-\(\)]+$', text))
