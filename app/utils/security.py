"""
Security utility module for input sanitization, rate-limiting, and LLM prompt-injection mitigation.
"""

import time
import re
import threading
from typing import Dict, Tuple
from fastapi import HTTPException, Request, status

class SecurityUtils:
    # Match HTML tags to prevent XSS
    HTML_CLEAN_RE = re.compile(r'<[^>]*>')
    
    # Prompt injection patterns (ignore instruction overrides, system instruction leaks)
    INJECTION_PATTERNS = [
        r"ignore\s+(?:the\s+)?previous",
        r"system\s+(?:prompt|instructions|role)",
        r"act\s+as\s+a",
        r"you\s+are\s+now",
        r"new\s+instructions",
        r"bypass\s+restrictions",
        r"disable\s+safety",
        r"jailbreak"
    ]
    
    INJECTION_RE = re.compile(f"(?:{'|'.join(INJECTION_PATTERNS)})", re.IGNORECASE)

    @classmethod
    def sanitize_input(cls, text: str) -> str:
        """Strips HTML tags and removes control/dangerous characters from user prompts."""
        if not text:
            return ""
        # Remove HTML tags
        clean_text = cls.HTML_CLEAN_RE.sub("", text)
        # Strip backslashes and single/double quotes to avoid shell/query escapes
        clean_text = clean_text.replace("\"", "").replace("'", "")
        # Remove non-printable control characters
        clean_text = "".join(c for c in clean_text if c.isprintable())
        return clean_text.strip()

    @classmethod
    def detect_prompt_injection(cls, text: str) -> bool:
        """Scans the user prompt for known adversarial jailbreaking/override keywords."""
        if not text:
            return False
        return bool(cls.INJECTION_RE.search(text))


class RateLimiter:
    """
    Sliding window rate limiter mapping IP addresses to request timestamps.
    Thread-safe implementation.
    """
    def __init__(self, requests_limit: int = 60, window_seconds: int = 60) -> None:
        self.limit = requests_limit
        self.window = window_seconds
        self.history: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def check_rate_limit(self, client_ip: str) -> bool:
        """
        Validates whether the client IP has exceeded the allowed rate limits.
        
        Returns:
            bool: True if request is allowed, False if throttled.
        """
        with self._lock:
            now = time.time()
            if client_ip not in self.history:
                self.history[client_ip] = [now]
                return True
            
            # Filter timestamps within current window
            window_start = now - self.window
            timestamps = [t for t in self.history[client_ip] if t > window_start]
            
            if len(timestamps) < self.limit:
                timestamps.append(now)
                self.history[client_ip] = timestamps
                return True
            else:
                self.history[client_ip] = timestamps
                return False

# Global Rate Limiter instance
rate_limiter = RateLimiter(requests_limit=60, window_seconds=60)

async def rate_limit_dependency(request: Request):
    """FastAPI route dependency to apply rate limiting based on client IP."""
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limiter.check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please wait before requesting another wayfinding route."
        )
