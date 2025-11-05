"""
Social handle normalization utilities for Dating Popcorn Bot
"""

import re
import logging
from typing import Optional

# Configure logger
logger = logging.getLogger(__name__)

def normalize_query(query: str) -> str:
    """
    Normalize input for better searching:
    - If it looks like a phone number: keep + sign, remove other special characters
    - If it's a username: prepend @ if missing and ensure alphanumeric
    - If it's a regular name: return as-is (lowercase for consistency)
    
    Args:
        query: Input string to normalize
    
    Returns:
        Normalized string
    """
    logger.debug(f"🔤 Normalizing query: '{query}'")
    
    if not query or not query.strip():
        logger.debug("🔤 Empty query, returning empty string")
        return ""
    
    query = query.strip()
    logger.debug(f"🔤 Trimmed query: '{query}'")
    
    # Check if it looks like a phone number (contains digits and possibly + at start)
    if re.match(r'^\+?[\d\s\-\(\)]+$', query):
        logger.debug(f"🔤 Detected phone number format: '{query}'")
        # Format as phone number: keep + if present, remove other special chars
        phone_number = query.lstrip('+')
        # Remove spaces, dashes, parentheses
        phone_number = re.sub(r'[\s\-\(\)]', '', phone_number)
        # Add + prefix if it was there originally or if it's a long number
        if query.startswith('+') or len(phone_number) >= 10:
            result = f"+{phone_number}"
        else:
            result = phone_number
        logger.info(f"🔤 Normalized phone number: '{query}' -> '{result}'")
        return result
    
    # Check if it's already a username (starts with @)
    if query.startswith('@'):
        result = query.lower()
        logger.info(f"🔤 Normalized existing username: '{query}' -> '{result}'")
        return result
    
    # Check if it looks like a username (alphanumeric with underscores/dots, no spaces)
    username = query.lstrip('@')
    if re.match(r'^[a-zA-Z0-9_.]+$', username) and ' ' not in username:
        # Valid username format, add @ prefix
        result = f"@{username.lower()}"
        logger.info(f"🔤 Normalized username: '{query}' -> '{result}'")
        return result
    else:
        # Regular name or text, return as-is (lowercase for consistency)
        result = query.lower()
        logger.info(f"🔤 Normalized regular text: '{query}' -> '{result}'")
        return result

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
    Check if the given text looks like a phone number.
    Phone numbers contain special characters (+, /, -, spaces) + numbers, OR pure digits (8+ digits).
    Nicknames/handles contain only alphanumeric characters and underscores/dots (no special phone chars).
    
    Args:
        text: Text to check
    
    Returns:
        True if it looks like a phone number, False otherwise
    """
    if not text or not text.strip():
        return False
    
    text = text.strip()
    
    # Check if it contains special phone number characters (+, /, -, spaces, parentheses)
    # Phone numbers have special chars + numbers
    # Nicknames/handles only have alphanumeric + underscores/dots (no +, /, -, spaces)
    has_phone_special_chars = bool(re.search(r'[+\/\-\s\(\)]', text))
    
    # Check if it contains digits
    has_digits = bool(re.search(r'\d', text))
    
    # Check if it's pure digits (8+ digits) - likely a phone number
    digits_only = re.sub(r'[^\d]', '', text)
    is_pure_digits_8plus = len(digits_only) >= 8 and bool(re.match(r'^\d+$', text))
    
    # If it has special phone chars AND digits, it's likely a phone number
    # OR if it's pure digits (8+ digits), it's likely a phone number
    # If it only has alphanumeric/underscores/dots (no special phone chars), it's likely a handle
    return (has_phone_special_chars and has_digits) or is_pure_digits_8plus

def normalize_phone_number(phone: str) -> str:
    """
    Normalize phone number by extracting the last 8-9 digits.
    - If user enters only 8 digits, keep 8
    - If user enters 9 or more digits, keep last 9
    - Remove all special characters (+, /, -, spaces, parentheses, etc.)
    
    Examples:
        +1123456789 -> 123456789 (9 digits)
        123 456 789 -> 123456789 (9 digits)
        0177/1234567 -> 771234567 (9 digits)
        123-456-678 -> 123456678 (9 digits)
        12345678 -> 12345678 (8 digits, stays 8)
    
    Args:
        phone: Phone number string to normalize
    
    Returns:
        Normalized phone number (last 8-9 digits only)
    """
    if not phone or not phone.strip():
        return ""
    
    # Remove all special characters, keep only digits
    digits_only = re.sub(r'[^\d]', '', phone.strip())
    
    if not digits_only:
        return ""
    
    # If user entered only 8 digits, keep 8
    # If user entered 9 or more digits, take last 9
    if len(digits_only) <= 8:
        return digits_only
    else:
        return digits_only[-9:]

def normalize_query(query: str) -> str:
    """
    Normalize input for better searching:
    - If it looks like a phone number: extract last 8-9 digits (remove country codes and special chars)
    - If it's a username: prepend @ if missing and ensure alphanumeric
    - If it's a regular name: return as-is (lowercase for consistency)
    
    Args:
        query: Input string to normalize
    
    Returns:
        Normalized string
    """
    logger.debug(f"🔤 Normalizing query: '{query}'")
    
    if not query or not query.strip():
        logger.debug("🔤 Empty query, returning empty string")
        return ""
    
    query = query.strip()
    logger.debug(f"🔤 Trimmed query: '{query}'")
    
    # Check if it looks like a phone number (contains special chars + numbers)
    if is_phone_like(query):
        logger.debug(f"🔤 Detected phone number format: '{query}'")
        # Normalize phone number: extract last 8-9 digits
        result = normalize_phone_number(query)
        logger.info(f"🔤 Normalized phone number: '{query}' -> '{result}'")
        return result
    
    # Check if it's already a username (starts with @)
    if query.startswith('@'):
        result = query.lower()
        logger.info(f"🔤 Normalized existing username: '{query}' -> '{result}'")
        return result
    
    # Check if it looks like a username (alphanumeric with underscores/dots, no spaces, no phone special chars)
    username = query.lstrip('@')
    if re.match(r'^[a-zA-Z0-9_.]+$', username) and ' ' not in username:
        # Valid username format, add @ prefix
        result = f"@{username.lower()}"
        logger.info(f"🔤 Normalized username: '{query}' -> '{result}'")
        return result
    else:
        # Regular name or text, return as-is (lowercase for consistency)
        result = query.lower()
        logger.info(f"🔤 Normalized regular text: '{query}' -> '{result}'")
        return result
