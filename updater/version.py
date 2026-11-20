"""
Semantic Versioning utilities for GitHub Auto-Update System.
"""
import re
from typing import Tuple, Optional


def parse_version(v_str: str) -> Tuple[int, int, int, int]:
    """Parses a version string into a 4-element integer tuple (major, minor, patch, build).
    
    Examples:
        '2.2.0'     -> (2, 2, 0, 0)
        'v2.3.1'    -> (2, 3, 1, 0)
        '2.3.1.5'   -> (2, 3, 1, 5)
        'V3.0'      -> (3, 0, 0, 0)
        '2.4-rc1'   -> (2, 4, 0, 0)
        'invalid'   -> (0, 0, 0, 0)
    """
    if not v_str:
        return (0, 0, 0, 0)

    clean = str(v_str).strip().lstrip("vV")
    match = re.match(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.(\d+))?", clean)
    if not match:
        return (0, 0, 0, 0)

    parts = [int(p) if p is not None else 0 for p in match.groups()]
    return (parts[0], parts[1], parts[2], parts[3])


def is_newer_version(latest_str: str, current_str: str) -> bool:
    """Returns True if latest_str is strictly newer than current_str."""
    return parse_version(latest_str) > parse_version(current_str)


def format_version(v_tuple: Tuple[int, ...]) -> str:
    """Formats a version tuple into standard 'X.Y.Z' string."""
    if len(v_tuple) >= 4 and v_tuple[3] > 0:
        return f"{v_tuple[0]}.{v_tuple[1]}.{v_tuple[2]}.{v_tuple[3]}"
    return f"{v_tuple[0]}.{v_tuple[1]}.{v_tuple[2]}"
