"""
Fibonacci utilities for Elliott Wave analysis.
Chapters 2 and 5 of SweeGlu Practical Application of Elliott Wave Principle.
"""

# ── Retracement levels (as fractions) ──────────────────────────────────────
RETRACEMENT_LEVELS = {
    "23.6%": 0.236,
    "38.2%": 0.382,
    "50.0%": 0.500,
    "61.8%": 0.618,
    "78.6%": 0.786,
    "100.0%": 1.000,
}

# ── Projection / extension levels (as fractions) ───────────────────────────
PROJECTION_LEVELS = {
    "38.2%": 0.382,
    "61.8%": 0.618,
    "100.0%": 1.000,
    "123.6%": 1.236,
    "161.8%": 1.618,
    "261.8%": 2.618,
}

# Convenience constants used throughout the library
RATIO_23 = 0.236
RATIO_38 = 0.382
RATIO_50 = 0.500
RATIO_61 = 0.618
RATIO_78 = 0.786
RATIO_100 = 1.000
RATIO_123 = 1.236
RATIO_161 = 1.618
RATIO_261 = 2.618


def retracement_price(start: float, end: float, ratio: float) -> float:
    """Return the price at a given Fibonacci retracement ratio.

    Args:
        start: Price at the beginning of the measured wave.
        end:   Price at the end of the measured wave.
        ratio: Fibonacci ratio (e.g. 0.382 for 38.2%).

    Returns:
        Retracement price level.
    """
    return end - (end - start) * ratio


def retracement_ratio(start: float, end: float, retrace_price: float) -> float:
    """Calculate the retracement ratio given start, end and retrace price.

    Args:
        start:         Price at the beginning of the measured wave.
        end:           Price at the end of the measured wave.
        retrace_price: Price to measure retracement to.

    Returns:
        Ratio in [0, 1+] representing the fraction retraced.

    Raises:
        ValueError: If start equals end (zero-length wave).
    """
    wave_length = abs(end - start)
    if wave_length == 0:
        raise ValueError("Wave length is zero; cannot calculate retracement ratio.")
    return abs(retrace_price - end) / wave_length


def projection_price(
    wave_start: float,
    wave_end: float,
    project_from: float,
    ratio: float,
) -> float:
    """Project a price target from *project_from* using *ratio* of the wave.

    Args:
        wave_start:   Start price of the reference wave.
        wave_end:     End price of the reference wave.
        project_from: Price level to project from (e.g. end of Wave 4).
        ratio:        Fibonacci projection ratio.

    Returns:
        Projected target price.
    """
    wave_length = abs(wave_end - wave_start)
    direction = 1 if wave_end > wave_start else -1
    return project_from + direction * wave_length * ratio


def wave_length(start: float, end: float) -> float:
    """Absolute length of a wave."""
    return abs(end - start)


def retracement_levels_for(start: float, end: float) -> dict:
    """Return all standard Fibonacci retracement price levels for a wave.

    Args:
        start: Price at the start of the wave.
        end:   Price at the end of the wave.

    Returns:
        Dictionary mapping label -> price for each Fibonacci level.
    """
    return {
        label: retracement_price(start, end, ratio)
        for label, ratio in RETRACEMENT_LEVELS.items()
    }


def projection_levels_for(
    wave_start: float, wave_end: float, project_from: float
) -> dict:
    """Return all standard Fibonacci projection price levels.

    Args:
        wave_start:   Start of the reference wave.
        wave_end:     End of the reference wave.
        project_from: Price to project from.

    Returns:
        Dictionary mapping label -> price for each projection level.
    """
    return {
        label: projection_price(wave_start, wave_end, project_from, ratio)
        for label, ratio in PROJECTION_LEVELS.items()
    }
