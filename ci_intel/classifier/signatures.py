"""
Normalizes raw error log lines into stable 12-char SHA-1 hashes (error_signature).

Strips volatile tokens so the same failure maps to the same signature across runs:
  - Hex addresses   → <addr>
  - Bare integers   → <n>
  - Unix paths      → <path>
  - Windows paths   → <path>
  - Excess whitespace collapsed
"""
import hashlib
import re

_ADDR = re.compile(r"0x[0-9a-fA-F]{4,}")
_PATH_WIN = re.compile(r"[A-Za-z]:\\[\w\\. /-]+")
_PATH_UNIX = re.compile(r"(?:/[\w.@_-]+){2,}")  # at least two components
_NUM = re.compile(r"\b\d+\b")
_WS = re.compile(r"\s+")


def normalize(line):
    line = _ADDR.sub("<addr>", line)
    line = _PATH_WIN.sub("<path>", line)
    line = _PATH_UNIX.sub("<path>", line)
    line = _NUM.sub("<n>", line)
    line = _WS.sub(" ", line).strip().lower()
    return line


def signature(line):
    """Return a 12-char hex SHA-1 prefix of the normalized line."""
    return hashlib.sha1(normalize(line).encode()).hexdigest()[:12]
