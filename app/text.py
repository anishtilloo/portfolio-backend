import math
import re
import unicodedata

WORDS_PER_MINUTE = 220


def slugify(value: str, max_length: int = 80) -> str:
    """Turn a title into a URL-friendly address: 'Hello, World!' -> 'hello-world'."""
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value[:max_length].strip("-") or "post"


def reading_minutes(markdown: str) -> int:
    words = len(re.findall(r"\w+", markdown))
    return max(1, math.ceil(words / WORDS_PER_MINUTE))


def escape_like(value: str) -> str:
    """Escape the wildcard characters in a LIKE pattern (use with escape='\\\\')."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
