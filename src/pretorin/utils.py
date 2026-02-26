"""Shared utilities for the Pretorin CLI."""

from __future__ import annotations

import re


def normalize_control_id(control_id: str) -> str:
    """Normalize a control ID to the canonical zero-padded format.

    NIST/FedRAMP control IDs use zero-padded numbers (e.g., ac-02, sc-07).
    AI agents sometimes produce unpadded variants (ac-2, sc-7). This function
    ensures consistent formatting.

    Examples:
        ac-3   -> ac-03
        AC-3   -> ac-03
        sc-7   -> sc-07
        ac-02  -> ac-02  (already padded)
        ac-2.1 -> ac-02.1 (enhancement)
        ac-2(1) -> ac-02(1) (enhancement alt format)
    """
    if not control_id:
        return control_id

    lowered = control_id.lower().strip()

    # Match: family prefix (letters) - single digit, optionally followed by
    # enhancement suffixes like .1, (1), etc.
    match = re.match(r"^([a-z]{2})-(\d+)(.*)", lowered)
    if not match:
        return lowered

    family = match.group(1)
    number = match.group(2)
    suffix = match.group(3)

    # Zero-pad the control number to at least 2 digits
    padded = number.zfill(2)

    return f"{family}-{padded}{suffix}"
