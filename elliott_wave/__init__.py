"""
Elliott Wave Theory – Python Library
=====================================

Implements all rules and conditions from *SweeGlu Practical Application of
Elliott Wave Principle* (Chapters 1, 4, 7–14, 17–21).

Public API::

    from elliott_wave import ElliottWaveAnalyzer
    from elliott_wave.fibonacci import retracement_levels_for, projection_levels_for
    from elliott_wave.rules import check_impulse_wave, RuleResult
    from elliott_wave.patterns import detect_zigzag, PatternType
"""

from .analyzer import ElliottWaveAnalyzer, WaveReport
from .fibonacci import (
    retracement_levels_for,
    projection_levels_for,
    retracement_price,
    projection_price,
    retracement_ratio,
    wave_length,
    RETRACEMENT_LEVELS,
    PROJECTION_LEVELS,
)
from .rules import (
    RuleResult,
    WavePoint,
    check_wave2_retrace,
    check_wave3_not_shortest,
    check_wave4_no_overlap,
    check_wave5_qualification,
    check_38pct_breakout,
    alternation_check,
    check_impulse_wave,
    classify_wave3,
    classify_wave5,
)
from .patterns import (
    PatternResult,
    PatternType,
    detect_impulse,
    detect_leading_diagonal,
    detect_ending_diagonal,
    detect_zigzag,
    detect_irregular_correction,
    detect_flat_correction,
    detect_complex_correction,
    zigzag_trade_setup,
)

__all__ = [
    # Analyzer
    "ElliottWaveAnalyzer",
    "WaveReport",
    # Fibonacci
    "retracement_levels_for",
    "projection_levels_for",
    "retracement_price",
    "projection_price",
    "retracement_ratio",
    "wave_length",
    "RETRACEMENT_LEVELS",
    "PROJECTION_LEVELS",
    # Rules
    "RuleResult",
    "WavePoint",
    "check_wave2_retrace",
    "check_wave3_not_shortest",
    "check_wave4_no_overlap",
    "check_wave5_qualification",
    "check_38pct_breakout",
    "alternation_check",
    "check_impulse_wave",
    "classify_wave3",
    "classify_wave5",
    # Patterns
    "PatternResult",
    "PatternType",
    "detect_impulse",
    "detect_leading_diagonal",
    "detect_ending_diagonal",
    "detect_zigzag",
    "detect_irregular_correction",
    "detect_flat_correction",
    "detect_complex_correction",
    "zigzag_trade_setup",
]
