"""
Password strength validation utilities
"""

import re
from typing import List, Tuple

# Common weak passwords to reject
COMMON_PASSWORDS = {
    'password', 'password123', 'admin', 'admin123', '12345678', '123456789',
    'qwerty', 'qwerty123', 'letmein', 'welcome', 'monkey', '1234567890',
    'abc123', 'password1', '12345', '123456', '1234567', 'sunshine',
    'princess', 'dragon', 'passw0rd', 'master', 'hello', 'freedom',
    'whatever', 'qazwsx', 'trustno1', 'jordan23', 'harley', 'robert',
    'matthew', 'jordan', 'michelle', 'charlie', 'andrew', 'joshua'
}


class PasswordStrengthError(Exception):
    """Exception raised when password doesn't meet strength requirements"""
    def __init__(self, message: str, errors: List[str]):
        self.message = message
        self.errors = errors
        super().__init__(self.message)


def validate_password_strength(password: str) -> Tuple[bool, List[str]]:
    """
    Validate password strength
    
    Requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)
    - Not a common weak password
    
    Args:
        password: Password to validate
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check minimum length
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    
    # Check for uppercase letter
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")
    
    # Check for lowercase letter
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")
    
    # Check for digit
    if not re.search(r'\d', password):
        errors.append("Password must contain at least one digit")
    
    # Check for special character
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
        errors.append("Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)")
    
    # Check against common passwords
    if password.lower() in COMMON_PASSWORDS:
        errors.append("Password is too common. Please choose a more unique password")
    
    # Check for repeated characters (e.g., "aaaaaa", "111111")
    if re.search(r'(.)\1{4,}', password):
        errors.append("Password contains too many repeated characters")
    
    # Check for sequential characters (e.g., "12345", "abcde")
    if _has_sequential_chars(password, 4):
        errors.append("Password contains sequential characters (e.g., '1234', 'abcd')")
    
    is_valid = len(errors) == 0
    return is_valid, errors


def _has_sequential_chars(password: str, min_length: int = 4) -> bool:
    """
    Check if password contains sequential characters
    
    Args:
        password: Password to check
        min_length: Minimum length of sequence to flag
        
    Returns:
        True if sequential characters found
    """
    password_lower = password.lower()
    
    # Check for sequential digits
    for i in range(len(password_lower) - min_length + 1):
        substr = password_lower[i:i+min_length]
        if substr.isdigit():
            # Check if it's a sequence
            digits = [int(c) for c in substr]
            if all(digits[j] == digits[0] + j for j in range(len(digits))):
                return True
            if all(digits[j] == digits[0] - j for j in range(len(digits))):
                return True
    
    # Check for sequential letters
    for i in range(len(password_lower) - min_length + 1):
        substr = password_lower[i:i+min_length]
        if substr.isalpha():
            # Check if it's a sequence
            ords = [ord(c) for c in substr]
            if all(ords[j] == ords[0] + j for j in range(len(ords))):
                return True
            if all(ords[j] == ords[0] - j for j in range(len(ords))):
                return True
    
    return False


def get_password_requirements() -> str:
    """
    Get a human-readable list of password requirements
    
    Returns:
        String describing password requirements
    """
    return (
        "Password must meet the following requirements:\n"
        "• At least 8 characters long\n"
        "• At least one uppercase letter (A-Z)\n"
        "• At least one lowercase letter (a-z)\n"
        "• At least one digit (0-9)\n"
        "• At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)\n"
        "• Not a common or weak password\n"
        "• No repeated characters (e.g., 'aaaaaa')\n"
        "• No sequential characters (e.g., '1234', 'abcd')"
    )

