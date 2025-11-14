"""
Rate limiting utility for image search
"""

import time
import logging
from typing import Dict, List, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)

# Default rate limit: 10 requests per user per hour
DEFAULT_RATE_LIMIT = 10
DEFAULT_TIME_WINDOW = 3600  # 1 hour in seconds


class RateLimiter:
    """
    Simple in-memory rate limiter using sliding window approach
    """
    
    def __init__(self, max_requests: int = DEFAULT_RATE_LIMIT, time_window: int = DEFAULT_TIME_WINDOW):
        """
        Initialize rate limiter
        
        Args:
            max_requests: Maximum number of requests allowed
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        # Store request timestamps per user: {user_id: [timestamp1, timestamp2, ...]}
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self._cleanup_interval = time_window * 2  # Clean up old entries every 2x time window
        self._last_cleanup = time.time()
    
    def _cleanup_old_entries(self):
        """Remove old request timestamps outside the time window"""
        current_time = time.time()
        
        # Only cleanup periodically to avoid overhead
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        cutoff_time = current_time - self.time_window
        
        for user_id in list(self.requests.keys()):
            # Filter out timestamps outside the time window
            self.requests[user_id] = [
                ts for ts in self.requests[user_id] 
                if ts > cutoff_time
            ]
            
            # Remove user entry if no requests left
            if not self.requests[user_id]:
                del self.requests[user_id]
        
        self._last_cleanup = current_time
    
    def is_allowed(self, user_id: str) -> tuple[bool, Optional[str]]:
        """
        Check if request is allowed for user
        
        Args:
            user_id: User identifier (telegram_id as string)
            
        Returns:
            Tuple of (is_allowed, error_message)
            - is_allowed: True if request is allowed, False otherwise
            - error_message: Error message if not allowed, None otherwise
        """
        self._cleanup_old_entries()
        
        current_time = time.time()
        cutoff_time = current_time - self.time_window
        
        # Get user's request timestamps
        user_requests = self.requests[user_id]
        
        # Filter out old requests outside the time window
        user_requests = [ts for ts in user_requests if ts > cutoff_time]
        self.requests[user_id] = user_requests
        
        # Check if limit exceeded
        if len(user_requests) >= self.max_requests:
            # Calculate time until next request is allowed
            oldest_request = min(user_requests)
            time_until_allowed = (oldest_request + self.time_window) - current_time
            minutes = int(time_until_allowed / 60) + 1
            
            logger.warning(
                f"Rate limit exceeded for user {user_id}: "
                f"{len(user_requests)}/{self.max_requests} requests in last hour"
            )
            
            return False, f"Rate limit exceeded. Please wait {minutes} minute(s) before trying again."
        
        # Add current request timestamp
        user_requests.append(current_time)
        self.requests[user_id] = user_requests
        
        logger.debug(
            f"Rate limit check for user {user_id}: "
            f"{len(user_requests)}/{self.max_requests} requests in last hour - ALLOWED"
        )
        
        return True, None
    
    def reset_user(self, user_id: str):
        """Reset rate limit for a specific user (for testing/admin purposes)"""
        if user_id in self.requests:
            del self.requests[user_id]
            logger.info(f"Rate limit reset for user {user_id}")


# Global rate limiter instance
_image_search_rate_limiter = RateLimiter(
    max_requests=DEFAULT_RATE_LIMIT,
    time_window=DEFAULT_TIME_WINDOW
)


def check_rate_limit(user_id: str) -> tuple[bool, Optional[str]]:
    """
    Check if image search request is allowed for user
    
    Args:
        user_id: User identifier (telegram_id as string)
        
    Returns:
        Tuple of (is_allowed, error_message)
    """
    return _image_search_rate_limiter.is_allowed(user_id)

