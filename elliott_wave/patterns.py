"""
Elliott Wave corrective and impulse pattern detection.
Based on Chapters 7-13 of SweeGlu Practical Application of Elliott Wave Principle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

from .fibonacci import (
    RATIO_23,
    RATIO_38,
    RATIO_61,
    RATIO_100,
    RATIO_161,
    wave_length,
    retracement_ratio,
    projection_price,
)
from .rules import RuleResult


class PatternType(str, Enum):
    """Recognised Elliott Wave pattern types."""

    IMPULSE = "Impulse"
    LEADING_DIAGONAL = "Leading Diagonal"
    ENDING_DIAGONAL = "Ending Diagonal"
    ZIGZAG = "Simple Zigzag"
    IRREGULAR_CORRECTION = "Irregular Correction"
    FLAT = "3-3-5 Flat"
    COMPLEX_CORRECTION = "Complex Correction"
    UNKNOWN = "Unknown"


@dataclass
class PatternResult:
    """Result of a pattern detection attempt."""

    pattern: PatternType
    passed: bool
    reasons: List[str] = field(default_factory=list)
    targets: dict = field(default_factory=dict)

    def add_reason(self, text: str) -> None:
        self.reasons.append(text)

    def __bool__(self) -> bool:  # pragma: no cover
        return self.passed


# ── Impulse Patterns (Chapters 7-9) ─────────────────────────────────────────


def detect_impulse(pivots: List[float], bullish: bool = True) -> PatternResult:
    """Detect a standard 5-wave impulse pattern.

    Args:
        pivots:  Six price pivots [W0, W1, W2, W3, W4, W5].
        bullish: True for upward impulse.

    Returns:
        PatternResult with projected targets if pattern is valid.
    """
    from .rules import check_impulse_wave

    if len(pivots) != 6:
        return PatternResult(
            pattern=PatternType.UNKNOWN,
            passed=False,
            reasons=[f"Need 6 pivots for impulse, got {len(pivots)}."],
        )

    rule_results = check_impulse_wave(pivots, bullish, is_diagonal=False)
    failed = [r for r in rule_results if not r.passed]

    result = PatternResult(
        pattern=PatternType.IMPULSE,
        passed=len(failed) == 0,
        reasons=[r.reason for r in rule_results],
    )

    if result.passed:
        w0, w1, w2, w3, w4, w5 = pivots
        # Targets: Fibonacci projections for potential Wave 5 extension
        result.targets = _impulse_targets(w0, w1, w2, w3, w4, bullish)

    return result


def detect_leading_diagonal(pivots: List[float], bullish: bool = True) -> PatternResult:
    """Detect a Leading Diagonal in Wave 1 position.

    Leading Diagonal characteristics (Chapter 7):
    - Waves 1-2-3-4 overlap (Wave 4 enters Wave 1 territory).
    - Sub-structure is 3-3-3-3-3.
    - Wave 3 can never be shortest among 1, 3, 5.

    Args:
        pivots:  Six price pivots [W0, W1, W2, W3, W4, W5].
        bullish: True for upward diagonal.

    Returns:
        PatternResult.
    """
    if len(pivots) != 6:
        return PatternResult(
            pattern=PatternType.LEADING_DIAGONAL,
            passed=False,
            reasons=[f"Need 6 pivots for LD, got {len(pivots)}."],
        )

    w0, w1, w2, w3, w4, w5 = pivots
    reasons: List[str] = []
    passed = True

    # Wave 4 must overlap Wave 1 (defining characteristic of diagonal)
    if bullish:
        overlap = w4 < w1
    else:
        overlap = w4 > w1

    if not overlap:
        reasons.append(
            "Wave 4 does not overlap Wave 1 – not a Leading Diagonal."
        )
        passed = False
    else:
        reasons.append("Wave 4 overlaps Wave 1 territory – diagonal confirmed.")

    # Wave 3 must not be shortest
    len1 = wave_length(w0, w1)
    len3 = wave_length(w2, w3)
    len5 = wave_length(w4, w5)
    if len3 < min(len1, len5):
        reasons.append(
            f"Wave 3 ({len3:.4f}) is shortest – invalid even for Leading Diagonal."
        )
        passed = False
    else:
        reasons.append(f"Wave 3 is not shortest (len={len3:.4f}).")

    return PatternResult(
        pattern=PatternType.LEADING_DIAGONAL,
        passed=passed,
        reasons=reasons,
    )


def detect_ending_diagonal(pivots: List[float], bullish: bool = True) -> PatternResult:
    """Detect an Ending Diagonal in Wave 5 position.

    Ending Diagonal characteristics (Chapter 9):
    - Overlapping structure identical to Leading Diagonal.
    - Sub-structure is 3-3-3-3-3.
    - Signals trend exhaustion; often followed by sharp reversal.

    Args:
        pivots:  Six price pivots [W0, W1, W2, W3, W4, W5].
        bullish: True for upward diagonal.

    Returns:
        PatternResult.
    """
    # Structural rules are the same as Leading Diagonal
    result = detect_leading_diagonal(pivots, bullish)
    return PatternResult(
        pattern=PatternType.ENDING_DIAGONAL,
        passed=result.passed,
        reasons=result.reasons,
    )


# ── Corrective Patterns (Chapters 10-13) ─────────────────────────────────────


def detect_zigzag(
    a_start: float,
    a_end: float,
    b_end: float,
    c_end: float,
    bullish: bool = True,
) -> PatternResult:
    """Detect a Simple Zigzag correction (A-B-C).

    Rules (Chapter 10):
    - Wave A: impulse-like (5 sub-waves).
    - Wave B: retraces 38–61% of Wave A.
    - Wave C: projects more than 100% of Wave A.

    Args:
        a_start: Price at start of Wave A.
        a_end:   Price at end of Wave A.
        b_end:   Price at end of Wave B.
        c_end:   Price at end of Wave C.
        bullish: True if the parent trend is upward (A moves down).

    Returns:
        PatternResult with targets if valid.
    """
    reasons: List[str] = []
    passed = True

    len_a = wave_length(a_start, a_end)
    b_ratio = retracement_ratio(a_start, a_end, b_end)
    len_c = wave_length(b_end, c_end)
    c_ratio = len_c / len_a if len_a else 0.0

    # Wave B must retrace 38–61% of Wave A (±0.5% tolerance for float precision)
    _FLOAT_TOLERANCE = 0.005
    if (RATIO_38 - _FLOAT_TOLERANCE) <= b_ratio <= (RATIO_61 + _FLOAT_TOLERANCE):
        reasons.append(
            f"Wave B retraces {b_ratio * 100:.1f}% of Wave A (38–61%): valid zigzag."
        )
    else:
        reasons.append(
            f"Wave B retraces {b_ratio * 100:.1f}% of Wave A – "
            "outside 38–61% range for a Simple Zigzag."
        )
        passed = False

    # Wave C must project more than 100% of Wave A
    if c_ratio > RATIO_100:
        reasons.append(
            f"Wave C projects {c_ratio * 100:.1f}% of Wave A (> 100%): valid."
        )
    else:
        reasons.append(
            f"Wave C projects only {c_ratio * 100:.1f}% of Wave A – "
            "must exceed 100% for Simple Zigzag."
        )
        passed = False

    result = PatternResult(
        pattern=PatternType.ZIGZAG,
        passed=passed,
        reasons=reasons,
    )

    if passed:
        # Provide 38% retracement breakout trade setup targets (Chapter 18)
        result.targets = _zigzag_targets(a_start, a_end, b_end, c_end, bullish)

    return result


def detect_irregular_correction(
    a_start: float,
    a_end: float,
    b_end: float,
    c_end: float,
    bullish: bool = True,
) -> PatternResult:
    """Detect an Irregular (Expanded Flat) Correction.

    Rules (Chapter 11):
    - Wave B retraces more than 100% of Wave A.
    - Wave C may end before Wave A start (truncated C) or extend further.

    Args:
        a_start: Price at start of Wave A.
        a_end:   Price at end of Wave A.
        b_end:   Price at end of Wave B.
        c_end:   Price at end of Wave C.
        bullish: True if parent trend is upward.

    Returns:
        PatternResult.
    """
    reasons: List[str] = []
    passed = True

    b_ratio = retracement_ratio(a_start, a_end, b_end)

    # Wave B must exceed 100%
    if b_ratio > RATIO_100:
        reasons.append(
            f"Wave B retraces {b_ratio * 100:.1f}% of Wave A (> 100%): irregular."
        )
    else:
        reasons.append(
            f"Wave B retraces only {b_ratio * 100:.1f}% of Wave A – "
            "must exceed 100% for Irregular Correction."
        )
        passed = False

    # Note whether Wave C ends before Wave A start (truncation)
    if bullish:
        truncated = c_end > a_start
    else:
        truncated = c_end < a_start

    if truncated:
        reasons.append("Wave C ends before Wave A start (truncated C).")
    else:
        reasons.append("Wave C extends beyond Wave A start.")

    return PatternResult(
        pattern=PatternType.IRREGULAR_CORRECTION,
        passed=passed,
        reasons=reasons,
    )


def detect_flat_correction(
    a_start: float,
    a_end: float,
    b_end: float,
    c_end: float,
) -> PatternResult:
    """Detect a 3-3-5 Flat Correction.

    Rules (Chapter 12):
    - Wave B retraces approximately 100% of Wave A (90–105% range used here).
    - Wave C is less than 100% of Wave A.

    Args:
        a_start: Price at start of Wave A.
        a_end:   Price at end of Wave A.
        b_end:   Price at end of Wave B.
        c_end:   Price at end of Wave C.

    Returns:
        PatternResult.
    """
    reasons: List[str] = []
    passed = True

    len_a = wave_length(a_start, a_end)
    b_ratio = retracement_ratio(a_start, a_end, b_end)
    len_c = wave_length(b_end, c_end)
    c_ratio = len_c / len_a if len_a else 0.0

    # Wave B approximately 100% of Wave A (90–105%, ±0.5% float tolerance)
    FLAT_B_LOW = 0.895
    FLAT_B_HIGH = 1.055
    if FLAT_B_LOW <= b_ratio <= FLAT_B_HIGH:
        reasons.append(
            f"Wave B retraces {b_ratio * 100:.1f}% of Wave A (~100%): flat pattern."
        )
    else:
        reasons.append(
            f"Wave B retraces {b_ratio * 100:.1f}% of Wave A – "
            "expected ~100% for 3-3-5 Flat."
        )
        passed = False

    # Wave C less than 100% of Wave A
    if c_ratio < RATIO_100:
        reasons.append(
            f"Wave C projects {c_ratio * 100:.1f}% of Wave A (< 100%): valid flat."
        )
    else:
        reasons.append(
            f"Wave C projects {c_ratio * 100:.1f}% of Wave A – "
            "must be less than 100% for Flat Correction."
        )
        passed = False

    return PatternResult(
        pattern=PatternType.FLAT,
        passed=passed,
        reasons=reasons,
    )


def detect_complex_correction(wave_count: int) -> PatternResult:
    """Identify a Complex Correction based on the number of corrective waves.

    Rule (Chapter 13): Complex corrections contain 5 or more corrective waves
    (double/triple zigzag or combinations).

    Args:
        wave_count: Total number of labelled corrective sub-waves detected.

    Returns:
        PatternResult.
    """
    if wave_count >= 5:
        return PatternResult(
            pattern=PatternType.COMPLEX_CORRECTION,
            passed=True,
            reasons=[
                f"Complex correction detected with {wave_count} corrective waves "
                "(≥ 5). May be double/triple zigzag or combination."
            ],
        )
    return PatternResult(
        pattern=PatternType.COMPLEX_CORRECTION,
        passed=False,
        reasons=[
            f"Only {wave_count} corrective waves present. "
            "Complex correction requires 5 or more sub-waves."
        ],
    )


# ── Trade Setup Helpers (Chapter 17-18) ──────────────────────────────────────


def zigzag_trade_setup(
    a_start: float,
    a_end: float,
    b_end: float,
    c_end: float,
    bullish: bool = True,
) -> dict:
    """Return 38% breakout trade setup levels for a confirmed zigzag.

    Trade rules (Chapter 18):
    - Entry zone: between 38% and 23% retracement of the breakout move.
    - Stop loss: beyond 23% retracement.
    - Target 1: start of Wave C.
    - Target 2: start of Wave A.

    Args:
        a_start: Start of Wave A.
        a_end:   End of Wave A.
        b_end:   End of Wave B.
        c_end:   End of Wave C.
        bullish: True if trading a post-correction upside breakout.

    Returns:
        Dictionary with 'entry_zone', 'stop_loss', 'target_1', 'target_2'.
    """
    from .fibonacci import retracement_price

    # Measure from start of C to end of C for breakout retracement
    len_c = wave_length(b_end, c_end)
    entry_high = retracement_price(b_end, c_end, RATIO_38)
    entry_low = retracement_price(b_end, c_end, RATIO_23)
    stop_loss = retracement_price(b_end, c_end, RATIO_23)

    return {
        "entry_zone": (min(entry_low, entry_high), max(entry_low, entry_high)),
        "stop_loss": stop_loss,
        "target_1": b_end,   # start of Wave C
        "target_2": a_start,  # start of Wave A
    }


# ── Internal Helpers ──────────────────────────────────────────────────────────


def _impulse_targets(
    w0: float,
    w1: float,
    w2: float,
    w3: float,
    w4: float,
    bullish: bool,
) -> dict:
    """Project Wave 5 Fibonacci targets from Wave 4 end."""
    targets = {}
    len3 = wave_length(w2, w3)
    for label, ratio in [
        ("38.2%", RATIO_38),
        ("61.8%", RATIO_61),
        ("100.0%", RATIO_100),
        ("161.8%", RATIO_161),
    ]:
        targets[f"Wave5_{label}"] = projection_price(w2, w3, w4, ratio)
    return targets


def _zigzag_targets(
    a_start: float,
    a_end: float,
    b_end: float,
    c_end: float,
    bullish: bool,
) -> dict:
    """Internal: pre-computed targets for a confirmed zigzag."""
    setup = zigzag_trade_setup(a_start, a_end, b_end, c_end, bullish)
    return setup
