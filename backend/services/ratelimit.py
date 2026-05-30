from datetime import date
from config import settings

# In-memory store: { "ip:date": count }
# Resets naturally as keys change with date
_counts: dict[str, int] = {}

def check_and_increment(ip: str) -> bool:
    """Returns True if request is allowed, False if rate limit exceeded."""
    key = f"{ip}:{date.today().isoformat()}"
    current = _counts.get(key, 0)
    if current >= settings.rate_limit_per_day:
        return False
    _counts[key] = current + 1
    return True
