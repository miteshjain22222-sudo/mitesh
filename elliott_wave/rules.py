"""
Core Elliott Wave rules and validation.
Based on Chapters 1, 4, 7-9, 14 of SweeGlu Practical Application of
Elliott Wave Principle.

Each validation function returns a ``RuleResult`` named-tuple so callers
can inspect both the pass/fail flag and a human-readable reason.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .fibonacci import (
    RATIO_38,
    RATIO_61,
    RATIO_100,
    RATIO_161,
    wave_length,
    retracement_ratio,
)


@dataclass(frozen=True)
class RuleResult:
    """Outcome of a single Elliott Wave rule check."""

    passed: bool
    rule: str
    reason: str

    def __bool__(self) -> bool:  # pragma: no cover
        return self.passed


@dataclass
class WavePoint:
    """A single price pivot that marks the start or end of a wave.

    Args:
        label: Human-readable label, e.g. ``"0"``, ``"1"``, ``"2"`` …
        price: Price at this pivot.
        index: Optional bar/candle index for ordering.
    """

    label: str
    price: float
    index: Optional[int] = None


# ── Chapter 1 – Basic Rules ──────────────────────────────────────────────────


def check_wave2_retrace(
    wave1_start: float,
    wave1_end: float,
    wave2_end: float,
) -> RuleResult:
    """Wave 2 must not retrace more than 100% of Wave 1.

    Wave 2 end price must stay *above* (bull) or *below* (bear) the Wave 1
    start price.

    Args:
        wave1_start: Price at the start of Wave 1 (pivot 0).
        wave1_end:   Price at the end of Wave 1 (pivot 1).
        wave2_end:   Price at the end of Wave 2 (pivot 2).

    Returns:
        RuleResult.
    """
    bull = wave1_end > wave1_start
    if bull:
        passed = wave2_end > wave1_start
    else:
        passed = wave2_end < wave1_start

    if passed:
        ratio = retracement_ratio(wave1_start, wave1_end, wave2_end)
        return RuleResult(
            passed=True,
            rule="Wave 2 Retracement",
            reason=f"Wave 2 retraces {ratio * 100:.1f}% of Wave 1 (≤ 100%).",
        )
    return RuleResult(
        passed=False,
        rule="Wave 2 Retracement",
        reason=(
            "Wave 2 retraces more than 100% of Wave 1 – "
            "Wave 2 end has crossed Wave 1 start."
        ),
    )


def check_wave3_not_shortest(
    w1_start: float,
    w1_end: float,
    w3_start: float,
    w3_end: float,
    w5_start: float,
    w5_end: float,
) -> RuleResult:
    """Wave 3 can never be the shortest among Waves 1, 3, and 5.

    Args:
        w1_start: Wave 1 start price.
        w1_end:   Wave 1 end price.
        w3_start: Wave 3 start price.
        w3_end:   Wave 3 end price.
        w5_start: Wave 5 start price.
        w5_end:   Wave 5 end price.

    Returns:
        RuleResult.
    """
    len1 = wave_length(w1_start, w1_end)
    len3 = wave_length(w3_start, w3_end)
    len5 = wave_length(w5_start, w5_end)

    passed = len3 >= min(len1, len5)
    if passed:
        return RuleResult(
            passed=True,
            rule="Wave 3 Not Shortest",
            reason=(
                f"Wave 3 length {len3:.4f} is not shorter than both "
                f"Wave 1 ({len1:.4f}) and Wave 5 ({len5:.4f})."
            ),
        )
    return RuleResult(
        passed=False,
        rule="Wave 3 Not Shortest",
        reason=(
            f"Wave 3 ({len3:.4f}) is the shortest impulse wave among "
            f"Wave 1 ({len1:.4f}), Wave 3 ({len3:.4f}), and Wave 5 ({len5:.4f})."
        ),
    )


def check_wave4_no_overlap(
    wave1_end: float,
    wave4_end: float,
    bullish: bool,
    is_diagonal: bool = False,
) -> RuleResult:
    """Wave 4 must not overlap Wave 1 territory (except diagonals).

    In a bullish sequence Wave 4's low must stay *above* Wave 1's high.
    In a bearish sequence Wave 4's high must stay *below* Wave 1's low.

    Args:
        wave1_end:   Price at the end of Wave 1.
        wave4_end:   Price at the end of Wave 4.
        bullish:     True for an upward impulse, False for downward.
        is_diagonal: If True, overlap is permitted (diagonal exception).

    Returns:
        RuleResult.
    """
    if is_diagonal:
        return RuleResult(
            passed=True,
            rule="Wave 4 No Overlap",
            reason="Diagonal exception: overlap between Wave 4 and Wave 1 is allowed.",
        )

    if bullish:
        passed = wave4_end > wave1_end
    else:
        passed = wave4_end < wave1_end

    if passed:
        return RuleResult(
            passed=True,
            rule="Wave 4 No Overlap",
            reason="Wave 4 does not overlap Wave 1 territory.",
        )
    return RuleResult(
        passed=False,
        rule="Wave 4 No Overlap",
        reason=(
            "Wave 4 overlaps Wave 1 territory. "
            "This is only valid for diagonal patterns."
        ),
    )


# ── Chapter 4 – Wave Personalities ──────────────────────────────────────────


def classify_wave3(
    w1_start: float,
    w1_end: float,
    w3_start: float,
    w3_end: float,
) -> RuleResult:
    """Classify Wave 3 as normal or extended.

    Extended Wave 3 projects more than 161.8% of Wave 1.

    Args:
        w1_start: Wave 1 start price.
        w1_end:   Wave 1 end price.
        w3_start: Wave 3 start price (= Wave 2 end).
        w3_end:   Wave 3 end price.

    Returns:
        RuleResult with 'extended' or 'normal' in the reason.
    """
    len1 = wave_length(w1_start, w1_end)
    len3 = wave_length(w3_start, w3_end)
    ratio = len3 / len1 if len1 else float("inf")

    if ratio > RATIO_161:
        return RuleResult(
            passed=True,
            rule="Wave 3 Classification",
            reason=(
                f"Extended Wave 3: projects {ratio * 100:.1f}% of Wave 1 "
                f"(> 161.8%)."
            ),
        )
    return RuleResult(
        passed=True,
        rule="Wave 3 Classification",
        reason=f"Normal Wave 3: projects {ratio * 100:.1f}% of Wave 1 (≤ 161.8%).",
    )


def classify_wave5(
    w3_start: float,
    w3_end: float,
    w4_end: float,
    w5_end: float,
    w1_start: float,
    w1_end: float,
) -> RuleResult:
    """Classify Wave 5 and check for failure.

    * Normal Wave 5: projects up to 61.8% of Wave 3.
    * Extended Wave 5: projects more than 61.8% of Wave 3.
    * Failed Wave 5: length < length of Wave 1.

    Args:
        w3_start: Wave 3 start price.
        w3_end:   Wave 3 end price.
        w4_end:   Wave 4 end price (Wave 5 start).
        w5_end:   Wave 5 end price.
        w1_start: Wave 1 start price.
        w1_end:   Wave 1 end price.

    Returns:
        RuleResult describing the Wave 5 type.
    """
    len3 = wave_length(w3_start, w3_end)
    len5 = wave_length(w4_end, w5_end)
    len1 = wave_length(w1_start, w1_end)
    ratio = len5 / len3 if len3 else float("inf")

    if len5 < len1:
        return RuleResult(
            passed=False,
            rule="Wave 5 Classification",
            reason=(
                f"Failed Wave 5: length {len5:.4f} is shorter than "
                f"Wave 1 length {len1:.4f}."
            ),
        )
    if ratio > RATIO_61:
        return RuleResult(
            passed=True,
            rule="Wave 5 Classification",
            reason=(
                f"Extended Wave 5: projects {ratio * 100:.1f}% of Wave 3 "
                f"(> 61.8%). Often corrects 100% of Wave 5."
            ),
        )
    return RuleResult(
        passed=True,
        rule="Wave 5 Classification",
        reason=f"Normal Wave 5: projects {ratio * 100:.1f}% of Wave 3 (≤ 61.8%).",
    )


# ── Chapters 7-9 – Impulse Pattern Rules ─────────────────────────────────────


def check_impulse_wave(
    pivots: List[float],
    bullish: bool = True,
    is_diagonal: bool = False,
) -> List[RuleResult]:
    """Validate all basic rules for a 5-wave impulse pattern.

    Args:
        pivots:      List of six price pivots [W0, W1, W2, W3, W4, W5].
        bullish:     True if the impulse moves upward.
        is_diagonal: True if this is a Leading or Ending Diagonal.

    Returns:
        List of RuleResult for each rule checked.

    Raises:
        ValueError: If *pivots* does not contain exactly 6 elements.
    """
    if len(pivots) != 6:
        raise ValueError(
            f"Expected 6 pivot prices [W0..W5], got {len(pivots)}."
        )

    w0, w1, w2, w3, w4, w5 = pivots
    results: List[RuleResult] = []

    results.append(check_wave2_retrace(w0, w1, w2))
    results.append(check_wave3_not_shortest(w0, w1, w2, w3, w4, w5))
    results.append(check_wave4_no_overlap(w1, w4, bullish, is_diagonal))
    results.append(classify_wave3(w0, w1, w2, w3))
    results.append(classify_wave5(w2, w3, w4, w5, w0, w1))

    return results


# ── Chapter 14 – Extensions & Failures ──────────────────────────────────────


def check_wave5_qualification(
    w3_end: float,
    w4_end: float,
    w5_end: float,
    bullish: bool = True,
) -> RuleResult:
    """Wave 5 must complete *beyond* Wave 3 end and achieve ≥ 38% projection.

    Args:
        w3_end:  Wave 3 end price.
        w4_end:  Wave 4 end / Wave 5 start price.
        w5_end:  Wave 5 end price.
        bullish: True for upward impulse.

    Returns:
        RuleResult.
    """
    # Rule: Wave 5 must end beyond Wave 3
    if bullish:
        beyond_w3 = w5_end > w3_end
    else:
        beyond_w3 = w5_end < w3_end

    if not beyond_w3:
        return RuleResult(
            passed=False,
            rule="Wave 5 Qualification",
            reason=(
                "Wave 5 does not complete beyond Wave 3 end. "
                "Minimum requirement not met."
            ),
        )

    # Rule: minimum 38% projection from Wave 4 end
    len5 = wave_length(w4_end, w5_end)
    # Reference distance: from Wave 4 end to Wave 3 end (i.e. Wave 3 retraced
    # back to its starting price from Wave 4's perspective). This is the
    # practical proxy for the 38% minimum Wave 5 projection requirement.
    w3_len = wave_length(w4_end, w3_end)
    min_proj = w3_len * RATIO_38

    if len5 >= min_proj:
        return RuleResult(
            passed=True,
            rule="Wave 5 Qualification",
            reason=(
                f"Wave 5 qualifies: ends beyond Wave 3 and achieves "
                f"{len5 / w3_len * 100:.1f}% projection (≥ 38%)."
            ),
        )
    return RuleResult(
        passed=False,
        rule="Wave 5 Qualification",
        reason=(
            f"Wave 5 achieves only {len5 / w3_len * 100:.1f}% projection – "
            "minimum 38% not met. Treat this impulse as inner Wave i of Wave 5."
        ),
    )


# ── Chapter 18 – 38% Retracement Logic ───────────────────────────────────────


def check_38pct_breakout(
    wave_start: float,
    wave_end: float,
    current_price: float,
    bullish: bool = True,
) -> RuleResult:
    """Determine whether price has broken above/below the 38% retracement level.

    Args:
        wave_start:    Start of the measured wave (e.g. Wave 3 start).
        wave_end:      End of the measured wave (e.g. Wave 3 end).
        current_price: Latest market price to evaluate.
        bullish:       True for upward trend.

    Returns:
        RuleResult indicating confirmed continuation or possible reversal.
    """
    from .fibonacci import retracement_price  # avoid circular at module level

    level_38 = retracement_price(wave_start, wave_end, RATIO_38)

    if bullish:
        if current_price >= level_38:
            return RuleResult(
                passed=True,
                rule="38% Breakout",
                reason=(
                    f"Price {current_price:.4f} is above the 38% retracement "
                    f"level {level_38:.4f}. Trend continuation confirmed."
                ),
            )
        return RuleResult(
            passed=False,
            rule="38% Breakout",
            reason=(
                f"Price {current_price:.4f} has broken below the 38% level "
                f"{level_38:.4f}. Possible trend reversal."
            ),
        )
    else:
        if current_price <= level_38:
            return RuleResult(
                passed=True,
                rule="38% Breakout",
                reason=(
                    f"Price {current_price:.4f} is below the 38% retracement "
                    f"level {level_38:.4f}. Bearish trend continuation confirmed."
                ),
            )
        return RuleResult(
            passed=False,
            rule="38% Breakout",
            reason=(
                f"Price {current_price:.4f} has broken above the 38% level "
                f"{level_38:.4f}. Possible bearish reversal."
            ),
        )


def alternation_check(
    wave2_retrace_ratio: float,
    wave4_retrace_ratio: float,
) -> RuleResult:
    """Check the Alternation Principle between Wave 2 and Wave 4.

    If Wave 2 retraces deeply (> 61.8%), Wave 4 should retrace shallowly
    (normal 23–38%). If Wave 2 is shallow, Wave 4 tends to be deeper.

    Args:
        wave2_retrace_ratio: Wave 2 retracement ratio (0–1).
        wave4_retrace_ratio: Wave 4 retracement ratio (0–1).

    Returns:
        RuleResult.
    """
    w2_deep = wave2_retrace_ratio > RATIO_61
    w4_deep = wave4_retrace_ratio > RATIO_38

    if (w2_deep and not w4_deep) or (not w2_deep and w4_deep):
        return RuleResult(
            passed=True,
            rule="Alternation Principle",
            reason=(
                f"Alternation holds: Wave 2 retrace {wave2_retrace_ratio * 100:.1f}%, "
                f"Wave 4 retrace {wave4_retrace_ratio * 100:.1f}%."
            ),
        )
    return RuleResult(
        passed=False,
        rule="Alternation Principle",
        reason=(
            f"Alternation not observed: Wave 2 retrace {wave2_retrace_ratio * 100:.1f}%, "
            f"Wave 4 retrace {wave4_retrace_ratio * 100:.1f}%. "
            "Expect the next corrective wave to show stronger alternation."
        ),
    )
